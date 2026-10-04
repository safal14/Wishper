import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as wishper


class MusicCatalogTests(unittest.TestCase):
    def test_bundled_tracks_are_listed_and_playable(self):
        with wishper.app.test_client() as client:
            response = client.get("/api/music/catalog")
            self.assertEqual(response.status_code, 200)
            tracks = response.json["tracks"]
            self.assertEqual(len(tracks), 3)
            for track in tracks:
                self.assertTrue(track["file"].startswith("static/music/"))
                asset = client.get(track["url"])
                self.assertEqual(asset.status_code, 200)
                asset.close()

    def test_package_accepts_catalog_track_and_rejects_fake_track(self):
        clip_id = "a" * 32
        layout = {
            "canvas": {"orientation": "horizontal", "aspect_ratio": "16:9", "width": 1280, "height": 720},
            "clips": [{
                "clip_id": clip_id, "index": 0, "source": {"width": 320, "height": 180},
                "regions": {"full": {"px": {"x": 0, "y": 0, "w": 320, "h": 180}, "mirror": False}},
            }],
            "timeline": [{"clip_id": clip_id, "start": 0, "end": 1, "mode": "full"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_id = "b" * 32
            job_dir = root / job_id
            job_dir.mkdir()
            (job_dir / "merged.mp4").touch()
            (job_dir / "source-order.json").write_text(json.dumps([clip_id]))
            project_path = root / "project.json"
            project_path.write_text(json.dumps({"orientation": "horizontal", "confirmed": True}))
            music_dir = root / "music"
            music_dir.mkdir()
            (music_dir / "own.mp3").write_bytes(b"test audio asset")
            payload = {
                "job_id": job_id, "clip_order": [clip_id], "prompt": "Make a travel film.",
                "transcript": {"segments": [{"start": 0, "end": 0.5, "text": "Hello"}]},
                "background_sound": {"enabled": True, "id": "soft-ambient", "file": "static/music/soft-ambient.mp3", "volume": 0.1, "start": 0},
            }
            with patch.object(wishper, "OUTPUT_DIR", root), patch.object(wishper, "MUSIC_DIR", music_dir), patch.object(wishper, "PROJECT_PATH", project_path), patch.object(wishper, "probe_video", return_value={"duration": 1}), patch.object(wishper, "build_layout_manifest", return_value=layout):
                with wishper.app.test_client() as client:
                    accepted = client.post("/api/server-package", json=payload)
                    self.assertEqual(accepted.status_code, 200, accepted.json)
                    self.assertEqual(accepted.json["manifest"]["music"]["source"], "builtin")
                    self.assertEqual(accepted.json["manifest"]["music"]["name"], "Soft ambient")
                    self.assertTrue(accepted.json["manifest"]["music"]["loop"])
                    payload["background_sound"]["file"] = "static/music/missing.mp3"
                    rejected = client.post("/api/server-package", json=payload)
                    self.assertEqual(rejected.status_code, 400)
                    payload["background_sound"].update({"id": [], "file": "static/music/soft-ambient.mp3"})
                    malformed = client.post("/api/server-package", json=payload)
                    self.assertEqual(malformed.status_code, 400)
                    payload["background_sound"].update({"id": "my-track", "file": "output/music/own.mp3"})
                    uploaded = client.post("/api/server-package", json=payload)
                    self.assertEqual(uploaded.status_code, 200, uploaded.json)
                    self.assertEqual(uploaded.json["manifest"]["music"]["file"], "output/music/own.mp3")


if __name__ == "__main__":
    unittest.main()
