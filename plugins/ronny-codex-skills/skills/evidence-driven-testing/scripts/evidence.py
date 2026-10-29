#!/usr/bin/env python3
"""Own a foreground FFmpeg capture and retain timed, independently reviewed assertions."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from uuid import uuid4


SOURCES = ("auto", "x11", "avfoundation", "gdigrab", "test")


def write_json(path, value):
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_session(directory):
    directory = Path(directory).resolve()
    data = json.loads((directory / "manifest.json").read_text())
    if data.get("format") != "codex-evidence-v1":
        raise ValueError("not a codex-evidence-v1 session")
    return directory, data


def source_options(source, input_name, size, fps):
    if source == "auto":
        if sys.platform == "win32":
            source = "gdigrab"
        elif sys.platform == "darwin":
            source = "avfoundation"
        elif os.environ.get("DISPLAY"):
            source = "x11"
        else:
            raise ValueError("no desktop source detected; use browser capture or select a supported source")
    if source == "test":
        return source, ["-re", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={fps}"]
    if source == "x11":
        display = input_name or os.environ.get("DISPLAY")
        if not display:
            raise ValueError("x11 requires DISPLAY or --input")
        return source, ["-f", "x11grab", "-framerate", str(fps), "-video_size", size, "-i", display]
    if source == "avfoundation":
        if not input_name:
            raise ValueError("avfoundation requires an explicit screen input, such as --input 1:none")
        return source, ["-f", "avfoundation", "-framerate", str(fps), "-i", input_name]
    return source, ["-f", "gdigrab", "-framerate", str(fps), "-video_size", size,
                    "-i", input_name or "desktop"]


def inspect_runtime(ffmpeg, source, input_name, size, fps):
    binary = shutil.which(ffmpeg)
    report = dict(ready=False, capture_ready=False, ffmpeg=binary, source=source, limitations=[])
    if binary is None:
        report["limitations"].append("FFmpeg not found; install it separately or use existing capture tools")
        return report
    encoders = subprocess.run([binary, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=10)
    report["ready"] = encoders.returncode == 0 and "libx264" in encoders.stdout
    if not report["ready"]:
        report["limitations"].append("FFmpeg with the libx264 encoder is required")
    try:
        selected, options = source_options(source, input_name, size, fps)
        report.update(source=selected, input_options=options, synthetic=selected == "test")
        if selected == "test":
            devices = subprocess.run([binary, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=10)
            available = "testsrc2" in devices.stdout
        else:
            devices = subprocess.run([binary, "-hide_banner", "-devices"], capture_output=True, text=True, timeout=10)
            required = "x11grab" if selected == "x11" else selected
            available = required in devices.stdout
        report["capture_ready"] = report["ready"] and devices.returncode == 0 and available
        if not available:
            report["limitations"].append("selected capture input is not compiled into FFmpeg")
        if selected != "test":
            report["limitations"].append("input support does not establish display access or screen-recording permission")
    except ValueError as exc:
        report["limitations"].append(str(exc))
    return report


def stop_child(child):
    if child.poll() is not None:
        return
    try:
        child.communicate(input=b"q\n", timeout=5)
    except (subprocess.TimeoutExpired, BrokenPipeError):
        child.terminate()
        try:
            child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate()


def finalize(directory, data, ffmpeg):
    raw, video = directory / "capture.mkv", directory / "evidence.mp4"
    if not raw.is_file() or not raw.stat().st_size:
        raise ValueError("capture is empty; inspect ffmpeg.log")
    remux = subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(raw),
                            "-map", "0:v:0", "-c:v", "copy", "-movflags", "+faststart", str(video)],
                           capture_output=True, text=True, timeout=120)
    if remux.returncode:
        raise ValueError("video finalization failed: " + remux.stderr[-2000:])
    probe = subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-i", str(video),
                            "-map", "0:v:0", "-f", "null", "-", "-progress", "pipe:1"],
                           capture_output=True, text=True, timeout=120)
    frames = [int(value) for value in re.findall(r"^frame=(\d+)$", probe.stdout, re.M)]
    if probe.returncode or not frames or max(frames) == 0:
        raise ValueError("video decode verification failed: " + probe.stderr[-2000:])
    events = [json.loads(path.read_text()) for path in (directory / "events").glob("*.json")]
    events.sort(key=lambda event: (event["elapsed_seconds"], event["id"]))
    label = "SYNTHETIC TOOLCHAIN CHECK" if data["synthetic"] else "Desktop capture"
    lines = [f"# {label}", "", data["title"], "", f"Started: {data['started_utc']}",
             f"Source: {data['source']}", f"Revision: {data['revision'] or 'not supplied'}", "",
             "Media decoded successfully. Assertion results are observer reports, not automated proof.",
             "Annotations are sidecar records; they are not burned into the video.", ""]
    for event in events:
        lines.append(f"- {event['elapsed_seconds']:.2f}s {event['kind']} {event.get('result') or ''}: {event['message']}")
    lines += ["", "## Limitations", "", "Review the recording and these assertions before sharing.",
              "This capture excludes audio. The recorder does not crop or redact sensitive content."]
    if data["synthetic"]:
        lines.append("Synthetic frames establish toolchain behavior only; they do not show a live application test.")
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    data.update(state="complete", media_verified=True, decoded_frames=max(frames),
                events=events, finished_utc=datetime.now(timezone.utc).isoformat())
    write_json(directory / "manifest.json", data)
    return data


def record(args):
    report = inspect_runtime(args.ffmpeg, args.source, args.input, args.size, args.fps)
    if not report["capture_ready"]:
        raise ValueError("capture unavailable: " + "; ".join(report["limitations"]))
    directory = args.output.resolve()
    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    (directory / "events").mkdir()
    data = dict(format="codex-evidence-v1", state="recording", title=args.title,
                revision=args.revision, source=report["source"], synthetic=report["synthetic"],
                started_utc=datetime.now(timezone.utc).isoformat(), started_monotonic=time.monotonic(),
                maximum_seconds=args.max_seconds, media_verified=False)
    command = [report["ffmpeg"], "-hide_banner", "-loglevel", "warning", *report["input_options"],
               "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
               "-progress", str(directory / "capture.progress"),
               "-t", str(args.max_seconds), str(directory / "capture.mkv")]
    data["command"] = command
    write_json(directory / "manifest.json", data)
    try:
        with (directory / "ffmpeg.log").open("wb") as log:
            with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log) as child:
                try:
                    announced = False
                    progress = directory / "capture.progress"
                    while child.poll() is None:
                        if not announced and progress.exists():
                            frames = re.findall(r"^frame=(\d+)$", progress.read_text(), re.M)
                            if any(int(value) > 0 for value in frames):
                                print(json.dumps({"session": str(directory), "source": data["source"],
                                                  "synthetic": data["synthetic"], "capture_started": True}), flush=True)
                                announced = True
                        if (directory / "STOP").exists() or time.monotonic() - data["started_monotonic"] >= args.max_seconds:
                            break
                        time.sleep(0.1)
                finally:
                    stop_child(child)
                if child.returncode != 0:
                    raise ValueError(f"FFmpeg capture exited {child.returncode}; inspect ffmpeg.log")
        data["state"] = "finalizing"
        write_json(directory / "manifest.json", data)
        data = finalize(directory, data, report["ffmpeg"])
    except BaseException as exc:
        data.update(state="failed", error=str(exc), media_verified=False)
        write_json(directory / "manifest.json", data)
        raise
    print(json.dumps({"session": str(directory), "state": data["state"],
                      "media_verified": data["media_verified"], "synthetic": data["synthetic"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg", help="Path to a separately installed FFmpeg binary")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "record"):
        command = commands.add_parser(name)
        command.add_argument("--source", choices=SOURCES, default="auto")
        command.add_argument("--input", help="Display identifier or explicit screen device")
        command.add_argument("--size", default="1280x720")
        command.add_argument("--fps", type=int, default=15)
        if name == "record":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--title", required=True)
            command.add_argument("--revision", default="")
            command.add_argument("--max-seconds", type=float, default=600)
    annotate = commands.add_parser("annotate")
    annotate.add_argument("session", type=Path)
    annotate.add_argument("--kind", choices=("setup", "test", "assertion"), required=True)
    annotate.add_argument("--message", required=True)
    annotate.add_argument("--result", choices=("passed", "failed", "untested"))
    stop = commands.add_parser("stop")
    stop.add_argument("session", type=Path)
    args = parser.parse_args()
    if args.command in ("doctor", "record"):
        if not re.fullmatch(r"[1-9]\d*x[1-9]\d*", args.size) or not 1 <= args.fps <= 60:
            parser.error("size must be positive WIDTHxHEIGHT and fps must be 1..60")
        if args.command == "record" and not 0 < args.max_seconds <= 3600:
            parser.error("max-seconds must be in (0, 3600]")
    if args.command == "doctor":
        report = inspect_runtime(args.ffmpeg, args.source, args.input, args.size, args.fps)
        print(json.dumps(report, indent=2))
        return int(not report["ready"])
    if args.command == "record":
        record(args)
        return 0
    directory, data = load_session(args.session)
    if args.command == "stop":
        if data["state"] == "recording":
            (directory / "STOP").touch(exist_ok=True)
        print(json.dumps({"state": data["state"], "stop_requested": data["state"] == "recording"}))
        return 0
    if data["state"] != "recording" or (directory / "STOP").exists():
        raise ValueError("annotations require an active recording before a stop request")
    if not args.message.strip() or len(args.message) > 240:
        parser.error("annotation message must contain 1..240 characters")
    if args.kind == "assertion" and not args.result:
        parser.error("assertions require --result")
    event = dict(id=uuid4().hex, kind=args.kind, message=args.message, result=args.result,
                 elapsed_seconds=max(0, time.monotonic() - data["started_monotonic"]))
    write_json(directory / "events" / (event["id"] + ".json"), event)
    print(json.dumps(event))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"evidence: {exc}", file=sys.stderr)
        raise SystemExit(1)
