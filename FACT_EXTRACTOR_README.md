# Auto Fact Extractor for Echo

Automatically extracts entities, preferences, tech stack, patterns, and context from conversations.

## What It Does

- **Automatic extraction**: Runs during `archive_session()` - zero latency during conversations
- **Local only**: Uses MLX LLM + MLX embeddings - no external services
- **Semantic search**: Recall facts using cosine similarity with embeddings
- **Smart filtering**: Skips test/debug conversations automatically

## Fact Types

| Type | Examples |
|-------|-----------|
| `entity` | Names, IDs, identifiers (e.g., "Nirvan", "Project Alpha") |
| `preference` | User preferences (e.g., "Prefers dark mode", "Likes spicy food") |
| `tech_stack` | Technologies/tools (e.g., "Uses MLX for embeddings", "React frontend") |
| `pattern` | Recurring behaviors (e.g., "Always runs tests before deployment") |
| `context` | Job/role info (e.g., "Software engineer on support team") |

## Integration Points

### 1. Database (`database.py`)
- New `facts` table with semantic search support
- Functions: `add_fact()`, `get_similar_facts()`, `recall_facts()`

### 2. LLM Client (`llm_client.py`)
- `archive_session()` extracts facts before archiving
- New tool: `recall_facts(query, fact_type=None)`
- Facts automatically added to LLM context every query

### 3. Fact Extractor (`fact_extractor.py`)
- Standalone module for extraction
- CLI tools: `extract`, `recall`, `list`
- MLX LLM for intelligent extraction

## Usage

### Automatic (during archive)
```
User: Archive this chat
→ Fact extraction runs
→ Stores entities, preferences, etc.
→ Archives to file
→ Shows extracted facts summary
```

### Manual recall via LLM
```
User: What do I use for embeddings?
→ LLM calls recall_facts()
→ Returns: "Uses MLX for all my embedding tasks"
```

### CLI tools
```bash
# List all stored facts
python3 fact_extractor.py list

# Recall facts by query
python3 fact_extractor.py recall "dark mode"

# Filter by type
python3 fact_extractor.py recall "Nirvan" --type entity

# Extract from current chat history
python3 fact_extractor.py extract --source manual
```

## Configuration

### Disable auto-extraction
```bash
export AUTO_EXTRACT_FACTS=false
```

### Skip test/debug conversations
Automatically skips conversations containing:
- `test`, `debug`, `example`, `demo`, `trial`, `sample`
- `testing`, `placeholder`, `fake`, `mock`, `dummy`

## Database Schema

```sql
CREATE TABLE facts (
    id INTEGER PRIMARY KEY,
    fact_type TEXT,              -- entity|preference|tech_stack|pattern|context
    value TEXT,                  -- The fact text
    confidence REAL,              -- 0.0-1.0 confidence score
    source TEXT,                 -- e.g., "session", "archive_2024-01-23"
    metadata TEXT,               -- JSON metadata
    embedding TEXT,               -- MLX embedding vector (JSON)
    created_at TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER           -- Track popularity
)
```

## Example Output

```bash
$ python3 fact_extractor.py extract

Extracting facts from 42 messages...
Extracted 8 facts
Stored 8 facts in database

[ENTITY] Marley (confidence: 1.00)
[PREFERENCE] Prefers dark mode (confidence: 1.00)
[TECH_STACK] Uses MLX for all my embedding tasks (confidence: 1.00)
[CONTEXT] Software engineer on support team (confidence: 1.00)
```

## Benefits vs Manual Notes

| Feature | Manual Notes | Auto Facts |
|----------|--------------|-------------|
| Extraction | User must say "remember this" | Automatic during archive |
| Classification | None (all notes same) | Categorized types |
| Recall | Manual `recall_notes()` | Auto-included in context |
| Semantic search | Yes (existing) | Yes (same) |
| Confidence tracking | No | Yes |
| Access tracking | No | Yes |

## Technical Details

- **LLM**: MLX Llama 3.2 3B at `http://127.0.0.1:1234/v1`
- **Embeddings**: MLX all-MiniLM-L6-v2 (sentence-transformers)
- **Search**: Cosine similarity with numpy
- **Storage**: SQLite with JSON embeddings