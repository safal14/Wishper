# Client/server boundary

The user's device runs only the frontend. The generator device is the system of record and performs all media work.

## Client responsibilities

- Select local video files and send them to the server.
- Show browser-only previews while files are being selected.
- Send editing choices: order, trim ranges, crop, layout, effects, canvas, style, music, and prompt.
- Render the sequential progress timeline returned by the server.
- Allow transcript corrections through server APIs.
- Poll or subscribe to progress updates.
- Play or download the final MP4 returned by the server.

The client must not run ffmpeg, Whisper, Revideo rendering, music processing, package creation, or final-video composition. It must not treat local files or local `output/` folders as the source of truth.

## Generator-server responsibilities

- Store uploaded source videos and job metadata.
- Validate and process every edit operation.
- Merge/trim/process clips with ffmpeg.
- Transcribe with Whisper and persist transcript/captions.
- Build the complete generation package, including verified style code and media references.
- Run the agent and final video composition.
- Persist progress, current step, percent, started time, finished time, and errors.
- Return the completed MP4 and captions.

## Current migration: server-side transcription only

For the current phase, editing remains on this client. The server only needs to receive the client's final `merged.mp4`, run Whisper, and return timestamped transcript data. Add these endpoints to the generator server:

| Endpoint | Request | Response |
| --- | --- | --- |
| `POST /api/transcribe` | `multipart/form-data`: `user_id`, `video` (`UploadFile`) | `202 {"job_id":"tjob_...","status":"QUEUED"}` |
| `GET /api/transcribe/{job_id}` | none | `{"job_id":"...","status":"RUNNING","percent":42}` while running; on completion include `{"status":"COMPLETED","language":"en","segments":[{"start":0.0,"end":1.2,"text":"..."}]}` |

The server must persist transcription jobs, run Whisper in a background worker, and return a consistent error response. The client sends the already edited/merged video to `/api/transcribe`; it then uses the returned segments to create the existing server package and sends that package/video to `/api/jobs` for generation.

The current client proxy routes are `/api/remote/transcribe` and `/api/remote/transcribe/{local_job_id}`. They call the remote server above, so the browser does not need to know the generator address or credentials.

## Future full frontend-only API contract

The existing `POST /api/jobs` endpoint is not enough for the frontend-only workflow. The server should expose:

| Endpoint | Purpose |
| --- | --- |
| `POST /handshake` | Validate client/user and protocol version. |
| `POST /api/client/jobs` | Create a job with JSON editing settings and uploaded source files. Return `{job_id}`. |
| `GET /api/client/jobs/{job_id}` | Return job state, current step, percent, timestamps, duration estimate, and error. |
| `GET /api/client/jobs/{job_id}/events` | Optional SSE stream for instant progress updates. |
| `GET /api/client/jobs/{job_id}/transcript` | Return server-generated transcript. |
| `PUT /api/client/jobs/{job_id}/transcript` | Save corrected transcript. |
| `POST /api/client/jobs/{job_id}/start` | Start or resume processing after the user confirms edits. |
| `GET /api/client/jobs/{job_id}/video` | Stream the final MP4. |
| `GET /api/client/jobs/{job_id}/captions` | Download WebVTT/SRT captions. |
| `POST /api/client/jobs/{job_id}/cancel` | Cancel safely. |

## Sequential progress model

The server should report these ordered steps:

1. `uploading`
2. `validating`
3. `editing`
4. `transcribing`
5. `waiting_for_review`
6. `building_prompt`
7. `generating_scenes`
8. `rendering_video`
9. `finalizing`
10. `completed`

Each status response should contain:

```json
{
  "job_id": "...",
  "state": "running",
  "step": "transcribing",
  "step_index": 4,
  "step_count": 10,
  "percent": 42,
  "message": "Transcribing audio",
  "started_at": "2026-10-04T00:00:00Z",
  "step_started_at": "2026-10-04T00:02:10Z",
  "finished_at": null,
  "elapsed_seconds": 130,
  "estimated_remaining_seconds": 185,
  "error": null
}
```

The browser can calculate elapsed display time, but the server owns timestamps and estimated remaining time because it knows the actual work and queue.

## Current migration status

This workspace still contains the legacy local Flask implementation (`/api/clips`, `/api/merge`, Whisper, ffmpeg, and local output storage). It cannot honestly be called frontend-only until the remote server implements the contract above and the browser calls those remote endpoints directly or through a thin authenticated proxy.
