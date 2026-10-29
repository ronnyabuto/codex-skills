#!/usr/bin/env python3
"""Run isolated Codex cases and retain evidence for human review."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path
import subprocess

from codex_session import analyze

CASES = [
    ("caching", True, "Our dashboard is slow. Assess whether Redis addresses the bottleneck before changing anything.",
     {"requirements.json": json.dumps({"target_ms": 200, "freshness": "immediate", "observed_ms": 1200, "database_ms": 1100, "plan": "SCAN orders", "rows": 1000000, "query": "SELECT * FROM orders WHERE customer_id = ?", "indexes": []})}),
    ("duplicate-payments", True, "Customers sometimes get charged twice despite disabling the submit button. Investigate the root cause before proposing a fix.",
     {"payments.py": "charges = []\ndef pay(order_id):\n    charges.append(order_id)\n    return {'status': 'paid', 'order': order_id}\nif __name__ == '__main__':\n    pay('order-17')\n    pay('order-17')\n    print({'charges': len(charges), 'orders': charges})\n",
      "README.md": "A client retries POST /pay with the same order after an acknowledgement timeout. The endpoint calls pay(order_id). Requirement: at most one charge per order. Run python3 payments.py for the observed retry scenario. The UI disables the button after the first click.\n"}),
    ("queue-capacity", True, "Background jobs fall behind during bursts. Should another synchronous endpoint move onto the queue? Assess capacity and failure behavior first.",
     {"workload.json": json.dumps({"observed_arrivals_per_second": 120, "workers": 4, "observed_jobs_per_second_per_worker": 15, "burst_seconds": 60, "normal_arrivals_per_second": 30, "queue_age_slo_seconds": 10, "proposed_extra_jobs_per_second": 20})}),
    ("routine-crud", False, "Assess adding a conventional CRUD endpoint for a display-name field following the existing adequate handler pattern.",
     {"handlers.py": "def update_name(database, user_id, name):\n    if not isinstance(name, str) or not name.strip():\n        raise ValueError('name required')\n    database[user_id]['name'] = name\n",
      "README.md": "Existing endpoints use handlers.py validation and per-user database ownership checks in the router. Only a display-name field is requested.\n"}),
    ("known-local-bug", False, "The date picker adds an erroneous +1 to the calendar day count. Explain the targeted correction and checks for leap and non-leap February.",
     {"dates.py": "import calendar\ndef days_in_month(year, month):\n    return calendar.monthrange(year, month)[1] + 1\n"}),
]


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--case", choices=[case[0] for case in CASES])
    parser.add_argument("--timeout", type=int, default=240, help="Seconds per case")
    parser.add_argument("--token-budget", type=int, help="Stop launching cases after this many reported input + output tokens; may overshoot by one case")
    args = parser.parse_args()
    if args.timeout < 1 or (args.token_budget is not None and args.token_budget < 1):
        parser.error("timeout and token budget must be positive integers")
    args.output.mkdir(parents=True, exist_ok=False)
    reports = []
    observed_tokens = 0
    usage_missing = 0
    admission_stop_reason = None
    for name, expected, query, files in CASES:
        if args.case and args.case != name:
            continue
        if admission_stop_reason:
            reports.append({"case": name, "skipped": True, "reason": admission_stop_reason, "behavior_review": "not-run"})
            continue
        fixture = args.output / name
        fixture.mkdir()
        for filename, content in files.items():
            (fixture / filename).write_text(content)
        subprocess.run(["git", "init", "-q", "-b", "main", str(fixture)], check=True)
        before = hashes(fixture)
        command = ["codex", "--no-daemon", "exec", "--json", "--ephemeral", "--sandbox", "read-only", "-C", str(fixture)]
        command += [query + "\nRead-only assessment: inspect the supplied fixture, run harmless probes if useful, and do not modify files or delegate."]
        env = dict(os.environ, CODEX_MEMORY_VAULT=str(args.output.resolve() / (name + "-memory")),
                   CODEX_MEMORY_CACHE=str(args.output.resolve() / (name + "-cache")), CODEX_MEMORY_EXCLUDE="")
        timed_out = False
        started = time.monotonic()
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=args.timeout, env=env)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            result = subprocess.CompletedProcess(command, 124, stdout, stderr + f"\nEval timed out after {args.timeout} seconds.\n")
        except OSError as exc:
            result = subprocess.CompletedProcess(command, 127, "", str(exc))
        (args.output / (fixture.name + ".jsonl")).write_text(result.stdout)
        (args.output / (fixture.name + ".stderr")).write_text(result.stderr)
        session, events = analyze(result.stdout, result.returncode, timed_out)
        (args.output / (fixture.name + ".answer.md")).write_text("\n\n".join(session["answers"]))
        error = bool(session["error"])
        commands = [event["item"].get("command", "") for event in events if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "command_execution"]
        invoked = any("system-reasoning/SKILL.md" in command for command in commands)
        unchanged = before == hashes(fixture)
        usage = session["usage"]
        tokens = session["reported_tokens"]
        if tokens is None:
            usage_missing += 1
        else:
            observed_tokens += tokens
        report = {
            "case": name, "error": error or not unchanged,
            "expected_trigger": expected, "skill_read": invoked,
            "fixture_unchanged": unchanged, "behavior_review": "pending",
            "usage": usage, "reported_tokens": tokens,
            "returncode": result.returncode, "timed_out": timed_out,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "thread_ids": [event["thread_id"] for event in events
                           if event.get("type") == "thread.started" and "thread_id" in event],
        }
        if args.token_budget is not None:
            if tokens is None:
                admission_stop_reason = "usage_unknown"
            elif observed_tokens >= args.token_budget:
                admission_stop_reason = "token_budget"
        reports.append(report)
        print(json.dumps(report), flush=True)
    (args.output / "summary.json").write_text(json.dumps(reports, indent=2) + "\n")
    executed = [report for report in reports if not report.get("skipped")]
    completed_count = sum(not report["error"] for report in executed)
    summary = {
        "executed": len(executed), "completed": completed_count,
        "errors": len(executed) - completed_count,
        "skipped": len(reports) - len(executed),
        "observed_tokens": observed_tokens if len(executed) > usage_missing else None,
        "usage_missing_cases": usage_missing,
        "tokens_per_completed_eval": (observed_tokens / completed_count
                                      if completed_count and not usage_missing else None),
        "estimated_cost_usd": None, "token_budget": args.token_budget,
        "admission_stop_reason": admission_stop_reason, "timeout_seconds": args.timeout,
        "behavior_review": "pending",
    }
    (args.output / "run-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return int(bool(summary["errors"] or summary["skipped"]))


if __name__ == "__main__":
    raise SystemExit(main())
