-- Golden Ball Ledger Schema

-- Core Tasks with V4 Metadata
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    source TEXT CHECK(source IN ('voice', 'chat', 'scheduled', 'api')),
    transcription_confidence REAL, -- 0.0 to 1.0
    reasoning_confidence REAL,     -- 0.0 to 1.0
    status TEXT DEFAULT 'pending', -- pending, approved, conflict, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Strategic Review Queue (HRM Conflicts)
CREATE TABLE IF NOT EXISTS strategic_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    conflict_reason TEXT,
    hrm_score REAL,
    impact_analysis TEXT,          -- JSON details
    resolved BOOLEAN DEFAULT 0,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

-- Clarification Requests (Low Confidence)
CREATE TABLE IF NOT EXISTS clarification_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_audio_path TEXT,
    transcription TEXT,
    confidence_score REAL,
    suggested_query TEXT,
    user_response TEXT,
    resolved BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Resource & Processing Log
CREATE TABLE IF NOT EXISTS processing_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service TEXT,       -- receiver, hrm, whisper
    event_type TEXT,    -- ingest, upscale, vad, inference
    details TEXT,
    duration_ms REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
