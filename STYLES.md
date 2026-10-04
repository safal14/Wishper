# Whiteboard styles

This repository is a Flask source-preparation client. It does not contain the downstream final-video generator. Its existing `/api/server-package` endpoint now accepts an optional `style_id` for backward compatibility; the new UI requires one. The server validates a ready style, checks that its source still matches the rendered preview, and writes a server-owned code snapshot and the full Revideo source into the handoff package. The browser sends only the ID and never executes style code. The generation prompt names the user-selected style and includes all five labeled style files so a remote LLM does not need access to this filesystem.

The existing media store is local `output/`, so the style catalog is SQLite at `output/styles.sqlite3` and shared preview media is at `output/style-previews/`. `migrations/001_styles.sql` is applied automatically when the catalog is opened. No cloud storage or new backend framework is required.

Install and render:

```sh
npm ci
./.venv/bin/python -m scripts.seed_styles
./.venv/bin/python -m scripts.render_styles
```

The seed command should report 3 styles. The render command should report `ready` for each style on the first run, producing three hash-named MP4s and JPGs in `output/style-previews/`. Subsequent runs should skip ready styles whose code is unchanged. To run the renderer as a background worker while developing, use `./.venv/bin/python -m scripts.render_styles --watch`; use `--retry-failed` after fixing a failed render. The worker stores failure details in the `styles.error_message` column and continues with other styles.

Verify:

```sh
npm run typecheck
./.venv/bin/python -m unittest discover -s tests -v
for video in output/style-previews/*.mp4; do ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -of default=noprint_wrappers=1 "$video"; done
./.venv/bin/python app.py
```

The tests should pass; each preview should be 1920×1080 at 30 fps. In the app, the gallery should show three shared thumbnails, load video only when hovered/focused, and mark a clicked style selected. `GET /styles` and `GET /styles/<id>` expose only ready preview metadata. Unknown or unready IDs sent to `/api/server-package` return 404. A successful handoff includes `style_id`, a hash-verified, server-made copy under the job's `style-snapshots/` directory, and instructions to reuse its tokens, helpers, and example scene. The package also contains `style.code` with the complete text of all five files, and the `prompt` embeds the same code. A downstream generator can consume that source without shared filesystem access; this repository still does not render the final generated scene.

Style authors edit `styles/<id>/style.json`, `tokens.ts`, `helpers.ts`, `scene.tsx`, and `project.ts`. Seeding hashes all five files. A code change marks the row pending and clears the old preview URLs; the worker creates new hash-named media and publishes it only after the render and thumbnail both succeed. The style packages are trusted server code, not user uploads.
