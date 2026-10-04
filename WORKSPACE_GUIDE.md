# Wishper Studio: complete workspace guide

This guide explains what this workspace does, how to use it, which code implements each feature, and what is still missing. It describes the project as it exists now, not a future design.

## The most important distinction

The videos uploaded here are **the user's footage**. They are not the AI-generated background video. This app prepares that footage and records where it should appear in a future video: full frame, in a small overlay, or beside generated content. The generated scenes and final composition are meant to be made by a separate server.

Today, this workspace runs locally. It can create a complete **handoff package** for that server, but it does **not** contact the other device, call an LLM, generate new scenes, or combine the final AI video by itself. Until the cross-device connection is built, a finished MP4 can be imported manually and viewed here.

Some names used below:

| Term | Simple meaning |
| --- | --- |
| Source clip | One video the user uploads. |
| Prepared source | The uploaded clips, trimmed/processed and joined into one video. |
| Generated visuals | New scenes that the other server is expected to create. |
| Layout | Instructions for placing the user's footage in those scenes. |
| Transcript | Timestamped words detected from the prepared source's audio. |
| Style | Revideo code that defines a whiteboard look, plus a reusable preview video. |
| Handoff package | A JSON file with the prompt, transcript, style code, music choice, source files, and layout instructions for the other server. |
| Finished video | The MP4 made by the other server and imported back into this workspace. |

## How the workspace reached this point

The project started as a local video/transcription tool. It now also has a source editor, layout planner, style gallery, background-music choices, and a structured handoff. The latest change joined preparation and transcription into one action and added restoration after refresh plus local finished-video import. The older direct-transcription API still exists for compatibility; the main user flow uses the combined preparation action.

The intended flow is:

```text
Upload user's clips → edit and arrange them → choose canvas/layout
       → prepare one source video + automatic transcript
       → correct transcript → choose whiteboard style, prompt, and music
       → create local handoff package
       → [future: send package/media to other device for generation]
       → import finished MP4 here → watch or download
```

### What a user does in the app

1. **Add videos.** Upload one or more clips. The app stores each original and reads its dimensions, duration, orientation, and audio information.
2. **Choose the output shape.** On the first upload, the app shows whether the files are horizontal or vertical and asks for a **16:9 horizontal** or **9:16 vertical** generated canvas. The choice is the user's; the app does not silently force it from the source video.
3. **Edit source clips.** Reorder or remove them, trim start/end times, adjust lighting and color, reduce video grain, clean audio, and preview or process the selected clip. These changes affect the user's footage, not the generated whiteboard scenes.
4. **Plan source placement.** For each clip, choose full frame, an overlay, split screen, or **Smart screen** (different layouts at different times). Set crop, mirror, overlay position/size/shape/border, or split direction/share. The canvas is a placement **mockup**; generated visuals are only a labeled placeholder at this stage.
5. **Prepare video & transcript.** One button processes the chosen clips, trims and joins them in sequence, then runs speech transcription automatically. There is no separate transcript-generation button. The prepared source keeps its own shape; overlay and split-screen choices are saved as instructions rather than burned into this video.
6. **Check the transcript.** Edit any detected line. Corrections save to local JSON/text/VTT caption files. If no speech is detected, the empty transcript is still valid and the user can continue with a visual prompt. If transcription fails, the same Prepare button retries it without merging again.
7. **Choose the generated look.** Select one of three pre-rendered whiteboard styles. The card shows a shared thumbnail and plays its preview on hover or keyboard focus.
8. **Write the brief and pick music.** Add the prompt for the future generated scenes. Choose a bundled instrumental track, no track, or an uploaded audio file; set volume and start time. The music choice is written into the handoff; this app does not mix it into a final video.
9. **Review and create the handoff.** The app shows the source, layout, transcript, style, prompt, and music before writing `server-package.json` locally. This is **not** a remote send yet.
10. **View a returned video.** When a finished MP4 is available, import it on the Finished video panel. The newest import is shown in the player and can be downloaded. Earlier imports remain on disk.

Refreshing the page restores the active prepared source, transcript, and last packaged style/prompt/music when their source files still match. Changing source clips or their processing means the source must be prepared again. Layout-only edits do not require another merge or transcription, but they do require a new handoff package.

## What technology is used, and why

| Tool | Job in this workspace |
| --- | --- |
| Python + Flask | Runs the local web app and JSON/file APIs. |
| HTML, CSS, and plain JavaScript | Build the editor, playback, layout mockup, style gallery, and review flow in one template. There is no separate frontend framework. |
| `ffprobe` | Reads video size, duration, rotation, and audio-stream information. |
| `ffmpeg` | Applies video/audio filters, trims and normalizes clips, merges them, extracts audio/frames, and makes style thumbnails. |
| `faster-whisper` | Converts the merged video's speech into timestamped transcript segments. |
| Revideo + TypeScript | Defines and renders the three code-based whiteboard style previews. It is **not** used here to render the final generated video. |
| SQLite | Stores the shared style catalog and preview status. Clip and job data are regular files under `output/`. |
| Python music-generation script | Creates the three bundled 24-second instrumental MP3 loops using generated waveforms, then encodes them with ffmpeg. |

## Feature-to-code map

The first column is what the user sees. The second points to the main code. The third explains the technique in plain language. `templates/index.html` contains both the visible page and its JavaScript.

### Clips and editing

| Feature | Main code | Technique |
| --- | --- | --- |
| Upload and list clips | `app.py`: `upload_clips`, `list_clips`, `probe_video`; `templates/index.html`: upload/list handlers | Files are saved under a unique clip ID; `ffprobe` reads metadata. Original files are kept. |
| Remove or reorder clips | `app.py`: `delete_clip`, `save_project_order`; `templates/index.html`: media cards and draggable timeline | The selected order is saved in `output/project.json`; deleting a clip removes its local clip directory. |
| Choose 16:9 or 9:16 | `app.py`: `set_project`, `canvas_for`; `templates/index.html`: `detectFiles`, `askFormat`, `setOrientation` | The browser reads selected files' dimensions for the prompt; the chosen canvas is saved and existing crop regions are fitted to it. |
| Trim a clip | `app.py`: `save_clip_trim`, `clip_trim`; `templates/index.html`: trim controls | Start/end seconds are saved in clip metadata; ffmpeg uses them when preparing the source. |
| Visible color, lighting, grain looks | `app.py`: `normalize_settings`, `process_clip`; `templates/index.html`: source-adjustment toggles and look presets | The page offers lighting, video-noise reduction, and preset color looks. The backend applies them with ffmpeg filters such as `eq` and `hqdn3d`. |
| Additional processing settings | `app.py`: `normalize_settings`, `process_clip` | Backend code also supports sharpness, blur, speed, rotation, and fade filters. The current page does **not** offer separate controls for all of these settings. |
| Audio cleaning | `app.py`: `process_clip`; `templates/index.html`: audio controls | ffmpeg filters can remove rumble/hum/noise, emphasize voice, normalize loudness, and limit peaks. Options include FFT, wavelet, or non-local-means denoising. |
| Original/enhanced preview | `templates/index.html`: `preview`, `renderAudio` | A quick browser filter shows the visual look; actual cleaned media is rendered by the backend when processed. |

### Layout and preparation

| Feature | Main code | Technique |
| --- | --- | --- |
| Full, overlay, split, smart layout | `app.py`: `normalize_layout`, `normalize_segments`, `save_layout`; `templates/index.html`: layout module (`makeLayout`, `renderPanel`, `renderSegments`) | Layout is stored as structured data. Smart segments give different layouts to different time ranges. |
| Crop, mirror, overlay geometry | `app.py`: `role_aspect`, `conform_region`, `region_px`; `templates/index.html`: crop handles and `paint` | Dragged boxes use normalized 0–1 coordinates so they can be translated back to source pixels and fitted to the selected canvas shape. |
| Placement mockup | `templates/index.html`: `paint`, `applyCanvasSize` | HTML Canvas draws the user's source where it would appear and labels the still-uncreated generated area. It is not the final render. |
| Layout export | `app.py`: `build_layout_manifest`, `export_layout`; `templates/index.html`: Save layout JSON | Creates a machine-readable layout with crop pixels, clip order, and absolute timeline positions. |
| Merge source sequence | `app.py`: `render_source_clip`, `merge_clips`; `templates/index.html`: Prepare button | ffmpeg trims and converts clips to compatible size, 30 fps, H.264/AAC; silent audio is added when needed. A concat list joins them into `merged.mp4`. |
| Avoid stale preparations | `app.py`: `source_fingerprint`, `get_workflow`, `create_server_package` | A SHA-256 fingerprint of clip IDs, trim/settings, and source file size/modified time is checked before restoring or packaging. It is a change detector, **not** a hash of every video byte. Changed footage requires another preparation. |

### Transcript, styles, music, and handoff

| Feature | Main code | Technique |
| --- | --- | --- |
| Automatic transcript after merge | `app.py`: `merge_clips`, `transcribe`; `templates/index.html`: Prepare button and `showPrepared` | ffmpeg extracts 16 kHz mono WAV; `faster-whisper` detects speech and timestamps, then writes JSON, plain text, and WebVTT captions. A few frames are also extracted for a later generation step. |
| Edit and restore transcript | `app.py`: `update_transcript`, `get_workflow`; `templates/index.html`: transcript textareas, debounced save, `load` | Changed lines are validated against video duration and saved automatically; a refresh reads the active job from disk. |
| Style catalog | `style_catalog.py`, `migrations/001_styles.sql`, `scripts/seed_styles.py` | SQLite stores style names, code folder/hash, preview URLs, version, and pending/rendering/ready/failed status. |
| Style previews | `scripts/render_styles.py`, `scripts/render_style.mjs`, `styles/*/project.ts`; `app.py`: `list_styles`, `get_style` | Revideo renders a shared MP4 at 1920×1080; ffmpeg extracts a JPG. A SHA-256 code hash prevents needless re-renders and invalidates a preview when its code changes. |
| Style gallery | `templates/index.html`: `loadStyles`, `syncStyleSelection` | The browser requests only ready style metadata, displays thumbnails, and loads a muted looping preview only on hover/focus. It sends only the selected `style_id`. |
| Bundled and uploaded music | `scripts/generate_music.py`, `static/music/`, `app.py`: `music_catalog`, `upload_music`; `templates/index.html`: music controls | Three local loops are offered, or an uploaded audio file is stored in `output/music/`. The selected file, volume, start, and loop instruction go into the package. |
| Server/LLM instructions | `app.py`: `build_layout_manifest`, `build_layout_instructions`, `create_server_package` | A time-coded composition plan explains full-frame, overlay, and split-screen placement. The server adds the selected style's verified code to the prompt and package. |
| Safe style snapshot | `style_catalog.py`: `style_reference`; `app.py`: `create_server_package` | The style's five files are checked against their hash and copied into the job's `style-snapshots/` folder so later style edits cannot change this handoff. |
| Finished-video import and playback | `app.py`: `import_generated_result`, `get_workflow`, `output_file`; `templates/index.html`: `showResult` and upload handler | An imported MP4 is checked with `ffprobe`, saved under a new unique name, and served back to the browser. `result.json` points to the newest one; earlier files are retained. |

Other available APIs include `POST /api/process` for direct transcription of one uploaded video and `POST /api/clips/process-all` for applying non-default clip settings. The main editor uses the combined merge/transcript flow instead.

### Browser-to-backend request map

These are the main local HTTP endpoints. They are called by the browser on this device; they are **not** the future cross-device protocol.

| Action | Endpoint | Main result |
| --- | --- | --- |
| Load or change project format and order | `GET/POST /api/project`, `POST /api/project/order` | Saved canvas choice and clip sequence. |
| Upload, list, edit, or delete clips | `POST /api/clips/upload`, `GET /api/clips`, `/api/clips/<clip-id>/...` | Original clips plus trim, settings, processed files, and layouts. |
| Export layout separately | `POST /api/layout/export` | `output/layouts/layout.json`. |
| Prepare and transcribe | `POST /api/merge` | `merged.mp4`, transcript, and caption URL; `transcription_error` if only speech detection fails. |
| Retry or correct transcript | `POST /api/jobs/<job-id>/transcribe`, `PUT /api/jobs/<job-id>/transcript` | Transcript JSON, text, and VTT captions. |
| Restore the current workflow | `GET /api/workflow` | Prepared job, transcript, safe handoff summary, and latest result URL. |
| Browse styles or music | `GET /styles`, `GET /styles/<style-id>`, `GET /api/music/catalog` | Ready style preview metadata and built-in tracks. |
| Upload music and create package | `POST /api/music/upload`, `POST /api/server-package` | Stored audio or a local `server-package.json`. |
| Import and view a finished video | `POST /api/jobs/<job-id>/result`, `GET /output/<job-id>/<file>` | A validated MP4 and its local playback URL. |

For the precise request/response fields, read the route functions in `app.py` and the browser calls in `templates/index.html`. The handoff JSON is the current contract for the later generator; no remote transport contract has been agreed yet.

## How the whiteboard styles work

There are three styles: **Marker Whiteboard** (bold marker strokes and a drawing cursor), **Clean Whiteboard** (thin navy lines and calm motion), and **Doodle Whiteboard** (cream paper, pastel notes, and playful motion). Each lives in `styles/<style-id>/`:

| File | Purpose |
| --- | --- |
| `style.json` | ID, name, description, Revideo framework, preview duration, and version. |
| `tokens.ts` | Shared visual rules: board and ink colors, accent colors, fonts, stroke width, wobble, speed, easing, and draw order. |
| `helpers.ts` | Reusable drawing tools such as wobbly lines/boxes/arrows, stroke animation, write-on lettering, and optional marker cursor. |
| `scene.tsx` | The example whiteboard scene shown in the preview. |
| `project.ts` | Revideo entry point that renders that scene. |

The preview is rendered **once per code version**, stored under `output/style-previews/`, and shared by all users of this local installation. Re-rendering is needed only when the five style files change. The gallery API (`GET /styles`) returns names and preview media URLs, not code. When a user creates a package, the Flask backend looks up `style_id`, verifies the hash, and inserts the code into the **server-bound** package and agent prompt. The browser never executes Revideo style code. A preview shows the intended look; it is not the user's finished video.

## What the handoff contains

`output/<job-id>/server-package.json` is the main item for the future server. It contains:

- `source_video`: the prepared `merged.mp4` path, duration, and clip order;
- `transcript` and `captions`: corrected text and caption-file path;
- `project` and `overlay`: output ratio plus exact per-clip crop, placement, and timed layout;
- `music`: selected asset, volume, start time, and loop instruction if applicable;
- `user_prompt`: the user's original creative brief;
- `layout_instructions`: the readable, time-coded placement plan;
- `style_id` and `style`: the chosen style plus server-owned Revideo code snapshot;
- `prompt`: the combined brief, style definition, and composition instructions for a future LLM/scene generator.

The package uses **paths for large videos and audio**, not embedded media bytes. When the other-device connection is built, those files must also be transferred or made accessible to that server. Creating this package today does not deliver files across devices.

## Where files live

```text
app.py                         Flask app and local APIs
templates/index.html           Page, styling, editor, gallery, browser logic
style_catalog.py               SQLite style catalog and code hashes
styles/<style-id>/             Trusted Revideo style source code
scripts/                       Style seeding/rendering and music generation
static/music/                  Three bundled music MP3s
tests/                         Automated API/workflow/style tests
output/
  project.json                 One local project's format, order, active job
  clips/<clip-id>/             Original/processed clip and metadata.json
  music/                       User-uploaded audio
  styles.sqlite3               Local style catalog
  style-previews/              Shared preview MP4/JPG files
  <job-id>/
    source-*.mp4, concat.txt   Normalized clip parts and merge instructions
    merged.mp4                 Prepared source sequence, not final AI video
    source-order.json          Exact order used in the prepared source
    transcript.json/.txt       Detected and corrected words
    captions.vtt               Downloadable timed captions
    audio.wav, frames/          Transcription/later-generator preparation
    preparation.json           Active source details and fingerprint
    server-package.json        Handoff for the future server
    style-snapshots/            Pinned copy of selected style code
    generated-<unique-id>.mp4  Imported finished video version(s)
    result.json                Pointer to the newest imported video
```

The app keeps old job folders and imported versions. It currently has **one local project**, not separate accounts or cloud projects. Do not treat `output/` as disposable if you want to keep uploaded footage and jobs.

## Setup and everyday commands

Run these from the workspace root. You need Python, Node/npm, `ffmpeg`, and `ffprobe` installed. Use the existing `.venv` if it is already set up; otherwise create one.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm ci
python -m scripts.seed_styles
python -m scripts.render_styles
python app.py
```

Open `http://127.0.0.1:5000`. The first style render may take time; later runs skip styles whose code has not changed. The music MP3s are already stored in `static/music/`; run `python scripts/generate_music.py` only if they need regenerating.

Useful checks:

```bash
ffmpeg -version
ffprobe -version
npm run typecheck
python -m unittest discover -s tests -v
```

Style maintenance:

```bash
python -m scripts.seed_styles
python -m scripts.render_styles --retry-failed
# Optional worker that checks for changed styles every 10 seconds:
python -m scripts.render_styles --watch
```

The default Whisper model is `medium` on CPU with `int8` computation. You can set `WHISPER_MODEL`, `WHISPER_DEVICE`, and `WHISPER_COMPUTE_TYPE` before starting Flask. `MAX_UPLOAD_MB` defaults to 2048. The app binds to `127.0.0.1:5000` by default; `HOST` and `PORT` can change that, but this development app is not an authenticated public service.

## If something goes wrong

| Symptom | What to check |
| --- | --- |
| No style cards | Run the seed/render commands; only `ready` styles appear. Check `output/styles.sqlite3` or the renderer's error output. |
| Prepare fails | Confirm ffmpeg/ffprobe are installed and the source video is readable. The error is shown in the page. |
| Transcription is slow or fails | The default model runs on CPU. Keep the prepared video; use the same Prepare button to retry transcription. Check the local model installation and settings. |
| Transcript is empty | If the video has no speech, continue using the visual prompt. Empty speech is not the same as a failed transcript. |
| Package says source changed | A clip, trim, order, or processing setting changed. Prepare again. If only layout changed, create a new package without merging again. |
| A package exists but no generated video appears | That is expected until the other server is connected or a finished MP4 is imported manually. |
| An old finished video appears after edits | It is kept for reference. Create a new handoff and import the new MP4 to update the preview. |

## What remains for the other-device integration

The other server's address, authentication, upload/transfer method, job-status messages, LLM prompt processing, actual generated scenes, final Revideo composition, and automatic return of the completed MP4 are **not implemented in this workspace**. The future handshake should transfer the package **and referenced media**, identify jobs reliably, and protect the return endpoint with authentication. The local import path is only a bridge for now.

For the deeper style rendering and catalog details, see [STYLES.md](STYLES.md). For a shorter quick start, see [README.md](README.md).
