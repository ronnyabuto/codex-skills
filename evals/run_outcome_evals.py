#!/usr/bin/env python3
"""Compare fresh enabled/disabled Codex skill outcomes on synthetic fixtures.

Live runs consume model usage. --list inspects cases without invoking Codex.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib

from codex_session import run_session
from outcome_cases import CASES, grade, tool_calls
from outcome_cases import prepare

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins/ronny-codex-skills/skills"


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
        f"skills.config=[{{path={json.dumps(str(skill_file))},enabled={enabled}}}]",
    ]
    command = ["codex", "--no-daemon", "exec", "--json", "--ephemeral", "--strict-config",
               "--ignore-user-config", "--ignore-rules", "--sandbox", "workspace-write",
               "--skip-git-repo-check", "-C", str(cwd), "--add-dir", str(destination),
               "--model", args.model]
    for value in overrides:
        command += ["-c", value]
    return command + [query + "\nWork only in this synthetic fixture. Do not delegate, access accounts, or publish anything."]


def run_arm(case_id, arm, args, destination):
    destination.mkdir(parents=True)
    context = prepare(case_id, destination)
    cwd = context["cwd"]
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
    command = session_command(args, CASES[case_id]["query"], cwd, skill_dir / "SKILL.md", arm, destination)
    (destination / "request.json").write_text(json.dumps({"query": CASES[case_id]["query"], "command": command}, indent=2) + "\n")
    # Keep personal standing instructions and plugin state out of both arms.
    # Authentication is linked only in this private, disposable runtime home.
    auth = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json"
    with tempfile.TemporaryDirectory(prefix="codex-eval-home-") as runtime:
        if auth.is_file():
            Path(runtime, "auth.json").symlink_to(auth.resolve())
        env["CODEX_HOME"] = runtime
        record, events = run_session(command, cwd=cwd, timeout=args.timeout, env=env, output=destination)
    commands = [call["input"]["command"] for call in tool_calls(events)]
    read = any(f"/{skill}/SKILL.md" in command for command in commands)
    record.update(type="case", case=case_id, arm=arm, skill=skill,
                  skill_read=read, candidate_sha256=candidate_hash, available_sha256=available_hash,
                  artifacts=str(destination))
    if snapshot_hash(skill_dir) != available_hash:
        record["error"] = record["error"] or "skill_snapshot_changed"
    if arm == "disabled" and read:
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


def summarize(records):
    executed = [r for r in records if r["status"] != "skipped"]
    counts = {arm: {status: sum(r["arm"] == arm and r["status"] == status for r in records)
                    for status in ("pass", "fail", "error", "skipped")} for arm in ("enabled", "disabled")}
    pairs = []
    for case in dict.fromkeys(r["case"] for r in records):
        pair = {r["arm"]: r for r in records if r["case"] == case}
        if len(pair) == 2 and all(r["status"] in ("pass", "fail") for r in pair.values()):
            pairs.append(pair)
    rates = {arm: sum(p[arm]["status"] == "pass" for p in pairs) / len(pairs) if pairs else None
             for arm in counts}
    known = [r["reported_tokens"] for r in executed if r["reported_tokens"] is not None]
    missing = len(executed) - len(known)
    return dict(type="summary", counts=counts, comparable_pairs=len(pairs), pass_rates=rates,
                pass_rate_delta=rates["enabled"] - rates["disabled"] if pairs else None,
                observed_tokens=sum(known) if known else None, usage_missing_runs=missing,
                total_tokens=sum(known) if not missing else None, estimated_cost_usd=None,
                elapsed_seconds={arm: round(sum(r["elapsed_seconds"] for r in executed if r["arm"] == arm), 3)
                                 for arm in counts})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", choices=CASES, dest="cases")
    parser.add_argument("--model", help="Defaults to the model selected in user config; provider configuration is not inherited")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--token-budget", type=int, default=60000,
                        help="Admission threshold for reported input + output tokens; an active run may exceed it")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.timeout < 1 or args.token_budget < 1:
        parser.error("timeout and token budget must be positive integers")
    if args.list:
        print(json.dumps(CASES, indent=2))
        return 0
    args.model = args.model or configured_model()
    if not isinstance(args.model, str) or not args.model:
        parser.error("choose --model or set model in the user config")
    try:
        version = subprocess.run(["codex", "--version"], check=True, capture_output=True, text=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        parser.error(f"cannot check Codex version: {exc}")
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (0, 165, 0):
        parser.error("paired outcomes require Codex CLI >= 0.165.0 for the tested session controls")
    selected = list(dict.fromkeys(args.cases or CASES))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (args.output or Path(tempfile.gettempdir()) / f"codex-skill-outcomes-{stamp}").resolve()
    if output.exists():
        parser.error(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if subprocess.run(["git", "-C", str(output.parent), "rev-parse", "--show-toplevel"],
                      capture_output=True, timeout=15).returncode == 0:
        parser.error("output must be outside Git worktrees")
    if output.is_relative_to(ROOT):
        parser.error("output must be outside the package directory")
    output.mkdir(mode=0o700)
    args.candidates = output / "candidates"
    for skill in dict.fromkeys(CASES[c]["skill"] for c in selected):
        shutil.copytree(SKILLS / skill, args.candidates / skill,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    grader_hash = hashlib.sha256(Path(__file__).with_name("outcome_cases.py").read_bytes()).hexdigest()
    metadata = dict(type="run", codex_version=version, model=args.model, cases=selected,
                    grader_sha256=grader_hash,
                    timeout_seconds=args.timeout, token_budget=args.token_budget,
                    candidate_sha256={CASES[c]["skill"]: snapshot_hash(args.candidates / CASES[c]["skill"]) for c in selected})
    (output / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    records, observed, stop = [], 0, None
    with (output / "report.jsonl").open("x") as report:
        report.write(json.dumps(metadata) + "\n")
        for index, case_id in enumerate(selected):
            arms = ("enabled", "disabled") if index % 2 == 0 else ("disabled", "enabled")
            for arm in arms:
                if stop:
                    record = dict(type="case", case=case_id, arm=arm, status="skipped", reason=stop)
                else:
                    record = run_arm(case_id, arm, args, output / case_id / arm)
                    if record["reported_tokens"] is None:
                        stop = "usage_unknown"
                    else:
                        observed += record["reported_tokens"]
                        if observed >= args.token_budget:
                            stop = "token_budget"
                    if record["error"]:
                        stop = stop or "session_error"
                records.append(record)
                report.write(json.dumps(record) + "\n")
                report.flush()
                print(f"{record['status'].upper():7} {case_id:20} {arm:8} {record.get('error') or record.get('reason') or ''}", flush=True)
        summary = summarize(records)
        summary.update(token_budget=args.token_budget, admission_stop_reason=stop)
        report.write(json.dumps(summary) + "\n")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"Artifacts: {output}")
    failed = any(r["status"] in ("error", "skipped") or (r["arm"] == "enabled" and r["status"] == "fail") for r in records)
    return int(failed or not summary["comparable_pairs"])


if __name__ == "__main__":
    raise SystemExit(main())
