import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as wishper


def sample_layout():
    return {
        "canvas": {"orientation": "horizontal", "aspect_ratio": "16:9", "width": 1280, "height": 720},
        "clips": [
            {
                "clip_id": "a" * 32,
                "index": 0,
                "source": {"width": 480, "height": 854, "duration": 2.5, "trim_start": 5.0},
                "mode": "smart",
                "regions": {
                    "inset": {"shape": "circle", "mirror": True, "px": {"x": 0, "y": 100, "w": 480, "h": 480}},
                    "pane_2": {"mirror": False, "px": {"x": 0, "y": 0, "w": 480, "h": 854}},
                },
                "overlay": {"position": "bottom-right", "size": 0.3, "margin": 0.04, "border_width": 2, "border_color": "#ffffff", "shadow": True},
                "split": {"direction": "vertical", "ratio": 0.4, "source_side": "first"},
            },
            {
                "clip_id": "b" * 32,
                "index": 1,
                "source": {"width": 1280, "height": 720, "duration": 1.5, "trim_start": 9.0},
                "mode": "full",
                "regions": {"full": {"mirror": False, "px": {"x": 0, "y": 0, "w": 1280, "h": 720}}},
            },
        ],
        "timeline": [
            {"clip_id": "a" * 32, "start": 0.0, "end": 1.25, "mode": "overlay"},
            {"clip_id": "a" * 32, "start": 1.25, "end": 2.5, "mode": "split"},
            {"clip_id": "b" * 32, "start": 2.5, "end": 4.0, "mode": "full"},
        ],
    }


class HandoffPromptTests(unittest.TestCase):
    def test_layout_instructions_include_absolute_timing_and_placement(self):
        instructions = wishper.build_layout_instructions(sample_layout())
        self.assertIn("16:9 horizontal", instructions)
        self.assertIn("00:00:00.000–00:00:01.250", instructions)
        self.assertIn("original time 00:00:05.000–00:00:06.250", instructions)
        self.assertIn("circle", instructions)
        self.assertIn("bottom-right", instructions)
        self.assertIn("30%", instructions)
        self.assertIn("mirror", instructions)
        self.assertIn("00:00:01.250–00:00:02.500", instructions)
        self.assertIn("original time 00:00:06.250–00:00:07.500", instructions)
        self.assertIn("split screen", instructions)
        self.assertIn("left", instructions)
        self.assertIn("40%", instructions)
        self.assertIn("00:00:02.500–00:00:04.000", instructions)
        self.assertIn("full frame", instructions)
        self.assertIn("generate visuals", instructions)

    def test_custom_overlay_and_stacked_split_are_described(self):
        layout = sample_layout()
        clip = layout["clips"][0]
        clip["regions"]["inset"]["shape"] = "square"
        clip["overlay"].update({"position": "custom", "x": 0.17, "y": 0.26, "border_width": 0, "shadow": False})
        clip["split"].update({"direction": "horizontal", "ratio": 0.35, "source_side": "second"})
        instructions = wishper.build_layout_instructions(layout)
        self.assertIn("square inset", instructions)
        self.assertIn("x=17%", instructions)
        self.assertIn("y=26%", instructions)
        self.assertIn("no border", instructions)
        self.assertIn("without shadow", instructions)
        self.assertIn("source on the bottom", instructions)
        self.assertIn("35% of canvas height", instructions)

    def test_manifest_links_crop_to_original_clip_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            clip_id = "d" * 32
            clip_dir = root / "clips" / clip_id
            clip_dir.mkdir(parents=True)
            (clip_dir / "metadata.json").write_text(json.dumps({
                "clip_id": clip_id, "name": "source.mp4", "filename": "processed.mp4",
                "trim_start": 1.0, "trim_end": 2.5, "layout": {"mode": "overlay"},
            }))
            project_path = root / "project.json"
            project_path.write_text(json.dumps({"orientation": "vertical", "confirmed": True}))
            info = {"width": 480, "height": 854, "duration": 3.0, "orientation": "vertical", "has_audio": True}
            with patch.object(wishper, "CLIPS_DIR", root / "clips"), patch.object(wishper, "PROJECT_PATH", project_path), patch.object(wishper, "clip_info", return_value=info):
                manifest = wishper.build_layout_manifest([clip_id])
        self.assertEqual(manifest["canvas"]["aspect_ratio"], "9:16")
        self.assertEqual(manifest["clips"][0]["source_file"], f"output/clips/{clip_id}/processed.mp4")
        self.assertEqual(manifest["timeline"][0]["end"], 1.5)
        self.assertIn("original time 00:00:01.000–00:00:02.500", wishper.build_layout_instructions(manifest))

    def test_server_package_prompt_contains_layout_and_preserves_user_brief(self):
        layout = sample_layout()
        clip_ids = [clip["clip_id"] for clip in layout["clips"]]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_id = "c" * 32
            job_dir = root / job_id
            job_dir.mkdir()
            (job_dir / "merged.mp4").touch()
            (job_dir / "source-order.json").write_text(json.dumps(clip_ids))
            project_path = root / "project.json"
            project_path.write_text(json.dumps({"orientation": "horizontal", "confirmed": True}))
            with patch.object(wishper, "OUTPUT_DIR", root), patch.object(wishper, "PROJECT_PATH", project_path), patch.object(wishper, "probe_video", return_value={"duration": 4.0}), patch.object(wishper, "build_layout_manifest", return_value=layout):
                with wishper.app.test_client() as client:
                    response = client.post("/api/server-package", json={
                        "job_id": job_id,
                        "prompt": "Make a calm travel film.",
                        "clip_order": clip_ids,
                        "transcript": {"segments": [{"start": 0, "end": 1, "text": "Hello"}]},
                    })
            self.assertEqual(response.status_code, 200, response.json)
            saved = json.loads((job_dir / "server-package.json").read_text())
            self.assertEqual(saved["user_prompt"], "Make a calm travel film.")
            self.assertIn("Make a calm travel film.", saved["prompt"])
            self.assertIn("00:00:01.250–00:00:02.500", saved["prompt"])
            self.assertIn("split screen", saved["prompt"])
            self.assertEqual(saved["overlay"], layout)
            self.assertEqual(response.json["manifest"], saved)


if __name__ == "__main__":
    unittest.main()
