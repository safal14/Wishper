import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as wishper
import style_catalog
from scripts import render_styles as worker
from test_handoff_prompt import sample_layout


class StyleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.database = self.root / "styles.sqlite3"
        with style_catalog.connect(self.database) as db:
            self.assertEqual(style_catalog.seed(db), 3)
            db.execute("UPDATE styles SET status='ready', preview_video_url='/output/style-previews/example.mp4', thumbnail_url='/output/style-previews/example.jpg' WHERE id='marker-whiteboard'")
            db.commit()
        self.connect_patch = patch.object(wishper, "connect_styles", lambda: style_catalog.connect(self.database))
        self.connect_patch.start()
        self.addCleanup(self.connect_patch.stop)

    def test_catalog_exposes_only_ready_preview_metadata(self):
        with wishper.app.test_client() as client:
            listing = client.get("/styles")
            selected = client.get("/styles/marker-whiteboard")
            missing = client.get("/styles/clean-whiteboard")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json["styles"]), 1)
        self.assertEqual(set(selected.json), {"id", "name", "description", "preview_video_url", "thumbnail_url"})
        self.assertEqual(missing.status_code, 404)
        self.assertNotIn("code", json.dumps(listing.json))

    def test_hash_change_invalidates_preview_but_unchanged_seed_does_not(self):
        copied = self.root / "packages" / "marker-whiteboard"
        shutil.copytree(style_catalog.STYLE_DIR / "marker-whiteboard", copied)
        with style_catalog.connect(self.database) as db:
            style_catalog.seed(db, copied.parent)
            row = db.execute("SELECT status,preview_video_url FROM styles WHERE id='marker-whiteboard'").fetchone()
            self.assertEqual(row["status"], "ready")
            self.assertIsNotNone(row["preview_video_url"])
            with (copied / "tokens.ts").open("a") as stream:
                stream.write("\n// changed\n")
            style_catalog.seed(db, copied.parent)
            row = db.execute("SELECT status,preview_video_url FROM styles WHERE id='marker-whiteboard'").fetchone()
        self.assertEqual(row["status"], "pending")
        self.assertIsNone(row["preview_video_url"])

    def test_handoff_uses_server_code_and_rejects_unknown_id(self):
        layout = sample_layout()
        clip_ids = [item["clip_id"] for item in layout["clips"]]
        job_id = "c" * 32
        job_dir = self.root / job_id
        job_dir.mkdir()
        (job_dir / "merged.mp4").touch()
        (job_dir / "source-order.json").write_text(json.dumps(clip_ids))
        project_path = self.root / "project.json"
        project_path.write_text(json.dumps({"orientation": "horizontal", "confirmed": True}))
        payload = {"job_id": job_id, "prompt": "Explain the idea", "clip_order": clip_ids,
                   "transcript": {"segments": [{"start": 0, "end": 1, "text": "Hello"}]},
                   "style_id": "marker-whiteboard", "style_code": "MALICIOUS CLIENT CODE"}
        with patch.object(wishper, "OUTPUT_DIR", self.root), patch.object(wishper, "PROJECT_PATH", project_path), \
             patch.object(wishper, "probe_video", return_value={"duration": 4.0}), \
             patch.object(wishper, "build_layout_manifest", return_value=layout):
            with wishper.app.test_client() as client:
                accepted = client.post("/api/server-package", json=payload)
                rejected = client.post("/api/server-package", json={**payload, "style_id": "missing"})
        self.assertEqual(accepted.status_code, 200, accepted.json)
        self.assertEqual(rejected.status_code, 404)
        manifest = accepted.json["manifest"]
        self.assertEqual(manifest["style_id"], "marker-whiteboard")
        self.assertTrue(Path(manifest["style"]["files"]["tokens.ts"]).is_file())
        self.assertTrue(Path(manifest["style"]["code_path"]).is_relative_to(job_dir / "style-snapshots"))
        self.assertEqual(style_catalog.code_hash(Path(manifest["style"]["code_path"])), manifest["style"]["code_hash"])
        self.assertEqual(manifest["style"]["code"]["tokens.ts"], (style_catalog.STYLE_DIR / "marker-whiteboard" / "tokens.ts").read_text())
        self.assertIn(manifest["style"]["code"]["tokens.ts"], manifest["prompt"])
        self.assertIn(manifest["style"]["code"]["helpers.ts"], manifest["prompt"])
        self.assertIn("Reuse tokens.ts and helpers.ts", manifest["prompt"])
        self.assertIn(manifest["style"]["code_path"], manifest["prompt"])
        self.assertNotIn("MALICIOUS CLIENT CODE", json.dumps(manifest))


    def test_render_failure_marks_only_the_claimed_style_failed(self):
        with style_catalog.connect(self.database) as db:
            db.execute("UPDATE styles SET status='rendering' WHERE id='marker-whiteboard'")
            db.commit()
            row = db.execute("SELECT * FROM styles WHERE id='marker-whiteboard'").fetchone()
            with patch.object(worker, "PREVIEW_DIR", self.root), patch.object(
                worker.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "node", stderr="render broke")
            ):
                self.assertFalse(worker.render_one(db, row))
            self.assertEqual(db.execute("SELECT status FROM styles WHERE id='marker-whiteboard'").fetchone()[0], "failed")
            self.assertEqual(db.execute("SELECT status FROM styles WHERE id='clean-whiteboard'").fetchone()[0], "pending")


if __name__ == "__main__":
    unittest.main()
