"""Server-owned style catalog and hash-based preview lifecycle."""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STYLE_DIR = ROOT / "styles"
DB_PATH = ROOT / "output" / "styles.sqlite3"
MIGRATION = ROOT / "migrations" / "001_styles.sql"
CODE_FILES = ("style.json", "tokens.ts", "helpers.ts", "scene.tsx", "project.ts")
PUBLIC_FIELDS = ("id", "name", "description", "preview_video_url", "thumbnail_url")


def connect(path=DB_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 30000")
    db.executescript(MIGRATION.read_text(encoding="utf-8"))
    return db


def code_hash(folder):
    digest = hashlib.sha256()
    for name in CODE_FILES:
        contents = (folder / name).read_bytes()
        digest.update(name.encode("utf-8") + b"\0" + contents + b"\0")
    return digest.hexdigest()


def seed(db, style_dir=STYLE_DIR):
    """Upsert checked-in styles; keep ready previews until their code changes."""
    count = 0
    for manifest_path in sorted(Path(style_dir).glob("*/style.json")):
        folder = manifest_path.parent
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        required = {"id", "name", "description", "framework", "scene_file", "preview_duration_seconds", "version"}
        if not required.issubset(manifest) or manifest["id"] != folder.name or manifest["framework"] != "revideo" or manifest["scene_file"] != "scene.tsx":
            raise ValueError(f"Invalid style manifest: {manifest_path}")
        if not isinstance(manifest["preview_duration_seconds"], (int, float)) or not 0 < manifest["preview_duration_seconds"] <= 30:
            raise ValueError(f"Invalid preview duration: {manifest_path}")
        digest = code_hash(folder)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            """INSERT INTO styles (id,name,description,framework,code_path,code_hash,status,version,created_at,updated_at)
               VALUES (?,?,?,?,?,?,'pending',?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, description=excluded.description, framework=excluded.framework,
                 code_path=excluded.code_path, version=excluded.version,
                 code_hash=excluded.code_hash,
                 status=CASE WHEN styles.code_hash=excluded.code_hash THEN styles.status ELSE 'pending' END,
                 preview_video_url=CASE WHEN styles.code_hash=excluded.code_hash THEN styles.preview_video_url ELSE NULL END,
                 thumbnail_url=CASE WHEN styles.code_hash=excluded.code_hash THEN styles.thumbnail_url ELSE NULL END,
                 error_message=CASE WHEN styles.code_hash=excluded.code_hash THEN styles.error_message ELSE NULL END,
                 updated_at=CASE WHEN styles.code_hash=excluded.code_hash THEN styles.updated_at ELSE excluded.updated_at END""",
            (manifest["id"], manifest["name"], manifest["description"], "revideo", str(folder.resolve()), digest, str(manifest["version"]), now, now),
        )
        count += 1
    db.commit()
    return count


def public_style(row):
    return {field: row[field] for field in PUBLIC_FIELDS}


def ready_styles(db):
    return [public_style(row) for row in db.execute("SELECT * FROM styles WHERE status='ready' ORDER BY name")]


def ready_style(db, style_id):
    row = db.execute("SELECT * FROM styles WHERE id=? AND status='ready'", (style_id,)).fetchone()
    return row


def style_reference(row):
    """Build the private handoff reference from server-owned files, never client code."""
    folder = Path(row["code_path"])
    if not folder.is_dir() or code_hash(folder) != row["code_hash"]:
        raise ValueError("Style code changed since its preview was rendered. Re-seed and render styles.")
    return {
        "id": row["id"], "name": row["name"], "framework": "revideo",
        "version": row["version"], "code_hash": row["code_hash"],
        "code_path": str(folder),
        "files": {name: str(folder / name) for name in CODE_FILES},
    }
