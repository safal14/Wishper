import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename
from style_catalog import CODE_FILES, code_hash, connect as connect_styles, ready_style, ready_styles, public_style, style_reference


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
CLIPS_DIR = OUTPUT_DIR / "clips"
CLIPS_DIR.mkdir(exist_ok=True)
MUSIC_DIR = OUTPUT_DIR / "music"
MUSIC_DIR.mkdir(exist_ok=True)
MUSIC_PRESETS = (
    {"id": "soft-ambient", "name": "Soft ambient", "description": "Calm, spacious notes for a voice-led video.", "file": "static/music/soft-ambient.mp3"},
    {"id": "steady-motion", "name": "Steady motion", "description": "A gentle pulse for a faster edit.", "file": "static/music/steady-motion.mp3"},
    {"id": "bright-day", "name": "Bright day", "description": "Light melodic notes for an upbeat story.", "file": "static/music/bright-day.mp3"},
)
MUSIC_PRESET_BY_ID = {track["id"]: track for track in MUSIC_PRESETS}

ALLOWED_EXTENSIONS = {"mp4", "mov", "mkv", "webm", "avi", "m4v", "mpeg", "mpg"}
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8" if WHISPER_DEVICE == "cpu" else "float16")
GENERATOR_SERVER_URL = os.getenv("GENERATOR_SERVER_URL", "http://192.168.1.16:8001").rstrip("/")
GENERATOR_USER_ID = os.getenv("GENERATOR_USER_ID", "safal")
GENERATOR_CLIENT_NAME = os.getenv("GENERATOR_CLIENT_NAME", "Wishper Studio")
GENERATOR_PROTOCOL_VERSION = "test4-v1"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "2048")) * 1024 * 1024


def remote_http(method, path, body=None, content_type=None):
    """Call the LAN generator without exposing generator credentials to the browser."""
    url = f"{GENERATOR_SERVER_URL}/{path.lstrip('/')}"
    request = urllib.request.Request(url, data=body, method=method.upper())
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.headers.get_content_type(), response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Generator server returned HTTP {exc.code}: {detail[:500]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Could not reach generator server at {GENERATOR_SERVER_URL}: {exc}") from exc


def multipart_form(fields, files=None):
    boundary = f"----Wishper{uuid.uuid4().hex}"
    chunks = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            str(value).encode(),
            b"\r\n",
        ])
    for name, file_info in (files or {}).items():
        filename, content_type, content = file_info
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            content,
            b"\r\n",
        ])
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def remote_generation_prompt(manifest):
    """Send the complete server-bound prompt; the generator allows up to 50000 characters."""
    prompt = manifest.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise RuntimeError("The handoff package has no generation prompt.")
    if len(prompt) > 50000:
        raise RuntimeError("The generation prompt exceeds the generator server's 50000-character limit.")
    return prompt


def stored_remote_job_id(record):
    value = record.get("remote_job_id")
    if isinstance(value, str) and value.lstrip().startswith("{"):
        try:
            payload = json.loads(value)
            value = payload.get("job_id") or payload.get("id")
        except json.JSONDecodeError:
            pass
    if not value:
        raise RuntimeError("Remote job ID is missing.")
    return str(value)


def remote_status_text(payload):
    if isinstance(payload, dict):
        values = []
        for key, value in payload.items():
            if key.lower() in {"status", "state", "phase"}:
                values.append(str(value))
            values.append(remote_status_text(value))
        return " ".join(values)
    if isinstance(payload, list):
        return " ".join(remote_status_text(value) for value in payload)
    return str(payload) if payload is not None else ""


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def clip_metadata_path(clip_id):
    return CLIPS_DIR / clip_id / "metadata.json"


def read_clip(clip_id):
    path = clip_metadata_path(clip_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def clip_source(clip):
    return CLIPS_DIR / clip["clip_id"] / clip["filename"]


def clip_original_source(clip):
    return CLIPS_DIR / clip["clip_id"] / clip.get("original_filename", "original.mp4")


def default_settings():
    return {"brightness": 0, "contrast": 1, "saturation": 1, "sharpness": 0, "blur": 0, "video_noise": 0, "audio_noise": 0, "noise_type": "general", "audio_mode": "manual", "hum_frequency": "auto", "remove_rumble": 1, "reduce_hiss": 0, "normalize_audio": 1, "audio_algorithm": "afftdn", "voice_enhance": 0, "speed": 1, "rotate": 0, "fade_in": 0, "fade_out": 0}


def clip_response(clip):
    return {**clip, "url": f"/output/clips/{clip['clip_id']}/{clip['filename']}"}


def run_ffmpeg(args):
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is not installed or is not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stderr.strip() or "ffmpeg could not process this video.") from exc


def audio_stream_details(video_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index,codec_name,channels,sample_rate", "-of", "json", str(video_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is not installed or is not on PATH. Install ffmpeg first.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stderr.strip() or "Could not inspect the uploaded video.") from exc
    try:
        return json.loads(result.stdout).get("streams", [])
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe returned invalid stream information for this video.") from exc


def format_timestamp(seconds, decimal=False):
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remainder = seconds % 60
    if decimal:
        return f"{hours:02d}:{minutes:02d}:{remainder:06.3f}"
    return f"{hours:02d}:{minutes:02d}:{int(remainder):02d}"


def write_vtt(segments, path):
    with path.open("w", encoding="utf-8") as file:
        file.write("WEBVTT\n\n")
        for index, segment in enumerate(segments, start=1):
            file.write(f"{index}\n")
            file.write(f"{format_timestamp(segment['start'], True)} --> {format_timestamp(segment['end'], True)}\n")
            file.write(f"{segment['text'].strip()}\n\n")


# ---------------------------------------------------------------------------
# The project aspect ratio and source placement are saved as handoff data.
# Source preparation only trims, processes, and joins uploaded clips.
# Generated visuals and final composition happen after this client workflow.
# ---------------------------------------------------------------------------
CANVAS_SIZES = {"horizontal": (1280, 720, "16:9"), "vertical": (720, 1280, "9:16")}
LAYOUT_MODES = ("full", "overlay", "split", "smart")
SEGMENT_LAYOUTS = ("full", "split", "overlay")
REGION_ROLES = ("full", "pane_1", "pane_2", "inset")
OVERLAY_POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right", "custom")
PROJECT_PATH = OUTPUT_DIR / "project.json"
LAYOUTS_DIR = OUTPUT_DIR / "layouts"
LAYOUTS_DIR.mkdir(exist_ok=True)

LAYOUT_SEMANTICS = [
    "Region coordinates x, y, w, h are normalized 0-1 fractions of the source frame, measured from its top-left corner. 'px' is the same box in source pixels.",
    "mode 'full': the source video uses regions.full and fills the whole canvas.",
    "mode 'overlay': generated content fills the background; the source video uses regions.inset as a circle or square. overlay.size and overlay.margin are fractions of the shorter canvas side; custom overlay.x/y are normalized top-left canvas coordinates. Border width is in pixels.",
    "mode 'split': generated content occupies the space not used by the source. split.direction vertical divides left/right; horizontal divides top/bottom. split.ratio is the source share of canvas width/height, and split.source_side first means left/top.",
    "mode 'smart': segments select full, split or overlay for time ranges relative to each source clip.",
    "'segments' is always present; for full, overlay and split it is a single segment covering the whole clip.",
    "mirror true means that region is flipped left-to-right before it is placed.",
    "Regions the chosen layout does not use can be ignored.",
    "Each clip's source_file points to the original/processed clip used by regions and pixel crop coordinates; the merged source sequence is a separate preview asset.",
]


def clamp(value, low, high):
    return max(low, min(high, value))


def as_number(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def read_project():
    project = {"orientation": "horizontal", "confirmed": False}
    try:
        project.update(json.loads(PROJECT_PATH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        pass
    if project["orientation"] not in CANVAS_SIZES:
        project["orientation"] = "horizontal"
    return project


def canvas_for(orientation):
    orientation = orientation if orientation in CANVAS_SIZES else "horizontal"
    width, height, ratio = CANVAS_SIZES[orientation]
    return {"orientation": orientation, "aspect_ratio": ratio, "width": width, "height": height}


def probe_video(path):
    """Return display width/height (rotation applied), duration and audio flag."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is not installed or is not on PATH. Install ffmpeg first.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stderr.strip() or "Could not inspect the video.") from exc
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError("No video stream was found in this file.")
    width, height = int(video["width"]), int(video["height"])
    rotation = video.get("tags", {}).get("rotate")
    for side in video.get("side_data_list", []) or []:
        if "rotation" in side:
            rotation = side["rotation"]
    if abs(int(as_number(rotation))) % 180 == 90:
        width, height = height, width
    duration = 0.0
    for value in (video.get("duration"), data.get("format", {}).get("duration")):
        duration = as_number(value)
        if duration > 0:
            break
    orientation = "vertical" if height > width else "horizontal" if width > height else "square"
    return {
        "width": width,
        "height": height,
        "duration": round(duration, 3),
        "orientation": orientation,
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def probe_summary(path):
    try:
        return probe_video(path)
    except (RuntimeError, KeyError, ValueError):
        return {}


def ensure_clip_info(clip):
    """Clips uploaded before this feature have no size info; add it once."""
    if "width" not in clip:
        info = probe_summary(clip_source(clip))
        if info:
            clip.update(info)
            clip_metadata_path(clip["clip_id"]).write_text(json.dumps(clip, indent=2), encoding="utf-8")
    return clip


def clip_trim(clip, duration):
    start = clamp(as_number(clip.get("trim_start"), 0), 0, max(0, duration - 0.05))
    end = clamp(as_number(clip.get("trim_end"), duration), start + 0.05, duration)
    return round(start, 3), round(end, 3)


def clip_info(clip):
    try:
        return probe_video(clip_source(clip))
    except RuntimeError:
        if clip.get("width") and clip.get("height"):
            return {key: clip.get(key) for key in ("width", "height", "duration", "orientation", "has_audio")}
        raise


def role_aspect(role, canvas, split=None):
    """Aspect ratio of a source region in the generated canvas."""
    aspect = canvas["width"] / canvas["height"]
    if role == "full":
        return aspect
    if role == "inset":
        return 1.0
    split = split or {"direction": "vertical" if canvas["orientation"] == "horizontal" else "horizontal", "ratio": 0.5}
    ratio = split["ratio"] if role == "pane_2" else 1 - split["ratio"]
    return aspect * ratio if split["direction"] == "vertical" else aspect / ratio


def rounded_region(region):
    for key in ("x", "y", "w", "h"):
        region[key] = round(region[key], 5)
    return region


def default_region(role, aspect, sw, sh):
    """Largest box of the right aspect ratio, centered (panes and inset are nudged)."""
    width = min(1.0, aspect * sh / sw)
    height = width * sw / (aspect * sh)
    scale, cx, cy = {"inset": (0.5, 0.5, 0.4), "pane_1": (1.0, 0.3, 0.5), "pane_2": (1.0, 0.7, 0.5)}.get(role, (1.0, 0.5, 0.5))
    width, height = width * scale, height * scale
    region = {"x": clamp(cx - width / 2, 0, 1 - width), "y": clamp(cy - height / 2, 0, 1 - height), "w": width, "h": height, "mirror": False}
    if role == "inset":
        region["shape"] = "circle"
    return rounded_region(region)


def conform_region(region, aspect, sw, sh):
    """Keep the region's centre and width but force the aspect ratio and stay inside the frame."""
    try:
        x, y, w, h = (float(region[key]) for key in ("x", "y", "w", "h"))
    except (KeyError, TypeError, ValueError):
        return None
    cx, cy = x + w / 2, y + h / 2
    w = clamp(w, 0.02, 1.0)
    h = w * sw / (aspect * sh)
    if h > 1.0:
        h = 1.0
        w = h * aspect * sh / sw
    return rounded_region({"x": clamp(cx - w / 2, 0, 1 - w), "y": clamp(cy - h / 2, 0, 1 - h), "w": w, "h": h})


def normalize_segments(mode, segments, duration):
    duration = duration if duration and duration > 0 else 3600.0
    if mode != "smart":
        return [{"start": 0.0, "end": round(duration, 3), "layout": mode}]
    cleaned, cursor = [], 0.0
    candidates = [s for s in (segments or []) if isinstance(s, dict)]
    for segment in sorted(candidates, key=lambda s: as_number(s.get("start"))):
        layout = segment.get("layout") if segment.get("layout") in SEGMENT_LAYOUTS else "full"
        end = clamp(as_number(segment.get("end"), duration), cursor, duration)
        if end - cursor < 0.05:
            continue
        cleaned.append({"start": round(cursor, 3), "end": round(end, 3), "layout": layout})
        cursor = end
    if not cleaned:
        return [{"start": 0.0, "end": round(duration, 3), "layout": "full"}]
    cleaned[-1]["end"] = round(duration, 3)
    return cleaned


def normalize_layout(layout, info, canvas):
    """Validate whatever the browser sent and fill in anything missing."""
    layout = layout if isinstance(layout, dict) else {}
    sw, sh = int(info["width"]), int(info["height"])
    mode = layout.get("mode") if layout.get("mode") in LAYOUT_MODES else "overlay"
    incoming = layout.get("regions") if isinstance(layout.get("regions"), dict) else {}
    split_in = layout.get("split") if isinstance(layout.get("split"), dict) else {}
    split = {
        "direction": split_in.get("direction") if split_in.get("direction") in {"horizontal", "vertical"} else ("vertical" if canvas["orientation"] == "horizontal" else "horizontal"),
        "ratio": round(clamp(as_number(split_in.get("ratio"), 0.5), 0.25, 0.75), 3),
        "source_side": "first" if split_in.get("source_side") == "first" else "second",
    }
    regions = {}
    for role in REGION_ROLES:
        aspect = role_aspect(role, canvas, split)
        source = incoming.get(role) if isinstance(incoming.get(role), dict) else {}
        region = conform_region(source, aspect, sw, sh) or default_region(role, aspect, sw, sh)
        region["mirror"] = bool(source.get("mirror"))
        if role == "inset":
            region["shape"] = "square" if source.get("shape") == "square" else "circle"
        regions[role] = region
    overlay_in = layout.get("overlay") if isinstance(layout.get("overlay"), dict) else {}
    border_color = overlay_in.get("border_color", "#ffffff")
    if not isinstance(border_color, str) or len(border_color) != 7 or border_color[0] != "#" or any(ch not in "0123456789abcdefABCDEF" for ch in border_color[1:]):
        border_color = "#ffffff"
    overlay = {
        "position": overlay_in.get("position") if overlay_in.get("position") in OVERLAY_POSITIONS else "bottom-right",
        "size": round(clamp(as_number(overlay_in.get("size"), 0.3), 0.1, 0.6), 3),
        "margin": round(clamp(as_number(overlay_in.get("margin"), 0.04), 0, 0.2), 3),
        "x": round(clamp(as_number(overlay_in.get("x"), 0.5), 0, 1), 3),
        "y": round(clamp(as_number(overlay_in.get("y"), 0.5), 0, 1), 3),
        "border_width": round(clamp(as_number(overlay_in.get("border_width"), 2), 0, 12), 1),
        "border_color": border_color,
        "shadow": bool(overlay_in.get("shadow", True)),
    }
    return {"mode": mode, "regions": regions, "overlay": overlay, "split": split, "segments": normalize_segments(mode, layout.get("segments"), info.get("duration") or 0)}


def region_px(region, sw, sh):
    x = min(int(round(region["x"] * sw)), sw - 2)
    y = min(int(round(region["y"] * sh)), sh - 2)
    w = max(2, min(int(round(region["w"] * sw)), sw - x))
    h = max(2, min(int(round(region["h"] * sh)), sh - y))
    return {"x": x, "y": y, "w": w, "h": h}


def render_source_clip(clip, job_dir, index, width, height):
    """Normalize source clips for concatenation without baking in overlay placement."""
    source = clip_source(clip)
    info = probe_video(source)
    output = job_dir / f"source-{index:03d}.mp4"
    trim_start, trim_end = clip_trim(clip, info["duration"])
    args = ["-ss", str(trim_start), "-i", str(source)]
    if info["has_audio"]:
        audio_map = ["-map", "0:a:0"]
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        audio_map = ["-map", "1:a:0"]
    args += ["-map", "0:v:0", *audio_map, "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-t", str(trim_end - trim_start), "-shortest", str(output)]
    run_ffmpeg(args)
    return output


def safe_job_dir(job_id):
    if not isinstance(job_id, str) or len(job_id) != 32 or any(ch not in "0123456789abcdef" for ch in job_id):
        return None
    path = OUTPUT_DIR / job_id
    return path if path.is_dir() else None


def source_fingerprint(clip_ids):
    """Only edits that change the merged source invalidate its saved transcript."""
    source = []
    for clip_id in clip_ids:
        clip = read_clip(clip_id)
        if not clip:
            return None
        path = clip_source(clip)
        if not path.is_file():
            return None
        stat = path.stat()
        source.append({"clip_id": clip_id, "filename": clip["filename"],
                       "trim_start": clip.get("trim_start"), "trim_end": clip.get("trim_end"),
                       "settings": clip.get("settings"), "size": stat.st_size,
                       "mtime_ns": stat.st_mtime_ns})
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode("utf-8")).hexdigest()


def build_layout_manifest(clip_ids=None):
    """The JSON that tells the server / LLM what to show, what to hide and how."""
    project = read_project()
    canvas = canvas_for(project["orientation"])
    if not clip_ids:
        found = []
        for metadata_path in CLIPS_DIR.glob("*/metadata.json"):
            try:
                found.append(json.loads(metadata_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        clip_ids = [c["clip_id"] for c in sorted(found, key=lambda c: c.get("name", ""))]
    entries = []
    for clip_id in clip_ids:
        clip = read_clip(clip_id)
        if not clip:
            continue
        info = clip_info(clip)
        trim_start, trim_end = clip_trim(clip, info["duration"])
        layout = normalize_layout(clip.get("layout"), {**info, "duration": trim_end - trim_start}, canvas)
        regions = {}
        for role, region in layout["regions"].items():
            regions[role] = {**region, "aspect": round(role_aspect(role, canvas, layout["split"]), 5), "px": region_px(region, info["width"], info["height"])}
        entries.append({
            "clip_id": clip_id,
            "index": len(entries),
            "name": clip.get("name"),
            "file": clip.get("filename"),
            "source_file": f"output/clips/{clip_id}/{clip['filename']}",
            "source": {**{key: info.get(key) for key in ("width", "height", "orientation", "has_audio")}, "duration": round(trim_end - trim_start, 3), "trim_start": trim_start, "trim_end": trim_end},
            "mode": layout["mode"],
            "regions": regions,
            "overlay": layout["overlay"],
            "split": layout["split"],
            "segments": layout["segments"],
        })
    timeline, offset = [], 0.0
    for entry in entries:
        for segment in entry["segments"]:
            timeline.append({"clip_id": entry["clip_id"], "start": round(offset + segment["start"], 3), "end": round(offset + segment["end"], 3), "mode": segment["layout"]})
        offset += entry["source"]["duration"] or 0
    return {
        "schema": "wishper.overlay/2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "canvas": canvas,
        "clips": entries,
        "timeline": timeline,
        "semantics": LAYOUT_SEMANTICS,
    }


def build_layout_instructions(layout):
    """Turn the saved composition timeline into instructions an agent can read."""
    canvas = layout["canvas"]
    lines = [
        f"Generated canvas: {canvas['aspect_ratio']} {canvas['orientation']} ({canvas['width']}x{canvas['height']}).",
        "The uploaded source footage is not the generated background. Follow the timeline below; times are absolute in the prepared source sequence.",
        "Use overlay.clips and overlay.timeline in this package as the authoritative source for exact timing and geometry. Clip crop coordinates refer to the original source files, not the padded merged preview.",
    ]
    clips = {clip["clip_id"]: clip for clip in layout["clips"]}
    clip_starts = {}
    for item in layout["timeline"]:
        clip = clips[item["clip_id"]]
        mode = item["mode"]
        clip_starts.setdefault(item["clip_id"], item["start"])
        original_start = clip["source"].get("trim_start", 0) + item["start"] - clip_starts[item["clip_id"]]
        original_end = original_start + item["end"] - item["start"]
        prefix = (f"- {format_timestamp(item['start'], True)}–{format_timestamp(item['end'], True)} "
                  f"(source clip {clip['index'] + 1}, original time {format_timestamp(original_start, True)}–{format_timestamp(original_end, True)}): ")
        if mode == "overlay":
            overlay = clip["overlay"]
            region = clip["regions"]["inset"]
            shape = region["shape"]
            position = overlay["position"]
            if position == "custom":
                placement = f"custom top-left position x={overlay['x'] * 100:g}% of canvas width, y={overlay['y'] * 100:g}% of canvas height (clamped inside the canvas)"
            else:
                placement = f"{position} with {overlay['margin'] * 100:g}% margin relative to the shorter canvas side"
            border = f"{overlay['border_width']:g}px {overlay['border_color']} border" if overlay["border_width"] else "no border"
            description = (f"overlay: generate background visuals; show the source as a {shape} inset at {placement}, "
                           f"size {overlay['size'] * 100:g}% of the shorter canvas side, {border}, "
                           f"{'with' if overlay['shadow'] else 'without'} shadow")
            role = "inset"
        elif mode == "split":
            split = clip["split"]
            side = ("left" if split["source_side"] == "first" else "right") if split["direction"] == "vertical" else ("top" if split["source_side"] == "first" else "bottom")
            dimension = "width" if split["direction"] == "vertical" else "height"
            description = f"split screen: show the source on the {side}, occupying {split['ratio'] * 100:g}% of canvas {dimension}; generate visuals for the remaining area"
            role = "pane_2"
        else:
            description = "full frame: show the source across the canvas; do not generate background visuals for this range"
            role = "full"
        crop = clip["regions"][role]
        px = crop["px"]
        original = clip["source"]
        details = (f"Crop from original {original['width']}x{original['height']} source: "
                   f"x={px['x']}, y={px['y']}, width={px['w']}, height={px['h']} pixels")
        if crop["mirror"]:
            details += "; mirror horizontally"
        if clip.get("source_file"):
            details += f"; source file: {clip['source_file']}"
        lines.append(prefix + description + ". " + details + ".")
    return "\n".join(lines)


@app.get("/api/project")
def get_project():
    project = read_project()
    return jsonify(project=project, canvas=canvas_for(project["orientation"]))


@app.post("/api/project")
def set_project():
    data = request.get_json(silent=True) or {}
    orientation = data.get("orientation")
    if orientation not in CANVAS_SIZES:
        return jsonify(error="Choose horizontal (16:9) or vertical (9:16)."), 400
    project = read_project()
    project.update({"orientation": orientation, "confirmed": True})
    PROJECT_PATH.write_text(json.dumps(project, indent=2), encoding="utf-8")
    canvas = canvas_for(orientation)
    clips = []
    for metadata_path in CLIPS_DIR.glob("*/metadata.json"):
        try:
            clip = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if clip.get("layout"):
            # Regions are locked to the canvas' aspect ratio, so re-fit them.
            try:
                info = clip_info(clip)
                trim_start, trim_end = clip_trim(clip, info["duration"])
                clip["layout"] = normalize_layout(clip["layout"], {**info, "duration": trim_end - trim_start}, canvas)
                metadata_path.write_text(json.dumps(clip, indent=2), encoding="utf-8")
            except RuntimeError:
                pass
        clips.append(clip_response(clip))
    return jsonify(project=project, canvas=canvas, clips=clips)


@app.post("/api/project/order")
def save_project_order():
    clip_ids = (request.get_json(silent=True) or {}).get("clip_ids")
    if not isinstance(clip_ids, list) or any(not isinstance(clip_id, str) for clip_id in clip_ids) or len(set(clip_ids)) != len(clip_ids) or any(not read_clip(clip_id) for clip_id in clip_ids):
        return jsonify(error="The source sequence contains an invalid clip."), 400
    project = read_project()
    project["clip_order"] = clip_ids
    PROJECT_PATH.write_text(json.dumps(project, indent=2), encoding="utf-8")
    return jsonify(clip_order=clip_ids)


@app.post("/api/clips/<clip_id>/layout")
def save_layout(clip_id):
    clip = read_clip(clip_id)
    if not clip:
        return jsonify(error="Clip not found."), 404
    try:
        info = clip_info(clip)
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 422
    canvas = canvas_for(read_project()["orientation"])
    trim_start, trim_end = clip_trim(clip, info["duration"])
    clip["layout"] = normalize_layout(request.get_json(silent=True) or {}, {**info, "duration": trim_end - trim_start}, canvas)
    clip_metadata_path(clip_id).write_text(json.dumps(clip, indent=2), encoding="utf-8")
    return jsonify(clip=clip_response(clip))


@app.post("/api/layout/export")
def export_layout():
    data = request.get_json(silent=True) or {}
    try:
        manifest = build_layout_manifest(data.get("clip_ids") or None)
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 422
    (LAYOUTS_DIR / "layout.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify(layout_url="/output/layouts/layout.json", manifest=manifest)


@app.delete("/api/clips/<clip_id>")
def delete_clip(clip_id):
    if not isinstance(clip_id, str) or len(clip_id) != 32 or any(ch not in "0123456789abcdef" for ch in clip_id):
        return jsonify(error="Clip not found."), 404
    clip_dir = CLIPS_DIR / clip_id
    if not clip_dir.is_dir():
        return jsonify(error="Clip not found."), 404
    import shutil
    shutil.rmtree(clip_dir)
    return jsonify(ok=True)


@app.get("/api/clips")
def list_clips():
    clips = []
    for metadata_path in CLIPS_DIR.glob("*/metadata.json"):
        try:
            clips.append(clip_response(ensure_clip_info(json.loads(metadata_path.read_text(encoding="utf-8")))))
        except (OSError, json.JSONDecodeError):
            continue
    return jsonify(clips=clips)


@app.post("/api/clips/upload")
def upload_clips():
    uploads = request.files.getlist("videos")
    if not uploads:
        return jsonify(error="Choose at least one video clip."), 400
    created = []
    for uploaded in uploads:
        if not uploaded.filename or not allowed_file(uploaded.filename):
            continue
        clip_id = uuid.uuid4().hex
        clip_dir = CLIPS_DIR / clip_id
        clip_dir.mkdir(parents=True)
        suffix = Path(secure_filename(uploaded.filename)).suffix.lower() or ".mp4"
        filename = f"original{suffix}"
        uploaded.save(clip_dir / filename)
        clip = {"clip_id": clip_id, "name": secure_filename(uploaded.filename), "filename": filename, "original_filename": filename, "effect": "none", "settings": default_settings(), **probe_summary(clip_dir / filename)}
        if clip.get("width") and clip.get("height"):
            clip["layout"] = normalize_layout({"mode": "overlay"}, clip, canvas_for(read_project()["orientation"]))
        (clip_dir / "metadata.json").write_text(json.dumps(clip, indent=2), encoding="utf-8")
        created.append(clip_response(clip))
    if not created:
        return jsonify(error="No supported video files were uploaded."), 400
    return jsonify(clips=created)


@app.post("/api/clips/<clip_id>/effect")
def effect_clip(clip_id):
    clip = read_clip(clip_id)
    effect = request.json.get("effect", "none") if request.is_json else "none"
    filters = {
        "none": None,
        "noise": "afftdn",
        "sunlight": "eq=brightness=0.08:saturation=1.25:contrast=1.05",
        "lighting": "eq=brightness=0.16:contrast=1.08",
        "blackwhite": "hue=s=0",
    }
    if not clip or effect not in filters:
        return jsonify(error="Clip or effect not found."), 404
    source = clip_source(clip)
    output = source.parent / "processed.mp4"
    if effect == "none":
        clip["filename"] = Path(clip["name"]).name
        if not (source.parent / clip["filename"]).exists():
            clip["filename"] = "original" + source.suffix
    else:
        args = ["-i", str(source), "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac", "-shortest"]
        if effect == "noise":
            args += ["-af", filters[effect]]
        else:
            args += ["-vf", filters[effect]]
        args.append(str(output))
        try:
            run_ffmpeg(args)
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 422
        clip["filename"] = "processed.mp4"
    clip["effect"] = effect
    clip_metadata_path(clip_id).write_text(json.dumps(clip, indent=2), encoding="utf-8")
    return jsonify(clip=clip_response(clip))


def normalize_settings(values):
    settings = default_settings()
    for key in settings:
        if key in {"noise_type", "audio_mode", "hum_frequency", "audio_algorithm"}:
            settings[key] = values.get(key, settings[key])
            continue
        try:
            settings[key] = float(values.get(key, settings[key]))
        except (TypeError, ValueError):
            pass
    settings["brightness"] = max(-1, min(1, settings["brightness"]))
    settings["contrast"] = max(0, min(3, settings["contrast"]))
    settings["saturation"] = max(0, min(3, settings["saturation"]))
    settings["sharpness"] = max(0, min(1, settings["sharpness"]))
    settings["blur"] = max(0, min(20, settings["blur"]))
    settings["video_noise"] = max(0, min(100, settings["video_noise"]))
    settings["audio_noise"] = max(0, min(100, settings["audio_noise"]))
    settings["voice_enhance"] = max(0, min(100, settings["voice_enhance"]))
    if settings.get("noise_type") not in {"general", "fan", "ac", "bus"}:
        settings["noise_type"] = "general"
    if settings.get("audio_mode") not in {"manual", "auto"}:
        settings["audio_mode"] = "manual"
    if settings.get("hum_frequency") not in {"auto", "off", "50", "60"}:
        settings["hum_frequency"] = "auto"
    if settings.get("audio_algorithm") not in {"afftdn", "afwtdn", "anlmdn"}:
        settings["audio_algorithm"] = "afftdn"
    settings["remove_rumble"] = 1 if settings["remove_rumble"] else 0
    settings["reduce_hiss"] = 1 if settings["reduce_hiss"] else 0
    settings["normalize_audio"] = 1 if settings["normalize_audio"] else 0
    settings["speed"] = max(.25, min(4, settings["speed"]))
    settings["rotate"] = max(-360, min(360, settings["rotate"]))
    settings["fade_in"] = max(0, min(30, settings["fade_in"]))
    settings["fade_out"] = max(0, min(30, settings["fade_out"]))
    return settings


@app.post("/api/clips/<clip_id>/trim")
def save_clip_trim(clip_id):
    clip = read_clip(clip_id)
    if not clip:
        return jsonify(error="Clip not found."), 404
    duration = clip_info(clip)["duration"]
    data = request.get_json(silent=True) or {}
    start, end = as_number(data.get("start"), -1), as_number(data.get("end"), -1)
    if not 0 <= start < end <= duration + 0.001 or end - start < 0.05:
        return jsonify(error=f"Trim must be within 0–{duration:.1f}s and at least 0.05s long."), 400
    clip["trim_start"], clip["trim_end"] = round(start, 3), round(end, 3)
    if clip.get("layout"):
        clip["layout"] = normalize_layout(clip["layout"], {**clip_info(clip), "duration": end - start}, canvas_for(read_project()["orientation"]))
    clip_metadata_path(clip_id).write_text(json.dumps(clip, indent=2), encoding="utf-8")
    return jsonify(clip=clip_response(clip))


@app.post("/api/clips/<clip_id>/settings")
def save_settings(clip_id):
    clip = read_clip(clip_id)
    if not clip:
        return jsonify(error="Clip not found."), 404
    clip["settings"] = normalize_settings(request.json or {})
    clip_metadata_path(clip_id).write_text(json.dumps(clip, indent=2), encoding="utf-8")
    return jsonify(clip=clip_response(clip))


@app.post("/api/clips/<clip_id>/process")
def process_clip(clip_id):
    clip = read_clip(clip_id)
    if not clip:
        return jsonify(error="Clip not found."), 404
    settings = normalize_settings(clip.get("settings", {}))
    source = clip_original_source(clip)
    output = source.parent / "processed.mp4"
    video_filters = []
    if settings["brightness"] or settings["contrast"] != 1 or settings["saturation"] != 1:
        video_filters.append(f"eq=brightness={settings['brightness']}:contrast={settings['contrast']}:saturation={settings['saturation']}")
    if settings["video_noise"]:
        strength = settings["video_noise"] / 100
        video_filters.append(f"hqdn3d={1 + strength * 4}:{1 + strength * 4}:{2 + strength * 6}:{2 + strength * 6}")
    if settings["sharpness"]:
        video_filters.append(f"unsharp=5:5:{settings['sharpness'] * 2}:5:5:0")
    if settings["blur"]:
        video_filters.append(f"boxblur={settings['blur']}:1")
    if settings["rotate"]:
        video_filters.append(f"rotate={settings['rotate']}*PI/180:ow=rotw({settings['rotate']}*PI/180):oh=roth({settings['rotate']}*PI/180)")
    if settings["fade_in"]:
        video_filters.append(f"fade=t=in:st=0:d={settings['fade_in']}")
    audio_filters = []
    noise_strength = settings["audio_noise"] / 100
    if settings["audio_mode"] == "auto" and not settings["audio_noise"]:
        noise_strength = .30
    if settings["remove_rumble"]:
        audio_filters.append("highpass=f=80")
    hum = settings["hum_frequency"]
    if hum == "auto":
        hum = "off"  # conservative auto mode avoids damaging nearby voice frequencies
    if hum in {"50", "60"}:
        base = int(hum)
        for harmonic in (base, base * 2, base * 3, base * 4):
            audio_filters.append(f"equalizer=f={harmonic}:t=q:w=1:g=-18")
    if noise_strength:
        if settings["noise_type"] == "fan":
            audio_filters += ["highpass=f=70", "lowpass=f=11000"]
        elif settings["noise_type"] == "ac":
            audio_filters += ["highpass=f=100", "lowpass=f=10000"]
        elif settings["noise_type"] == "bus":
            audio_filters += ["highpass=f=130", "lowpass=f=8500"]
        reduction_db = 6 + (noise_strength * 18)
        if settings["audio_algorithm"] == "afwtdn":
            audio_filters.append(f"afwtdn=sigma={0.02 + noise_strength * .18:.3f}:percent={40 + noise_strength * 60:.1f}:adaptive=1")
        elif settings["audio_algorithm"] == "anlmdn":
            audio_filters.append(f"anlmdn=strength={1 + noise_strength * 8:.2f}:smooth=11")
        else:
            audio_filters.append(f"afftdn=nr={reduction_db:.1f}:nf=-50:tn=1")
    if settings["reduce_hiss"]:
        audio_filters.append("lowpass=f=16000")
    if settings["voice_enhance"]:
        audio_filters += ["highpass=f=80", "lowpass=f=12000", "acompressor=threshold=0.08:ratio=2:attack=20:release=200"]
    if settings["normalize_audio"]:
        audio_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    if audio_filters:
        audio_filters.append("alimiter=limit=0.95")
    if settings["speed"] != 1:
        video_filters.append(f"setpts={1 / settings['speed']}*PTS")
        audio_filters.append(f"atempo={settings['speed']}")
    has_audio = bool(audio_stream_details(source))
    if audio_filters and not has_audio:
        if settings["audio_noise"] or settings["voice_enhance"]:
            return jsonify(error="This video has no readable audio stream to clean."), 422
        audio_filters = []  # nothing to clean; merge adds silence for clips without audio
    args = ["-i", str(source), "-map", "0:v:0", "-map", "0:a?", "-c:a", "aac"]
    if video_filters:
        args += ["-vf", ",".join(video_filters), "-c:v", "libx264", "-preset", "fast", "-crf", "22"]
    else:
        args += ["-c:v", "copy"]
    if audio_filters:
        args += ["-af", ",".join(audio_filters)]
    args += ["-movflags", "+faststart", str(output)]
    try:
        run_ffmpeg(args)
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 422
    clip["filename"] = "processed.mp4"
    clip["settings"] = settings
    clip_metadata_path(clip_id).write_text(json.dumps(clip, indent=2), encoding="utf-8")
    return jsonify(clip=clip_response(clip))


@app.post("/api/clips/process-all")
def process_all_clips():
    results = []
    for metadata_path in CLIPS_DIR.glob("*/metadata.json"):
        clip = json.loads(metadata_path.read_text(encoding="utf-8"))
        if any(float(value) != float(default_settings()[key]) for key, value in clip.get("settings", {}).items() if key in default_settings()):
            response = process_clip(clip["clip_id"])
            if response[1] if isinstance(response, tuple) else False:
                return response
            results.append(clip["clip_id"])
    return jsonify(processed=results)


@app.post("/api/merge")
def merge_clips():
    clip_ids = (request.get_json(silent=True) or {}).get("clip_ids", [])
    if not isinstance(clip_ids, list) or not clip_ids or any(not isinstance(clip_id, str) for clip_id in clip_ids) or len(set(clip_ids)) != len(clip_ids):
        return jsonify(error="Choose one or more unique clips for the source sequence."), 400
    clips = [read_clip(clip_id) for clip_id in clip_ids]
    if any(clip is None for clip in clips):
        return jsonify(error="A source clip could not be found. Refresh the page and try again."), 400
    job_id = uuid.uuid4().hex
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir()
    merged_path = job_dir / "merged.mp4"
    concat_file = job_dir / "concat.txt"
    try:
        first = probe_video(clip_source(clips[0]))
        if first["width"] <= 0 or first["height"] <= 0:
            raise RuntimeError("Could not read the source video dimensions.")
        width = min(first["width"], 1280)
        height = max(2, round(width * first["height"] / first["width"]))
        width += width % 2
        height += height % 2
        normalized = [render_source_clip(clip, job_dir, index, width, height) for index, clip in enumerate(clips)]
        concat_file.write_text("\n".join(f"file '{path.as_posix().replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'" for path in normalized) + "\n", encoding="utf-8")
        run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", str(merged_path)])
        info = probe_video(merged_path)
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 422
    (job_dir / "source-order.json").write_text(json.dumps(clip_ids), encoding="utf-8")
    preparation = {"job_id": job_id, "video_url": f"/output/{job_id}/merged.mp4",
                   "clip_count": len(clips), "duration": info["duration"],
                   "source": {"width": info["width"], "height": info["height"]},
                   "fingerprint": source_fingerprint(clip_ids)}
    (job_dir / "preparation.json").write_text(json.dumps(preparation), encoding="utf-8")
    project = read_project()
    project.update({"clip_order": clip_ids, "prepared_job_id": job_id})
    PROJECT_PATH.write_text(json.dumps(project, indent=2), encoding="utf-8")
    try:
        metadata = transcribe(merged_path, job_dir)
        return jsonify(**{key: value for key, value in preparation.items() if key != "fingerprint"},
                       language=metadata["language"], segments=metadata["segments"],
                       captions_url=f"/output/{job_id}/captions.vtt")
    except Exception as exc:
        # Keep the merged video so the same Prepare button can retry transcription.
        (job_dir / "error.txt").write_text(str(exc) + "\n", encoding="utf-8")
        return jsonify(**{key: value for key, value in preparation.items() if key != "fingerprint"},
                       transcription_error=str(exc))


@app.post("/api/jobs/<job_id>/transcribe")
def transcribe_prepared_source(job_id):
    job_dir = safe_job_dir(job_id)
    if not job_dir or not (job_dir / "merged.mp4").is_file():
        return jsonify(error="Prepare the source video before transcribing it."), 404
    try:
        metadata = transcribe(job_dir / "merged.mp4", job_dir)
    except Exception as exc:
        return jsonify(error=str(exc)), 422
    return jsonify(job_id=job_id, language=metadata["language"], segments=metadata["segments"], captions_url=f"/output/{job_id}/captions.vtt")


@app.get("/api/workflow")
def get_workflow():
    """Restore only a preparation that still matches the current source sequence."""
    project = read_project()
    job_dir = safe_job_dir(project.get("prepared_job_id"))
    if not job_dir or not (job_dir / "merged.mp4").is_file():
        return jsonify(prepared=None)
    try:
        preparation = json.loads((job_dir / "preparation.json").read_text(encoding="utf-8"))
        clip_ids = json.loads((job_dir / "source-order.json").read_text(encoding="utf-8"))
        if clip_ids != project.get("clip_order") or preparation["fingerprint"] != source_fingerprint(clip_ids):
            return jsonify(prepared=None)
        transcript_path = job_dir / "transcript.json"
        transcript = json.loads(transcript_path.read_text(encoding="utf-8")) if transcript_path.is_file() else None
    except (OSError, ValueError, KeyError):
        return jsonify(prepared=None)
    job_id = job_dir.name
    package_path = job_dir / "server-package.json"
    package_current = package_path.is_file() and all(
        path.stat().st_mtime_ns <= package_path.stat().st_mtime_ns
        for path in [PROJECT_PATH, transcript_path, *(clip_metadata_path(clip_id) for clip_id in clip_ids)]
        if path.is_file()
    )
    handoff = None
    if package_path.is_file():
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
            handoff = {"style_id": package.get("style_id"), "user_prompt": package.get("user_prompt", ""),
                       "music": package.get("music")}
        except (OSError, ValueError):
            pass
    result_url = None
    result_is_current = False
    result_record = job_dir / "result.json"
    if result_record.is_file():
        try:
            result = json.loads(result_record.read_text(encoding="utf-8"))
            filename = result["filename"]
            if (isinstance(filename, str) and filename.startswith("generated-")
                    and filename.endswith(".mp4") and len(filename) == 46
                    and (job_dir / filename).is_file()):
                result_url = f"/output/{job_id}/{filename}"
                result_is_current = package_current and result.get("package_mtime_ns") == package_path.stat().st_mtime_ns
        except (OSError, ValueError, KeyError):
            pass
    elif (job_dir / "generated.mp4").is_file():
        result_url = f"/output/{job_id}/generated.mp4"
    remote_job_id = None
    remote_record = job_dir / "remote-job.json"
    if remote_record.is_file():
        try:
            remote_job_id = stored_remote_job_id(json.loads(remote_record.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, RuntimeError):
            pass
    return jsonify(prepared={key: value for key, value in preparation.items() if key != "fingerprint"},
                   transcript=transcript,
                   captions_url=f"/output/{job_id}/captions.vtt" if transcript else None,
                   package_url=f"/output/{job_id}/server-package.json" if package_current else None,
                   handoff=handoff, remote_job_id=remote_job_id,
                   result_url=result_url, result_is_current=result_is_current)


@app.put("/api/jobs/<job_id>/transcript")
def update_transcript(job_id):
    job_dir = safe_job_dir(job_id)
    if not job_dir or not (job_dir / "transcript.json").is_file():
        return jsonify(error="Transcript not found."), 404
    data = request.get_json(silent=True)
    segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segments, list) or not segments:
        return jsonify(error="Transcript needs at least one caption."), 400
    duration = probe_video(job_dir / "merged.mp4")["duration"]
    cleaned = []
    for item in segments:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not item["text"].strip():
            return jsonify(error="Every caption needs text."), 400
        start, end = as_number(item.get("start"), -1), as_number(item.get("end"), -1)
        if not 0 <= start < end <= duration + 0.5:
            return jsonify(error="Caption times must fit the prepared video."), 400
        cleaned.append({"start": start, "end": end, "text": item["text"].strip()})
    path = job_dir / "transcript.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["segments"] = cleaned
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (job_dir / "transcript.txt").write_text(
        "\n".join(f"[{format_timestamp(item['start'])}-{format_timestamp(item['end'])}] {item['text']}" for item in cleaned) + "\n",
        encoding="utf-8")
    write_vtt(cleaned, job_dir / "captions.vtt")
    return jsonify(job_id=job_id, segments=cleaned, captions_url=f"/output/{job_id}/captions.vtt")


def transcribe(video_path, job_dir):
    audio_path = job_dir / "audio.wav"
    frames_dir = job_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    audio_streams = audio_stream_details(video_path)
    if not audio_streams:
        raise RuntimeError("No audio stream was detected by ffprobe. If the video plays sound, it may be a separate audio track or an unsupported container.")

    # Whisper receives a clean mono wav, while the frames make the job ready for
    # the later Claude step without needing to touch the original video again.
    run_ffmpeg(["-i", str(video_path), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio_path)])
    run_ffmpeg(["-i", str(video_path), "-vf", "fps=1/5", "-frames:v", "20", str(frames_dir / "frame-%03d.jpg")])

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is not installed. Run: pip install -r requirements.txt") from exc

    model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
    detected_segments, info = model.transcribe(str(audio_path), language=None, vad_filter=True)
    segments = []
    for segment in detected_segments:
        text = segment.text.strip()
        if text:
            segments.append({"start": round(segment.start, 3), "end": round(segment.end, 3), "text": text})

    metadata = {
        "job_id": job_dir.name,
        "model": WHISPER_MODEL,
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "segments": segments,
    }
    (job_dir / "transcript.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (job_dir / "transcript.txt").write_text(
        "\n".join(f"[{format_timestamp(item['start'])}-{format_timestamp(item['end'])}] {item['text']}" for item in segments) + "\n",
        encoding="utf-8",
    )
    write_vtt(segments, job_dir / "captions.vtt")
    return metadata


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/process")
def process_video():
    uploaded = request.files.get("video")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Choose a video file first."), 400
    if not allowed_file(uploaded.filename):
        return jsonify(error=f"Unsupported video type. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}"), 400

    job_id = uuid.uuid4().hex
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True)
    original_name = secure_filename(uploaded.filename) or "video.mp4"
    video_path = job_dir / f"original{Path(original_name).suffix.lower()}"
    try:
        uploaded.save(video_path)
        metadata = transcribe(video_path, job_dir)
    except Exception as exc:
        (job_dir / "error.txt").write_text(str(exc) + "\n", encoding="utf-8")
        return jsonify(error=str(exc), job_id=job_id, video_url=f"/output/{job_id}/{video_path.name}"), 422

    return jsonify({
        "job_id": job_id,
        "language": metadata["language"],
        "language_probability": metadata["language_probability"],
        "segments": metadata["segments"],
        "video_url": f"/output/{job_id}/{video_path.name}",
        "captions_url": f"/output/{job_id}/captions.vtt",
        "files_url": f"/output/{job_id}/",
    })


@app.post("/api/server-package")
def create_server_package():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify(error="Invalid package request."), 400
    # Legacy clients may omit style_id; the new UI always supplies one.
    style_id = data.get("style_id")
    style = None
    if style_id is not None:
        if not isinstance(style_id, str) or not style_id:
            return jsonify(error="Style not found or not ready."), 404
        with connect_styles() as styles_db:
            selected_style = ready_style(styles_db, style_id)
            if selected_style is None:
                return jsonify(error="Style not found or not ready."), 404
            try:
                style = style_reference(selected_style)
            except (OSError, ValueError):
                return jsonify(error="Style preview is out of date. Re-render this style."), 409
    job_id = data.get("job_id")
    job_dir = safe_job_dir(job_id)
    if not job_dir or not (job_dir / "merged.mp4").is_file():
        return jsonify(error="Prepared source video not found."), 404
    prompt = str(data.get("prompt", "")).strip()
    if not prompt:
        return jsonify(error="Enter a generation prompt before sending."), 400
    transcript = data.get("transcript")
    segments = transcript.get("segments") if isinstance(transcript, dict) else None
    if not isinstance(segments, list) or (not segments and not (job_dir / "transcript.json").is_file()):
        return jsonify(error="Prepare the video to create its transcript before sending."), 400
    duration = probe_video(job_dir / "merged.mp4")["duration"]
    for segment in segments:
        if not isinstance(segment, dict) or not isinstance(segment.get("text"), str) or not segment["text"].strip():
            return jsonify(error="Transcript segments must contain text."), 400
        start, end = as_number(segment.get("start"), -1), as_number(segment.get("end"), -1)
        if not 0 <= start < end <= duration + 0.5:
            return jsonify(error="Transcript timestamps must fit the prepared source video."), 400
    try:
        clip_ids = json.loads((job_dir / "source-order.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return jsonify(error="Source sequence record not found."), 422
    if data.get("clip_order") != clip_ids:
        return jsonify(error="The source sequence changed. Prepare it again before sending."), 409
    preparation_path = job_dir / "preparation.json"
    if preparation_path.is_file():
        try:
            preparation = json.loads(preparation_path.read_text(encoding="utf-8"))
            if preparation["fingerprint"] != source_fingerprint(clip_ids):
                return jsonify(error="A source clip changed. Prepare it again before sending."), 409
        except (OSError, ValueError, KeyError):
            return jsonify(error="Source preparation record is invalid. Prepare it again."), 409
    project = read_project()
    if not project.get("confirmed"):
        return jsonify(error="Choose 16:9 or 9:16 for the generated canvas."), 400
    music = data.get("background_sound") or {"id": "none", "enabled": False, "volume": 0}
    if not isinstance(music, dict):
        return jsonify(error="Invalid music configuration."), 400
    try:
        music_volume = float(music.get("volume", 0))
        music_start = float(music.get("start", 0))
    except (TypeError, ValueError):
        return jsonify(error="Music volume and start must be numbers."), 400
    if not 0 <= music_volume <= 1 or music_start < 0:
        return jsonify(error="Music volume must be 0–1 and start cannot be negative."), 400
    music = {**music, "enabled": bool(music.get("enabled")), "volume": music_volume, "start": music_start}
    music_file = music.get("file")
    preset_id = music.get("id")
    preset = MUSIC_PRESET_BY_ID.get(preset_id) if isinstance(preset_id, str) else None
    if preset:
        if music_file != preset["file"] or not (BASE_DIR / preset["file"]).is_file():
            return jsonify(error="The selected built-in music track is unavailable."), 400
        music = {**music, "source": "builtin", "name": preset["name"], "loop": True}
    elif music_file:
        music_path = OUTPUT_DIR / music_file.removeprefix("output/") if isinstance(music_file, str) else None
        if not music_path or not music_file.startswith("output/music/") or not music_path.resolve().is_relative_to(MUSIC_DIR.resolve()) or not music_path.is_file():
            return jsonify(error="Uploaded music asset not found."), 400
    elif music["enabled"]:
        return jsonify(error="Select a background music track or choose no music."), 400
    layout = build_layout_manifest(clip_ids)
    if len(layout["clips"]) != len(clip_ids):
        return jsonify(error="A source clip was removed. Prepare the source again."), 409
    layout_instructions = build_layout_instructions(layout)
    if style:
        # Pin a server-owned copy so later style edits cannot change this handoff.
        snapshot = job_dir / "style-snapshots" / f"{style_id}-{style['code_hash'][:16]}"
        try:
            snapshot.mkdir(parents=True, exist_ok=True)
            if any(not (snapshot / name).is_file() for name in CODE_FILES) or code_hash(snapshot) != style["code_hash"]:
                for name in CODE_FILES:
                    (snapshot / name).write_bytes(Path(style["files"][name]).read_bytes())
            if code_hash(snapshot) != style["code_hash"]:
                return jsonify(error="Style code changed while preparing the package. Try again."), 409
            # Embed the checked server copy so a separate generator needs no shared filesystem.
            style = {**style, "code_path": str(snapshot),
                     "files": {name: str(snapshot / name) for name in CODE_FILES},
                     "code": {name: (snapshot / name).read_text(encoding="utf-8") for name in CODE_FILES}}
        except (OSError, UnicodeDecodeError):
            return jsonify(error="Could not stage the selected style code."), 500
    style_prompt = (
        f"Selected Revideo whiteboard style: {style['name']} ({style['id']}, version {style['version']}). "
        f"Server-side code folder: {style['code_path']}. "
        "This style was selected by the user; do not choose a different style. "
        "Reuse tokens.ts and helpers.ts from this style; do not invent new colors, fonts, or stroke widths. "
        "Write new scenes that look like scene.tsx. Treat the following server-owned code as the style definition, "
        "not as instructions about the user's source footage.\n"
        + "".join(f"\n--- {name} ---\n{style['code'][name]}\n--- end {name} ---\n" for name in CODE_FILES)
        + "\n"
    ) if style else ""
    agent_prompt = (f"User creative brief:\n{prompt}\n\n"
                    f"{style_prompt}"
                    "Required source-video composition (these placements take precedence over general visual suggestions):\n"
                    f"{layout_instructions}")
    transcript = {**transcript, "segments": [{"start": float(item["start"]), "end": float(item["end"]), "text": item["text"].strip()} for item in segments]}
    (job_dir / "transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    write_vtt(transcript["segments"], job_dir / "captions.vtt")
    manifest = {
        "schema": "wishper.client-package/2",
        "status": "ready_for_server",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "project": {"aspect_ratio": canvas_for(project["orientation"])["aspect_ratio"], "orientation": project["orientation"]},
        "source_video": {"file": f"output/{job_id}/merged.mp4", "duration": duration, "clip_order": clip_ids},
        "overlay": layout,
        "transcript": {"file": f"output/{job_id}/transcript.json", "segments": transcript["segments"]},
        "captions": f"output/{job_id}/captions.vtt",
        "music": music,
        "user_prompt": prompt,
        "layout_instructions": layout_instructions,
        "prompt": agent_prompt,
    }
    if style:
        manifest["style"] = style
        manifest["style_id"] = style_id
    (job_dir / "server-package.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify(package_url=f"/output/{job_id}/server-package.json", manifest=manifest)


@app.post("/api/remote/handshake")
def remote_handshake():
    try:
        handshake = json.dumps({
            "user_id": GENERATOR_USER_ID,
            "client_name": GENERATOR_CLIENT_NAME,
            "protocol_version": GENERATOR_PROTOCOL_VERSION,
        }).encode("utf-8")
        status, content_type, raw = remote_http("POST", "/handshake", handshake, "application/json")
        return jsonify(server_url=GENERATOR_SERVER_URL, status=status,
                       message=raw.decode("utf-8", errors="replace"))
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 502


@app.post("/api/remote/generate")
def remote_generate():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    job_dir = safe_job_dir(job_id)
    package_path = job_dir / "server-package.json" if job_dir else None
    if not package_path or not package_path.is_file():
        return jsonify(error="Create the local handoff package first."), 404
    try:
        manifest = json.loads(package_path.read_text(encoding="utf-8"))
        video_path = job_dir / "merged.mp4"
        if not video_path.is_file():
            raise RuntimeError("Prepared source video is missing.")
        body, content_type = multipart_form({
            "user_id": GENERATOR_USER_ID,
            "prompt": remote_generation_prompt(manifest),
        }, files={"video": ("merged.mp4", "video/mp4", video_path.read_bytes())})
        _, response_type, raw = remote_http("POST", "/api/jobs", body, content_type)
        raw_text = raw.decode("utf-8", errors="replace").strip()
        try:
            response_payload = json.loads(raw_text) if "json" in response_type or raw_text.startswith("{") else None
        except json.JSONDecodeError:
            response_payload = None
        if isinstance(response_payload, dict):
            remote_job_id = response_payload.get("job_id") or response_payload.get("id")
        else:
            remote_job_id = raw_text.strip('"')
        if not remote_job_id:
            raise RuntimeError("Generator server returned an empty job ID.")
        record = {"server_url": GENERATOR_SERVER_URL, "remote_job_id": remote_job_id,
                  "submitted_at": datetime.now(timezone.utc).isoformat(),
                  "submission": response_payload or raw_text}
        (job_dir / "remote-job.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return jsonify(job_id=job_id, remote_job_id=remote_job_id, status="submitted")
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        return jsonify(error=str(exc)), 502


@app.get("/api/remote/jobs/<job_id>")
def remote_job_status(job_id):
    local_dir = safe_job_dir(job_id)
    if not local_dir or not (local_dir / "remote-job.json").is_file():
        return jsonify(error="No remote job exists for this preparation."), 404
    try:
        record = json.loads((local_dir / "remote-job.json").read_text(encoding="utf-8"))
        remote_id = urllib.parse.quote(stored_remote_job_id(record), safe="")
        _, content_type, raw = remote_http("GET", f"/api/jobs/{remote_id}")
        if "json" in content_type:
            payload = json.loads(raw.decode("utf-8"))
            text = json.dumps(payload)
            status_value = remote_status_text(payload)
        else:
            payload = raw.decode("utf-8", errors="replace")
            text = payload
            status_value = payload
        normalized = status_value.lower()
        if any(word in normalized for word in ("failed", "error", "cancel")):
            state = "failed"
        elif any(word in normalized for word in ("complete", "completed", "done", "success", "finished")):
            state = "completed"
        else:
            state = "running"
        return jsonify(job_id=job_id, remote_job_id=stored_remote_job_id(record), state=state, response=payload)
    except (RuntimeError, OSError, ValueError, KeyError, UnicodeError) as exc:
        return jsonify(error=str(exc)), 502


@app.post("/api/remote/jobs/<job_id>/import")
def import_remote_result(job_id):
    local_dir = safe_job_dir(job_id)
    if not local_dir or not (local_dir / "remote-job.json").is_file():
        return jsonify(error="No remote job exists for this preparation."), 404
    try:
        record = json.loads((local_dir / "remote-job.json").read_text(encoding="utf-8"))
        remote_id = urllib.parse.quote(stored_remote_job_id(record), safe="")
        _, content_type, raw = remote_http("GET", f"/api/jobs/{remote_id}/video")
        if "json" in content_type:
            payload = json.loads(raw.decode("utf-8"))
            video_url = payload.get("url") or payload.get("video_url") or payload.get("path")
            if not video_url:
                raise RuntimeError("Generator returned JSON without a video URL.")
            if video_url.startswith("/"):
                video_url = f"{GENERATOR_SERVER_URL}{video_url}"
            with urllib.request.urlopen(video_url, timeout=120) as response:
                raw = response.read()
        filename = f"generated-{uuid.uuid4().hex}.mp4"
        candidate = local_dir / f".{filename}"
        candidate.write_bytes(raw)
        info = probe_video(candidate)
        if info["duration"] <= 0:
            raise RuntimeError("The generated video has no playable duration.")
        result = local_dir / filename
        os.replace(candidate, result)
        (local_dir / "result.json").write_text(json.dumps({"filename": filename, "duration": info["duration"],
            "package_mtime_ns": (local_dir / "server-package.json").stat().st_mtime_ns,
            "imported_at": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")
        return jsonify(job_id=job_id, video_url=f"/output/{job_id}/{filename}", duration=info["duration"])
    except (RuntimeError, OSError, ValueError, KeyError, urllib.error.URLError) as exc:
        candidate = locals().get("candidate")
        if candidate:
            candidate.unlink(missing_ok=True)
        return jsonify(error=str(exc)), 502

@app.post("/api/jobs/<job_id>/result")
def import_generated_result(job_id):
    """Local handoff until a separate authenticated server transport is agreed."""
    job_dir = safe_job_dir(job_id)
    if not job_dir or not (job_dir / "server-package.json").is_file():
        return jsonify(error="Create the handoff package before importing a finished video."), 404
    uploaded = request.files.get("video")
    if not uploaded or not uploaded.filename or Path(uploaded.filename).suffix.lower() != ".mp4":
        return jsonify(error="Choose a finished MP4 video."), 400
    filename = f"generated-{uuid.uuid4().hex}.mp4"
    result = job_dir / filename
    candidate = job_dir / f".{filename}"
    try:
        uploaded.save(candidate)
        info = probe_video(candidate)
        if info["duration"] <= 0:
            raise RuntimeError("The finished video has no playable duration.")
        os.replace(candidate, result)
        record = {"filename": filename, "duration": info["duration"],
                  "package_mtime_ns": (job_dir / "server-package.json").stat().st_mtime_ns,
                  "imported_at": datetime.now(timezone.utc).isoformat()}
        (job_dir / "result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        candidate.unlink(missing_ok=True)
        return jsonify(error=str(exc)), 422
    return jsonify(job_id=job_id, video_url=f"/output/{job_id}/{filename}", duration=info["duration"])


@app.post("/api/music/upload")
def upload_music():
    uploaded = request.files.get("music")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Choose an audio file first."), 400
    allowed = {"mp3", "wav", "m4a", "aac", "ogg", "flac"}
    name = secure_filename(uploaded.filename)
    if "." not in name or name.rsplit(".", 1)[1].lower() not in allowed:
        return jsonify(error="Unsupported audio type. Use MP3, WAV, M4A, AAC, OGG, or FLAC."), 400
    asset_id = uuid.uuid4().hex
    path = MUSIC_DIR / f"{asset_id}-{name}"
    uploaded.save(path)
    return jsonify(asset_id=asset_id, name=name, url=f"/output/music/{path.name}", reference=f"output/music/{path.name}")


@app.get("/api/music/catalog")
def music_catalog():
    return jsonify(tracks=[{**track, "url": f"/{track['file']}", "duration": 24} for track in MUSIC_PRESETS])


@app.get("/styles")
def list_styles():
    with connect_styles() as db:
        return jsonify(styles=ready_styles(db))


@app.get("/styles/<style_id>")
def get_style(style_id):
    with connect_styles() as db:
        row = ready_style(db, style_id)
        if row is None:
            return jsonify(error="Style not found."), 404
        return jsonify(public_style(row))


@app.get("/output/<job_id>/<path:filename>")
def output_file(job_id, filename):
    # Only job IDs and the known shared asset directories are publicly served.
    job_dir = OUTPUT_DIR / job_id if job_id in {"clips", "music", "layouts", "style-previews"} else safe_job_dir(job_id)
    if not job_dir or not job_dir.is_dir() or ".." in Path(filename).parts:
        return jsonify(error="Output not found."), 404
    return send_from_directory(job_dir, filename)


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="The video is larger than the configured upload limit."), 413


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")), debug=True)
