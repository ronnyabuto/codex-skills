#!/usr/bin/env python3
"""Compare fresh enabled/disabled Codex skill outcomes on synthetic fixtures.

Live runs consume model usage. --list inspects cases without invoking Codex.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib

from codex_session import EFFORT_LEVELS, LIMIT_ERROR, run_session
from outcome_cases import CASES, contracts_bytes, grade, tool_calls
from outcome_cases import prepare, user_prompt

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins/ronny-codex-skills/skills"
RETRYABLE = {LIMIT_ERROR, "interrupted"}


def snapshot_hash(root):
    hashed = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            hashed.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    return hashed.hexdigest()


def configured_model():
    config = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
    return tomllib.loads(config.read_text()).get("model") if config.is_file() else None


def session_command(args, query, cwd, skill_file, arm, destination):
    enabled = "true" if arm == "enabled" else "false"
    overrides = [
        "approval_policy=\"never\"", "project_doc_max_bytes=0", "web_search=\"disabled\"",
        "features.plugins=false", "features.hooks=false", "features.apps=false",
        "features.multi_agent=false", "features.memories=false", "features.browser_use=false",
        "skills.bundled.enabled=false",
        f"skills.config=[{{path={json.dumps(str(skill_file))},enabled={enabled}}}]",
    ]
    if args.effort is not None:
        overrides.append(f"model_reasoning_effort={json.dumps(args.effort)}")
    command = ["codex", "--no-daemon", "exec", "--json", "--ephemeral", "--strict-config",
               "--ignore-user-config", "--ignore-rules", "--sandbox", "workspace-write",
               "--skip-git-repo-check", "-C", str(cwd), "--add-dir", str(destination),
               "--model", args.model]
    for value in overrides:
        command += ["-c", value]
    return command + [query + "\nWork only in this synthetic fixture. Do not delegate, access accounts, or publish anything."]


def shell_segments(command):
    def tokens(text):
        lexer = shlex.shlex(text, posix=True, punctuation_chars="();|&<>\n")
        lexer.whitespace_split = True
        lexer.whitespace = " \t\r"
        return list(lexer)

    try:
        words = tokens(command)
        if len(words) >= 3 and Path(words[0]).name in ("bash", "sh", "zsh") and words[1] in ("-c", "-lc", "-cl"):
            words = tokens(words[2])
    except ValueError:
        return
    segment = []
    for word in words:
        if word and all(char in ";|&()\n" for char in word):
            if segment:
                yield segment
                segment = []
        else:
            segment.append(word)
    if segment:
        yield segment


def skill_reads(events, cwd, skill, known_paths):
    """Count reads of real files, including reads before a trailing command fails."""
    readers = {"cat", "head", "tail", "sed", "nl", "bat", "less", "rg"}
    prefixes = {"if", "then", "do", "command"}
    reads = set()
    for call in tool_calls(events, successful_only=False):
        command, output = call["input"]["command"], call["output"]
        for words in shell_segments(command):
            while words and words[0] in prefixes:
                words = words[1:]
            if not words or Path(words[0]).name not in readers:
                continue
            if Path(words[0]).name == "rg" and "--files" in words:
                continue
            for index, word in enumerate(words[1:], 1):
                if words[index - 1].startswith(">") or Path(word).name != "SKILL.md":
                    continue
                path = (cwd / word).resolve()
                if not path.is_file() or (path not in known_paths and path.parent.name != skill):
                    continue
                if call["exit_code"] == 0 and "No such file" not in output and "Permission denied" not in output:
                    reads.add(str(path))
                elif any(line.strip() in output for line in path.read_text().splitlines()
                         if len(line.strip()) >= 10):
                    reads.add(str(path))
    return sorted(reads)


def command_blocks(events):
    patterns = {
        "approval": r"approval (?:required|denied|rejected)|rejected by (?:user|policy)|approval policy",
        "sandbox": r"sandbox (?:blocked|denied|violation)|bwrap:|read-only file system",
        "denied": r"permission denied|operation not permitted|execpolicy.*(?:deny|denied|forbidden)",
    }
    blocked = []
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        if item.get("type") != "command_execution":
            continue
        output = item.get("aggregated_output", "")
        # The shell can fall back after journald stream setup fails. This is
        # host noise, even when an unrelated command later exits nonzero.
        diagnostic = "\n".join(line for line in output.splitlines()
                               if line != "Failed to create stream fd: Operation not permitted")
        kinds = [name for name, pattern in patterns.items() if re.search(pattern, diagnostic, re.I)]
        if kinds:
            blocked.append({"kinds": kinds, "command": item.get("command"),
                            "exit_code": item.get("exit_code"), "output": output})
    return blocked


def run_arm(case_id, round_number, arm, args, destination):
    destination.mkdir(parents=True)
    context = prepare(case_id, destination)
    cwd = context.get("session_cwd", context["cwd"])
    skill = CASES[case_id]["skill"]
    skill_dir = cwd / ".agents/skills" / skill
    shutil.copytree(args.candidates / skill, skill_dir)
    candidate_hash = snapshot_hash(skill_dir)
    if arm == "disabled":
        (skill_dir / "SKILL.md").unlink()
    available_hash = snapshot_hash(skill_dir)
    vault = context.get("vault", destination / "vault")
    vault.mkdir(exist_ok=True)
    env = dict(os.environ, CODEX_MEMORY_VAULT=str(vault),
               CODEX_MEMORY_CACHE=str(destination / "cache"), CODEX_MEMORY_EXCLUDE="",
               PYTHONDONTWRITEBYTECODE="1")
    command = session_command(args, user_prompt(case_id), cwd, skill_dir / "SKILL.md", arm, destination)
    (destination / "request.json").write_text(json.dumps({"query": user_prompt(case_id), "command": command}, indent=2) + "\n")
    # Keep personal standing instructions and plugin state out of both arms.
    # Authentication is linked only in this private, disposable runtime home.
    auth = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json"
    with tempfile.TemporaryDirectory(prefix="codex-eval-home-") as runtime:
        if auth.is_file():
            Path(runtime, "auth.json").symlink_to(auth.resolve())
        env["CODEX_HOME"] = runtime
        record, events = run_session(command, cwd=cwd, timeout=args.timeout, env=env, output=destination)
    known_paths = {(args.candidates / skill / "SKILL.md").resolve()}
    if arm == "enabled":
        known_paths.add((skill_dir / "SKILL.md").resolve())
    reads = skill_reads(events, cwd, skill, known_paths)
    blocks = command_blocks(events)
    record.update(type="case", case=case_id, round=round_number, arm=arm, skill=skill,
                  skill_read=bool(reads), skill_reads=reads, blocked_commands=blocks,
                  candidate_sha256=candidate_hash, available_sha256=available_hash, artifacts=str(destination))
    if CASES[case_id].get("review"):
        record["design_review"] = "pending"
        record["review_criteria"] = CASES[case_id]["review"]
    if snapshot_hash(skill_dir) != available_hash:
        record["error"] = record["error"] or "skill_snapshot_changed"
    if arm == "disabled" and reads:
        record["error"] = record["error"] or "disabled_skill_read"
    if record["error"]:
        record.update(status="error", checks=[])
    else:
        try:
            checks = grade(case_id, context, events)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            checks = [{"name": "gradeable outcome artifacts", "passed": False,
                       "evidence": f"{type(exc).__name__}: {exc}"}]
        record.update(checks=checks, status="pass" if checks and all(c["passed"] for c in checks) else "fail")
    (destination / "grading.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def summarize(records, attempts=None):
    executed = [r for r in (attempts if attempts is not None else records) if r["status"] != "skipped"]
    counts = {arm: {status: sum(r["arm"] == arm and r["status"] == status for r in records)
                    for status in ("pass", "fail", "error", "skipped")} for arm in ("enabled", "disabled")}
    grouped = {}
    for record in records:
        key = (record["case"], record.get("round", 1))
        grouped.setdefault(key, {})[record["arm"]] = record
    pairs = [pair for pair in grouped.values()
             if len(pair) == 2 and all(r["status"] in ("pass", "fail") for r in pair.values())]
    rates = {arm: sum(p[arm]["status"] == "pass" for p in pairs) / len(pairs) if pairs else None
             for arm in counts}
    known = [r["reported_tokens"] for r in executed if r["reported_tokens"] is not None]
    missing = len(executed) - len(known)
    overhead = []
    for pair in pairs:
        enabled, disabled = pair["enabled"], pair["disabled"]
        def difference(field):
            values = [record.get(field) for record in (enabled, disabled)]
            return values[0] - values[1] if all(type(v) in (int, float) for v in values) else None
        overhead.append(dict(case=enabled["case"], round=enabled.get("round", 1), elapsed_seconds_delta=difference("elapsed_seconds"),
                             token_delta=difference("reported_tokens"), turn_delta=difference("num_turns")))
    elapsed = {}
    for arm in counts:
        values = [r.get("elapsed_seconds") for r in executed if r["arm"] == arm]
        elapsed[arm] = round(sum(values), 3) if all(v is not None for v in values) else None
    by_case = {}
    for record in records:
        by_case.setdefault(record["case"], {arm: dict.fromkeys(counts[arm], 0) for arm in counts})
        by_case[record["case"]][record["arm"]][record["status"]] += 1
    block_counts = {arm: {kind: sum(kind in block["kinds"] for record in executed
                                   if record["arm"] == arm
                                   for block in record.get("blocked_commands", []))
                          for kind in ("approval", "sandbox", "denied")} for arm in counts}
    usage_by_case = {}
    for record in executed:
        arms = usage_by_case.setdefault(record["case"], {})
        stats = arms.setdefault(record["arm"], dict(observed_tokens=0, unknown_usage_attempts=0,
                                                     skill_reads=0, blocked_commands=0))
        if record["reported_tokens"] is None:
            stats["unknown_usage_attempts"] += 1
        else:
            stats["observed_tokens"] += record["reported_tokens"]
        stats["skill_reads"] += bool(record.get("skill_read"))
        stats["blocked_commands"] += len(record.get("blocked_commands", []))
    return dict(type="summary", counts=counts, per_case=by_case, per_case_usage=usage_by_case,
                blocked_commands=block_counts, attempts=len(executed), paired_overhead=overhead,
                comparable_pairs=len(pairs), pass_rates=rates,
                pass_rate_delta=rates["enabled"] - rates["disabled"] if pairs else None,
                observed_tokens=sum(known) if known else None, usage_missing_runs=missing,
                total_tokens=sum(known) if not missing else None, estimated_cost_usd=None,
                elapsed_seconds=elapsed)


def input_hashes():
    files = [Path(__file__).with_name(name) for name in (
        "run_outcome_evals.py", "codex_session.py", "outcome_cases.py", "data_workflow_case.py", "skill_value_cases.py")]
    files.append(SKILLS / "vault-memory/scripts/memory.py")
    files.extend(p for p in (ROOT / "evals/fixtures").rglob("*")
                 if p.is_file() and "__pycache__" not in p.parts)
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def planned_arms(cases, runs):
    return [(case, round_number, arm) for round_number in range(1, runs + 1)
            for index, case in enumerate(cases)
            for arm in (("enabled", "disabled") if (index + round_number) % 2
                        else ("disabled", "enabled"))]


@contextmanager
def lock_run(output):
    with (output / "runner.lock").open("a+b") as lock:
        if os.name == "posix":
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            import msvcrt
            lock.write(b"0")
            lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        yield


def checkpoint(report, record):
    report.write(json.dumps(record) + "\n")
    report.flush()
    os.fsync(report.fileno())


def restore(output, args, version):
    metadata = json.loads((output / "run.json").read_text())
    if metadata.get("format_version") != 2:
        raise ValueError("this run predates checkpoint/resume support")
    if metadata["codex_version"] != version:
        raise ValueError("Codex version changed since this run started")
    if metadata["inputs_sha256"] != input_hashes():
        raise ValueError("evaluation code or fixture bytes changed since this run started")
    if metadata["contracts_sha256"] != hashlib.sha256(contracts_bytes()).hexdigest():
        raise ValueError("outcome contracts changed since this run started")
    args.candidates = output / "candidates"
    for skill, expected in metadata["candidate_sha256"].items():
        if snapshot_hash(args.candidates / skill) != expected:
            raise ValueError(f"frozen candidate changed: {skill}")
    args.model, args.effort = metadata["model"], metadata["requested_effort"]
    args.timeout = metadata["timeout_seconds"]
    args.token_budget = args.token_budget or metadata["token_budget"]
    history, valid_bytes = [], 0
    raw = (output / "report.jsonl").read_bytes()
    lines = raw.splitlines(keepends=True)
    for index, line in enumerate(lines):
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("checkpoint must be an object")
        except (ValueError, UnicodeDecodeError):
            if index == len(lines) - 1 and not line.endswith(b"\n"):
                break
            raise ValueError("invalid checkpoint history") from None
        history.append(record)
        valid_bytes += len(line)
    completed = {r["artifacts"] for r in history if r.get("type") == "case" and "artifacts" in r}
    interrupted = [dict(type="case", case=r["case"], arm=r["arm"], round=r.get("round", 1), skill=CASES[r["case"]]["skill"],
                        artifacts=r["artifacts"], status="error", error="interrupted", checks=[],
                        reported_tokens=None, usage=[], num_turns=None, elapsed_seconds=None)
                   for r in history if r.get("type") == "attempt_started" and r["artifacts"] not in completed]
    return metadata, history, interrupted, raw[valid_bytes:]


def attempt_directory(output, case, round_number, arm):
    parent = output / case if round_number == 1 else output / f"round-{round_number}" / case
    destination = parent / arm
    attempt = 0
    while destination.exists():
        attempt += 1
        destination = parent / f"{arm}-retry-{attempt}"
    return destination


def execute(output, args, version):
    if args.resume:
        metadata, history, interrupted, tail = restore(output, args, version)
    else:
        selected = list(dict.fromkeys(args.cases or CASES))
        args.token_budget = args.token_budget or 60000
        args.candidates = output / "candidates"
        for skill in dict.fromkeys(CASES[c]["skill"] for c in selected):
            shutil.copytree(SKILLS / skill, args.candidates / skill,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        definitions = contracts_bytes()
        (output / "outcome-contracts.json").write_bytes(definitions)
        metadata = dict(type="run", format_version=2, codex_version=version, model=args.model,
                        cases=selected, runs=args.runs, requested_effort=args.effort, timeout_seconds=args.timeout,
                        token_budget=args.token_budget, inputs_sha256=input_hashes(),
                        contracts_sha256=hashlib.sha256(definitions).hexdigest(),
                        candidate_sha256={s: snapshot_hash(args.candidates / s)
                                          for s in dict.fromkeys(CASES[c]["skill"] for c in selected)})
        (output / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        history, interrupted, tail = [metadata], [], b""
    latest = {(r["case"], r.get("round", 1), r["arm"]): r for r in history + interrupted if r.get("type") == "case"}
    plan = planned_arms(metadata["cases"], metadata.get("runs", 1))
    pending = [key for key in plan if key not in latest or latest[key]["status"] == "skipped"
               or latest[key].get("error") in RETRYABLE]
    if not pending:
        raise ValueError("nothing to resume: every arm has a terminal result")
    report_path = output / "report.jsonl"
    if tail:
        backup = output / f"report-partial-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.txt"
        backup.write_bytes(tail)
        with report_path.open("r+b") as report:
            report.truncate(report_path.stat().st_size - len(tail))
    with report_path.open("a" if args.resume else "x", encoding="utf-8") as report:
        if args.resume:
            # A valid final JSON object may have survived without its newline.
            if report_path.stat().st_size and not report_path.read_bytes().endswith(b"\n"):
                report.write("\n")
            checkpoint(report, dict(type="resume", resumed_at=datetime.now(timezone.utc).isoformat(),
                                    token_budget=args.token_budget))
        else:
            checkpoint(report, metadata)
        for record in interrupted:
            checkpoint(report, record)
            history.append(record)
        observed, stop = 0, None
        for case, round_number, arm in pending:
            if stop:
                record = dict(type="case", case=case, round=round_number, arm=arm, status="skipped", reason=stop)
            else:
                destination = attempt_directory(output, case, round_number, arm)
                checkpoint(report, dict(type="attempt_started", case=case, round=round_number, arm=arm, artifacts=str(destination)))
                record = run_arm(case, round_number, arm, args, destination)
                tokens = record["reported_tokens"]
                if tokens is not None:
                    observed += tokens
                stop = (LIMIT_ERROR if record["error"] == LIMIT_ERROR else
                        "usage_unknown" if tokens is None else
                        "token_budget" if observed >= args.token_budget else
                        "session_error" if record["error"] else None)
            latest[(case, round_number, arm)] = record
            history.append(record)
            checkpoint(report, record)
            print(f"{record['status'].upper():7} {case:24} round={round_number} {arm:8} {record.get('error') or record.get('reason') or ''}", flush=True)
        records = [latest[key] for key in plan]
        attempts = [r for r in history if r.get("type") == "case" and r["status"] != "skipped"]
        summary = summarize(records, attempts)
        summary.update(token_budget=args.token_budget, admission_stop_reason=stop,
                       reviews_pending=sum(r.get("design_review") == "pending" for r in records),
                       unfinished_arms=sum(r["status"] == "skipped" or r.get("error") in RETRYABLE for r in records))
        checkpoint(report, summary)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"Artifacts: {output}")
    if stop == LIMIT_ERROR:
        print(f"Usage/rate limit reached. After reset: python3 {Path(__file__).resolve()} --resume {output}", file=sys.stderr)
        return 75
    return int(any(r["status"] in ("error", "skipped") or
                   (r["arm"] == "enabled" and r["status"] == "fail") for r in records)
               or not summary["comparable_pairs"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", choices=CASES, dest="cases")
    parser.add_argument("--model", help="Defaults to the selected user model; provider/profile settings are not inherited")
    parser.add_argument("--effort", choices=EFFORT_LEVELS)
    parser.add_argument("--timeout", type=int, default=180, help="Seconds per CLI process")
    parser.add_argument("--token-budget", type=int, help="Per-invocation input + output admission threshold; default 60000")
    parser.add_argument("--runs", type=int, default=1, help="Fresh repetitions per case and arm")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", type=Path, metavar="RUN_DIR")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.timeout < 1 or args.runs < 1 or (args.token_budget is not None and args.token_budget < 1):
        parser.error("runs, timeout and token budget must be positive integers")
    if args.list:
        print(json.dumps(CASES, indent=2))
        return 0
    if args.resume:
        fixed = {"--case", "--model", "--effort", "--timeout", "--output", "--runs"}
        if fixed & {arg.split("=", 1)[0] for arg in sys.argv[1:]}:
            parser.error("--resume preserves model, effort, timeout, cases and runs; only --token-budget may change")
    else:
        args.model = args.model or configured_model()
        if not isinstance(args.model, str) or not args.model:
            parser.error("choose --model or set model in the user config")
    try:
        version = subprocess.run(["codex", "--version"], check=True, capture_output=True, text=True, timeout=15).stdout.strip()
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
        if not match or tuple(map(int, match.groups())) < (0, 170, 0):
            parser.error("paired outcomes require Codex CLI >= 0.170.0")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = (args.resume or args.output or Path.home() / "agent-eval-runs" / f"codex-skill-outcomes-{stamp}").resolve()
        if not args.resume:
            if output.exists():
                parser.error(f"output already exists: {output}")
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.is_relative_to(ROOT) or subprocess.run(
                    ["git", "-C", str(output.parent), "rev-parse", "--show-toplevel"],
                    capture_output=True, timeout=15).returncode == 0:
                parser.error("output must be outside the package and Git worktrees")
            output.mkdir(mode=0o700)
        with lock_run(output):
            return execute(output, args, version)
    except BlockingIOError:
        parser.error("another runner owns this output directory")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
