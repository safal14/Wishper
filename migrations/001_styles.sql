CREATE TABLE IF NOT EXISTS styles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    framework TEXT NOT NULL CHECK (framework = 'revideo'),
    code_path TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    preview_video_url TEXT,
    thumbnail_url TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'rendering', 'ready', 'failed')),
    version TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS styles_status_idx ON styles(status);
