"""Background preview worker; run once or poll for pending styles."""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from style_catalog import ROOT, connect, seed


PREVIEW_DIR = ROOT / "output" / "style-previews"


def render_one(db, row):
    style_id, digest = row["id"], row["code_hash"]
    folder = Path(row["code_path"])
    duration = json.loads((folder / "style.json").read_text(encoding="utf-8"))["preview_duration_seconds"]
    with tempfile.TemporaryDirectory(prefix="style-preview-", dir=PREVIEW_DIR) as temporary:
        video = Path(temporary) / "preview.mp4"
        thumb = Path(temporary) / "thumbnail.jpg"
        try:
            subprocess.run(["node", str(ROOT / "scripts" / "render_style.mjs"), str(folder / "project.ts"), str(video), str(duration)], cwd=ROOT, check=True, capture_output=True, text=True, timeout=600)
            if not video.is_file() or video.stat().st_size == 0:
                raise RuntimeError("Revideo did not create the preview video")
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(max(0, float(duration) - 1)), "-i", str(video), "-frames:v", "1", str(thumb)], check=True, capture_output=True, text=True, timeout=60)
            video_target = PREVIEW_DIR / f"{style_id}-{digest[:16]}.mp4"
            thumb_target = PREVIEW_DIR / f"{style_id}-{digest[:16]}.jpg"
            video.replace(video_target)
            thumb.replace(thumb_target)
            # A concurrent re-seed must not make an old render ready.
            updated = db.execute("""UPDATE styles SET status='ready', preview_video_url=?, thumbnail_url=?,
                error_message=NULL, updated_at=? WHERE id=? AND code_hash=? AND status='rendering'""",
                (f"/output/style-previews/{video_target.name}", f"/output/style-previews/{thumb_target.name}", datetime.now(timezone.utc).isoformat(), style_id, digest)).rowcount
            db.commit()
            if not updated:
                video_target.unlink(missing_ok=True)
                thumb_target.unlink(missing_ok=True)
            return bool(updated)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError) as exc:
            detail = (exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)) or str(exc)
            db.execute("UPDATE styles SET status='failed', error_message=?, updated_at=? WHERE id=? AND code_hash=? AND status='rendering'",
                       (detail[-4000:], datetime.now(timezone.utc).isoformat(), style_id, digest))
            db.commit()
            print(f"{style_id}: failed: {detail[-500:]}", flush=True)
            return False


def run_pending(retry_failed=False):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        seed(db)
        statuses = ("pending", "failed") if retry_failed else ("pending",)
        rows = db.execute(f"SELECT * FROM styles WHERE status IN ({','.join('?' * len(statuses))}) ORDER BY id", statuses).fetchall()
        failures = 0
        for row in rows:
            claimed = db.execute("UPDATE styles SET status='rendering', updated_at=? WHERE id=? AND code_hash=? AND status=?",
                                 (datetime.now(timezone.utc).isoformat(), row["id"], row["code_hash"], row["status"])).rowcount
            db.commit()
            if claimed:
                print(f"{row['id']}: rendering preview…", flush=True)
                if render_one(db, row):
                    print(f"{row['id']}: ready", flush=True)
                else:
                    failures += 1
        return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="Keep polling for changed styles")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed renders")
    args = parser.parse_args()
    while True:
        failures = run_pending(args.retry_failed)
        if not args.watch:
            sys.exit(1 if failures else 0)
        time.sleep(10)
