# Optional desktop recorder

The original recorder in public release 2.0.0 requires a separately installed
FFmpeg with `libx264`. It captures video without audio and keeps annotations as
sidecar JSON/Markdown, rather than burning them into frames. It does not use
ffprobe or the ASS filter. Locate `scripts/evidence.py` inside this installed
skill; use that path as `EVIDENCE` below.

Check the environment first:

```bash
python3 "$EVIDENCE" doctor
```

`ready` checks the encoder; `capture_ready` also checks the selected input.
Device support does not establish display access or OS screen-recording
permission. The script supports X11 (`DISPLAY` or `--input :0`), Windows
`gdigrab`, and macOS `avfoundation` with an explicit screen device. To identify
macOS devices, use `ffmpeg -f avfoundation -list_devices true -i ""`; choose
the intended screen, not a camera. `--source test` is synthetic toolchain
validation and must never be presented as application evidence. Native Wayland
capture is not implemented; use browser capture or an available OS recorder.

## Capture and annotate

Run the recorder in a foreground execution session that the harness can leave
running while other tools drive the UI:

```bash
python3 "$EVIDENCE" record --output "$OUTPUT" --title "Setting persists after reload" \
  --revision "<tested commit and dirty-state description>" --max-seconds 600
```

`OUTPUT` must be a new directory. A JSON `capture_started: true` message is
emitted after FFmpeg reports its first frame. Keep that path as `SESSION`.
The execution process owns its FFmpeg child; do not detach it or kill arbitrary
PIDs. The recorder finishes automatically at `--max-seconds` (at most 3600).
Use `--source`, `--input`, `--size` or `--fps` to select an appropriate supported
capture surface. Review the selected surface and keep private data out of it;
the script does not automatically redact or crop content.

While the recording runs, drive the real app and annotate observed states:

```bash
python3 "$EVIDENCE" annotate "$SESSION" --kind test --message "Save and reload"
python3 "$EVIDENCE" annotate "$SESSION" --kind assertion --result passed \
  --message "The saved setting is still present after reloading"
python3 "$EVIDENCE" stop "$SESSION"
```

Assertions require `passed`, `failed` or `untested`. Messages must contain
1–240 characters. Mark a blocked assertion `untested` and explain its missing
prerequisite. Annotate before requesting stop; later annotations are rejected.
Each annotation is an independent atomic JSON file, so concurrent annotations
do not overwrite each other.

`stop` requests shutdown through a file and returns immediately. Wait for the
recording execution session to finish, then inspect `manifest.json`. Only
`state: complete` and `media_verified: true` establish successful finalization.
The recorder asks its owned child to quit, then terminates/kills that child
if necessary; it never looks up or signals an externally stored PID.

## Review and recovery

Keep `evidence.mp4`, `report.md`, `manifest.json`, and `events/` together.
`capture.mkv`, `capture.progress` and `ffmpeg.log` retain diagnostic evidence.
Media verification decodes the video; it does not establish that application
assertions are true. Review the video at the recorded timestamps before sharing.
Synthetic captures are explicitly labeled in both the manifest and report.

On failure, inspect `ffmpeg.log` and the manifest's error. Existing session
directories are never overwritten. If the execution host crashes, a partial MKV
may remain, but the manifest must not be treated as a completed capture. Check
that no recorder is still running before manually recovering partial media;
start a new session for another attempt. Publication still requires the user's
authorization. If capture is unavailable, use the headless reference and report
the untested recording boundary.
