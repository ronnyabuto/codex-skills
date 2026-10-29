"""Bounded Codex execution and native JSONL outcome/usage parsing."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def analyze(output, returncode, timed_out=False):
    events, malformed = [], False
    for line in output.splitlines():
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("event must be an object")
            events.append(event)
        except ValueError:
            malformed = True
    items = [event["item"] for event in events if event.get("type") == "item.completed"]
    answers = [item.get("text", "") for item in items if item.get("type") == "agent_message"]
    completed = [event for event in events if event.get("type") == "turn.completed"]
    errors = [event for event in events if event.get("type") in ("error", "turn.failed")]
    error = ("timeout" if timed_out else "process_exit" if returncode else
             "malformed_events" if malformed else "api_error" if errors else
             "missing_answer" if not any(text.strip() for text in answers) else
             "incomplete_turn" if not completed else None)
    usage = [event.get("usage") for event in completed]
    known = bool(usage) and all(
        isinstance(item, dict) and all(type(item.get(key)) is int and item[key] >= 0
                                      for key in ("input_tokens", "output_tokens")) for item in usage)
    tokens = sum(item["input_tokens"] + item["output_tokens"] for item in usage) if known else None
    return dict(error=error, error_details=errors, answers=answers, usage=usage,
                reported_tokens=tokens, estimated_cost_usd=None, returncode=returncode,
                timed_out=timed_out,
                thread_ids=[e["thread_id"] for e in events
                            if e.get("type") == "thread.started" and "thread_id" in e]), events


def run_session(command, *, cwd, timeout, env, output):
    started = time.monotonic()
    stdout, stderr, timed_out, returncode = "", "", False, 127
    try:
        with subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True,
                              start_new_session=os.name == "posix") as proc:
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                stdout, stderr = proc.communicate()
            returncode = proc.returncode
    except OSError as exc:
        stderr = str(exc)
    Path(output, "session.jsonl").write_text(stdout)
    Path(output, "stderr.txt").write_text(stderr)
    record, events = analyze(stdout, returncode, timed_out)
    Path(output, "answer.md").write_text("\n\n".join(record.pop("answers")))
    record["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return record, events
