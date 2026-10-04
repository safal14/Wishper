import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as wishper


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.clips = self.root / "clips"
        self.clips.mkdir()
        self.project = self.root / "project.json"
        self.project.write_text(json.dumps({"orientation": "horizontal", "confirmed": True}))
        self.clip_id = "a" * 32
        clip_dir = self.clips / self.clip_id
        clip_dir.mkdir()
        self.source = clip_dir / "original.mp4"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", "color=c=blue:s=160x90:r=30:d=1",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", str(self.source)], check=True)
        (clip_dir / "metadata.json").write_text(json.dumps({
            "clip_id": self.clip_id, "filename": "original.mp4", "name": "test.mp4",
            "settings": wishper.default_settings(), "trim_start": 0, "trim_end": 1,
        }))
        self.patches = [patch.object(wishper, "OUTPUT_DIR", self.root),
                        patch.object(wishper, "CLIPS_DIR", self.clips),
                        patch.object(wishper, "PROJECT_PATH", self.project)]
        for item in self.patches:
            item.start()
        self.client = wishper.app.test_client()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temporary.cleanup()

    def fake_transcribe(self, _video, job_dir):
        data = {"job_id": job_dir.name, "language": "en",
                "segments": [{"start": 0, "end": 0.5, "text": "Hello world"}]}
        (job_dir / "transcript.json").write_text(json.dumps(data))
        wishper.write_vtt(data["segments"], job_dir / "captions.vtt")
        return data

    def test_merge_transcribes_and_restores_then_invalidates_changed_source(self):
        with patch.object(wishper, "transcribe", side_effect=self.fake_transcribe) as transcribe:
            response = self.client.post("/api/merge", json={"clip_ids": [self.clip_id]})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(transcribe.call_count, 1)
        self.assertEqual(response.json["segments"][0]["text"], "Hello world")
        self.assertEqual(self.client.get("/api/workflow").json["transcript"]["segments"][0]["text"], "Hello world")
        job_id = response.json["job_id"]
        edited = self.client.put(f"/api/jobs/{job_id}/transcript", json={
            "segments": [{"start": 0, "end": 0.5, "text": "Edited words"}]})
        self.assertEqual(edited.status_code, 200, edited.json)
        self.assertIn("Edited words", (self.root / job_id / "captions.vtt").read_text())
        self.assertEqual(self.client.get("/api/workflow").json["transcript"]["segments"][0]["text"], "Edited words")
        metadata = self.clips / self.clip_id / "metadata.json"
        changed = json.loads(metadata.read_text())
        changed["trim_start"] = 0.1
        metadata.write_text(json.dumps(changed))
        self.assertIsNone(self.client.get("/api/workflow").json["prepared"])
        stale = self.client.post("/api/server-package", json={
            "job_id": job_id, "clip_order": [self.clip_id], "prompt": "Make a sketch",
            "transcript": {"segments": [{"start": 0, "end": 0.5, "text": "Edited words"}]},
        })
        self.assertEqual(stale.status_code, 409)

    def test_silent_video_can_continue_with_empty_transcript(self):
        def empty_transcript(_video, job_dir):
            data = {"job_id": job_dir.name, "language": "en", "segments": []}
            (job_dir / "transcript.json").write_text(json.dumps(data))
            wishper.write_vtt([], job_dir / "captions.vtt")
            return data
        with patch.object(wishper, "transcribe", side_effect=empty_transcript):
            merged = self.client.post("/api/merge", json={"clip_ids": [self.clip_id]})
        self.assertEqual(merged.status_code, 200, merged.json)
        self.assertEqual(merged.json["segments"], [])
        self.assertEqual(self.client.get("/api/workflow").json["transcript"]["segments"], [])
        layout = {"canvas": wishper.canvas_for("horizontal"),
                  "clips": [{"clip_id": self.clip_id, "index": 0, "mode": "full",
                             "source": {"width": 160, "height": 90}, "regions": {"full": {"px": {"x": 0, "y": 0, "w": 160, "h": 90}, "mirror": False}}}],
                  "timeline": [{"clip_id": self.clip_id, "start": 0, "end": 1, "mode": "full"}]}
        with patch.object(wishper, "build_layout_manifest", return_value=layout):
            package = self.client.post("/api/server-package", json={
                "job_id": merged.json["job_id"], "clip_order": [self.clip_id],
                "prompt": "Draw a quiet scene", "transcript": {"segments": []},
            })
        self.assertEqual(package.status_code, 200, package.json)
        self.assertEqual(package.json["manifest"]["transcript"]["segments"], [])
        restored = self.client.get("/api/workflow").json
        self.assertEqual(restored["handoff"]["user_prompt"], "Draw a quiet scene")
        self.assertNotIn("code", restored["handoff"])
        self.assertIsNotNone(restored["package_url"])

    def test_failed_transcript_keeps_source_for_retry(self):
        with patch.object(wishper, "transcribe", side_effect=RuntimeError("Whisper unavailable")):
            response = self.client.post("/api/merge", json={"clip_ids": [self.clip_id]})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json["transcription_error"], "Whisper unavailable")
        job_id = response.json["job_id"]
        self.assertTrue((self.root / job_id / "merged.mp4").is_file())
        self.assertIsNone(self.client.get("/api/workflow").json["transcript"])
        with patch.object(wishper, "transcribe", side_effect=self.fake_transcribe):
            retried = self.client.post(f"/api/jobs/{job_id}/transcribe")
        self.assertEqual(retried.status_code, 200, retried.json)
        self.assertEqual(retried.json["segments"][0]["text"], "Hello world")

    def test_output_route_does_not_escape_workspace(self):
        self.assertEqual(self.client.get("/output/../app.py").status_code, 404)
        self.assertEqual(self.client.get("/output/not-a-job/file.mp4").status_code, 404)

    def test_import_finished_video_requires_package_and_does_not_overwrite(self):
        with patch.object(wishper, "transcribe", side_effect=self.fake_transcribe):
            merged = self.client.post("/api/merge", json={"clip_ids": [self.clip_id]})
        job_id = merged.json["job_id"]
        video_bytes = self.source.read_bytes()
        def upload(content=video_bytes):
            return self.client.post(f"/api/jobs/{job_id}/result", data={
                "video": (io.BytesIO(content), "finished.mp4")}, content_type="multipart/form-data")
        self.assertEqual(upload().status_code, 404)
        (self.root / job_id / "server-package.json").write_text("{}")
        self.assertEqual(upload(b"not a video").status_code, 422)
        first = upload()
        self.assertEqual(first.status_code, 200, first.json)
        second = upload()
        self.assertEqual(second.status_code, 200, second.json)
        self.assertNotEqual(first.json["video_url"], second.json["video_url"])
        self.assertTrue((self.root / job_id / first.json["video_url"].rsplit("/", 1)[1]).is_file())
        workflow = self.client.get("/api/workflow").json
        self.assertEqual(workflow["result_url"], second.json["video_url"])
        self.assertTrue(workflow["result_is_current"])
        result = self.client.get(second.json["video_url"])
        self.assertEqual(result.status_code, 200)
        result.close()


if __name__ == "__main__":
    unittest.main()
