import sqlite3
import json
import numpy as np
import datetime
from typing import List, Dict, Optional

import os

# Use absolute path to ensure all modules share the same DB
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.db")

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date TIMESTAMP,
            completed_at TIMESTAMP,
            archived_at TIMESTAMP
        )
    ''')
    
    # Check for new columns (migration)
    cursor.execute("PRAGMA table_info(tasks)")
    columns = [info[1] for info in cursor.fetchall()]
    if "completed_at" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN completed_at TIMESTAMP")
    if "archived_at" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN archived_at TIMESTAMP")

    # Processed messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_messages (
            message_id TEXT PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Chat History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Notes table with embedding support
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            embedding TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if embedding column exists (migration)
    cursor.execute("PRAGMA table_info(notes)")
    note_columns = [info[1] for info in cursor.fetchall()]
    if "embedding" not in note_columns:
        cursor.execute("ALTER TABLE notes ADD COLUMN embedding TEXT")

    conn.commit()
    conn.close()

def add_task(description: str, due_date: Optional[str] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (description, due_date) VALUES (?, ?)", (description, due_date))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id

def add_note(content: str, embedding: Optional[List[float]] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    embedding_json = json.dumps(embedding) if embedding else None
    cursor.execute("INSERT INTO notes (content, embedding) VALUES (?, ?)", (content, embedding_json))
    conn.commit()
    note_id = cursor.lastrowid
    conn.close()
    return note_id

def get_similar_notes(query_embedding: List[float], top_k: int = 3) -> List[Dict]:
    """
    Retrieves notes sorted by cosine similarity to the query embedding.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    notes_with_scores = []
    query_vec = np.array(query_embedding)
    
    norm_query = np.linalg.norm(query_vec)
    if norm_query == 0:
        return [dict(row) for row in rows[:top_k]] # Fallback

    for row in rows:
        note = dict(row)
        if not note['embedding']:
            continue
            
        try:
            emb_vec = np.array(json.loads(note['embedding']))
            norm_emb = np.linalg.norm(emb_vec)
            if norm_emb == 0:
                score = 0
            else:
                score = np.dot(query_vec, emb_vec) / (norm_query * norm_emb)
            
            notes_with_scores.append((score, note))
        except Exception:
            continue

    # Sort by score descending
    notes_with_scores.sort(key=lambda x: x[0], reverse=True)
    
    return [n for score, n in notes_with_scores[:top_k]]

def get_notes() -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_note(note_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    changes = cursor.rowcount
    conn.close()
    return changes > 0

def get_tasks(status: Optional[str] = None) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY id DESC", (status,))
    else:
        cursor.execute("SELECT * FROM tasks ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_due_tasks() -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    # Find pending tasks where due_date is in the past or now
    cursor.execute("SELECT * FROM tasks WHERE status = 'pending' AND due_date IS NOT NULL AND due_date <= datetime('now', 'localtime')")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def complete_task(task_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?", (now, task_id))
    conn.commit()
    changes = cursor.rowcount
    conn.close()
    return changes > 0

def complete_all_tasks() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tasks SET status = 'completed', completed_at = ? WHERE status = 'pending'", (now,))
    conn.commit()
    changes = cursor.rowcount
    conn.close()
    return changes

def _normalize_task_query(description: str) -> str:
    return " ".join(description.strip().lower().split())


def find_tasks_by_description(description: str, status: Optional[str] = None) -> List[Dict]:
    """Find tasks by case-insensitive partial match, newest first."""
    query = _normalize_task_query(description)
    if not query:
        return []
    conn = get_connection()
    cursor = conn.cursor()
    like_query = f"%{query}%"
    if status:
        cursor.execute(
            "SELECT * FROM tasks WHERE status = ? AND LOWER(description) LIKE ? ORDER BY id DESC",
            (status, like_query),
        )
    else:
        cursor.execute(
            "SELECT * FROM tasks WHERE LOWER(description) LIKE ? ORDER BY id DESC",
            (like_query,),
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def complete_task_by_description(description: str) -> Optional[Dict]:
    """Complete the newest pending task matching the description."""
    matches = find_tasks_by_description(description, status="pending")
    if not matches:
        return None
    task = matches[0]
    if complete_task(task["id"]):
        return task
    return None


def delete_task_by_description(description: str) -> Optional[Dict]:
    """Delete the newest task matching the description."""
    matches = find_tasks_by_description(description)
    if not matches:
        return None
    task = matches[0]
    if delete_task(task["id"]):
        return task
    return None


def delete_task(task_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    changes = cursor.rowcount
    conn.close()
    return changes > 0

def delete_completed_tasks() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE status = 'completed'")
    conn.commit()
    changes = cursor.rowcount
    conn.close()
    return changes

# --- ARCHIVE HELPERS ---

def archive_completed_tasks() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Mark 'completed' tasks as 'archived'
    cursor.execute("UPDATE tasks SET status = 'archived', archived_at = ? WHERE status = 'completed'", (now,))
    conn.commit()
    changes = cursor.rowcount
    conn.close()
    return changes

def get_archived_tasks() -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE status = 'archived' ORDER BY completed_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_chat_history() -> List[Dict]:
    """Get everything for archiving."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_history ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_chat_history(session_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if session_id:
        cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
    else:
        cursor.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()

def save_chat_message(session_id: str, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
    conn.commit()
    conn.close()

def get_chat_history(session_id: str, limit: int = 50) -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY id ASC LIMIT ?", (session_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_message_processed(message_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO processed_messages (message_id) VALUES (?)", (message_id,))
    conn.commit()
    conn.close()

def is_message_processed(message_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_messages WHERE message_id = ?", (message_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
