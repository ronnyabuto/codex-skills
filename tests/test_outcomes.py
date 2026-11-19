"""Exercise paired Codex runs through a local executable and real outcome graders."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "evals/run_outcome_evals.py"
CASE_COUNT = sum(len(json.loads((ROOT / "evals" / name).read_text()))
                 for name in ("outcome_contracts.json", "outcome_contracts.codex.json"))
FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys, time
if "--version" in sys.argv:
    print(os.environ.get("FAKE_VERSION", "codex-cli 0.170.0"))
    sys.exit(0)
args = sys.argv[1:]
setting = next(args[i+1] for i,v in enumerate(args[:-1]) if v == "-c" and args[i+1].startswith("skills.config="))
arm = "enabled" if "enabled=true" in setting else "disabled"
skill = next(pathlib.Path(".agents/skills").iterdir()).name
case = pathlib.Path.cwd().parent.parent.name
mode = json.loads(os.environ.get("FAKE_OUTCOMES", "{}")).get(case+":"+arm, "pass")
with open(os.environ["CALL_LOG"], "a") as stream:
    stream.write(json.dumps({"args":args,"cwd":str(pathlib.Path.cwd()),"arm":arm,"runtime_home":os.environ["CODEX_HOME"]})+"\\n")
def command(text, output=""):
    print(json.dumps({"type":"item.completed","item":{"type":"command_execution","command":text,"exit_code":0,"aggregated_output":output}}))
print(json.dumps({"type":"thread.started","thread_id":"fake-thread"}))
if (arm == "enabled" and case not in ("routine-control", "design-control")) or mode == "contaminated":
    command("cat " + str(pathlib.Path.cwd() / ".agents/skills" / skill / "SKILL.md"))
pathlib.Path(".artifacts").mkdir(exist_ok=True)
if case == "assigned-worktree":
    if mode == "fetch-verify":
        verification=pathlib.Path.cwd().parent / "verification.git"
        origin=pathlib.Path.cwd().parent / "origin.git"
        subprocess.run(["git","init","--bare",str(verification)],check=True,capture_output=True)
        fetch=["git","-C",str(verification),"fetch",str(origin),"refs/heads/main:refs/heads/main"]
        subprocess.run(fetch,check=True,capture_output=True)
        head=subprocess.run(["git","-C",str(verification),"rev-parse","refs/heads/main"],check=True,capture_output=True,text=True).stdout
        command(" ".join(fetch),head)
    else:
        fetch=["git","fetch","origin"] if mode != "fetch-no-head" else ["git","fetch","--no-write-fetch-head","origin"]
        subprocess.run(fetch,check=True,capture_output=True)
        command(" ".join(fetch))
    p=pathlib.Path("calendar_app.py")
    p.write_text(p.read_text().replace(" + 1",""))
elif case == "audit-scope":
    pathlib.Path(".artifacts/audit.md").write_text("api.py:5 accepts empty email. parse_request({'email': ''}) returns ok True. Specialist delegation unavailable; inspected directly.")
    if mode == "fail":
        pathlib.Path("api.py").write_text("# unauthorized edit")
elif case == "memory-recall":
    vault=pathlib.Path(os.environ["CODEX_MEMORY_VAULT"])
    note=next(vault.rglob("cedar-current.md"))
    pathlib.Path(".artifacts/recall.md").write_text("73 seconds; 90-second lease, 17 seconds for retries. Source: " + str(note.relative_to(vault)) + " dated 2026-10-15.")
    command("python3 .agents/skills/vault-memory/scripts/memory.py read " + str(note.relative_to(vault)) + " --lines 1:30")
elif case == "data-rehearsal":
    results = []
    for profile in ("sanitized", "legacy-shape"):
        result = subprocess.run([sys.executable, "workflow.py", "rehearse", "--profile", profile], capture_output=True, text=True)
        results.append(json.loads(result.stdout))
    pathlib.Path(".artifacts/rehearsal.json").write_text(json.dumps(dict(ready_for_release=False, deployment_performed=False, results=results)))
elif case in ("routine-control", "design-control"):
    pathlib.Path("arithmetic.py").write_text("def double(value):\\n    return value * 2\\n")
elif case == "design-sizing":
    pathlib.Path(".artifacts/design.md").write_text("Use the existing app and Postgres with a durable outbox. SMTP acknowledgement loss may cause duplicate delivery; require relay idempotency or accept at-least-once. Disable the sender to roll back.")
    pathlib.Path(".artifacts/load.json").write_text(json.dumps(dict(daily_messages=2000,active_hours=10,burst_multiplier=10,peak_messages_per_second=2000/36000*10)))
elif case == "query-evidence":
    script=pathlib.Path(".artifacts/probe.py")
    script.write_text("import json,sys\\nfrom pathlib import Path\\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]))\\nimport app\\nout={}\\nfor name in ('before','after'):\\n    db=app.connect()\\n    queries=[]\\n    db.set_trace_callback(queries.append)\\n    names=getattr(app,name)(db)\\n    out[name]=dict(query_count=len(queries),queries=queries,names=names)\\n    db.close()\\nprint(json.dumps(out))\\n")
    r=subprocess.run([sys.executable,str(script)],check=True,capture_output=True,text=True)
    pathlib.Path(".artifacts/probe-output.json").write_text(r.stdout if mode != "fail" else "not JSON")
    command("python3 .artifacts/probe.py")
print(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"Completed synthetic task."}}))
if mode.startswith("limit"):
    print(json.dumps({"type":"turn.failed","error":{"message":"You have hit your usage limit. Try again after reset."}}))
elif mode == "error":
    print(json.dumps({"type":"turn.failed","error":{"message":"synthetic API failure"}}))
usage=None if mode in ("missing-usage", "limit-missing-usage") else dict(input_tokens=100,output_tokens=20,cached_input_tokens=90,reasoning_output_tokens=5)
print(json.dumps({"type":"turn.completed","usage":usage}))
if mode == "timeout":
    sys.stdout.flush()
    time.sleep(5)
'''


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-outcome-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        binary = self.root / "bin"
        binary.mkdir()
        (binary / "codex").write_text(FAKE)
        (binary / "codex").chmod(0o755)
        self.env = dict(os.environ, PATH=f"{binary}{os.pathsep}{os.environ['PATH']}",
                        CALL_LOG=str(self.root / "calls.jsonl"), PYTHONDONTWRITEBYTECODE="1")

    def run_evals(self, *options, outcomes=None):
        defaults = [] if "--resume" in options else ["--model", "test-model", "--output", str(self.root / "run")]
        proc = subprocess.run([sys.executable, "-B", str(RUNNER), *defaults, *options],
                              capture_output=True, text=True, timeout=30,
                              env=dict(self.env, FAKE_OUTCOMES=json.dumps(outcomes or {})))
        report = self.root / "run/report.jsonl"
        records = [json.loads(line) for line in report.read_text().splitlines()] if report.exists() else []
        return proc, records

    def test_real_grading_isolated_pairs_snapshot_identity_and_native_controls(self):
        proc, records = self.run_evals()
        runs = [r for r in records if r["type"] == "case"]
        failures = [{"case": r["case"], "arm": r["arm"], "error": r.get("error"),
                     "checks": [c for c in r.get("checks", []) if not c["passed"]]}
                    for r in runs if r["status"] != "pass"]
        self.assertEqual(proc.returncode, 0, proc.stderr + json.dumps(failures, indent=2))
        self.assertEqual(len(runs), 2 * CASE_COUNT)
        self.assertTrue(all(r["status"] == "pass" for r in runs))
        self.assertEqual(records[-1]["comparable_pairs"], CASE_COUNT)
        self.assertIsNone(records[0]["requested_effort"])
        overhead = records[-1]["paired_overhead"]
        self.assertEqual(len(overhead), CASE_COUNT)
        self.assertTrue(all(row["turn_delta"] == 0 for row in overhead))
        self.assertTrue(all(row["token_delta"] == 0 for row in overhead))
        saved = self.root / "run/outcome-contracts.json"
        self.assertTrue(saved.is_file())
        self.assertEqual(len(records[0]["contracts_sha256"]), 64)
        contracts = json.loads(saved.read_text())
        for record in (r for r in records if r["type"] == "case"):
            request = json.loads((Path(record["artifacts"]) / "request.json").read_text())
            definition = contracts[record["case"]]
            expected = "\n\n".join(part for part in (definition["query"], definition["deliverable"]) if part)
            self.assertEqual(request["query"], expected)
            self.assertTrue(any(expected in arg for arg in request["command"]))
        self.assertEqual(records[-1]["pass_rate_delta"], 0)
        self.assertEqual(records[-1]["total_tokens"], 240 * CASE_COUNT)
        self.assertIsNone(records[-1]["estimated_cost_usd"])
        for run in runs:
            self.assertEqual(run["candidate_sha256"], records[0]["candidate_sha256"][run["skill"]])
            self.assertEqual(run["skill_read"], run["arm"] == "enabled" and run["case"] not in ("routine-control", "design-control"))
            local = Path(run["artifacts"]) / ("assigned" if run["case"] == "assigned-worktree" else "project")
            self.assertEqual((local / ".agents/skills" / run["skill"] / "SKILL.md").exists(), run["arm"] == "enabled")
            self.assertEqual(run["reported_tokens"], 120)
            self.assertTrue((Path(run["artifacts"]) / "session.jsonl").is_file())
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(len({call["cwd"] for call in calls}), 2 * CASE_COUNT)
        for call in calls:
            self.assertFalse(any(arg.startswith("model_reasoning_effort=") for arg in call["args"]))
            self.assertFalse(Path(call["runtime_home"]).exists())
            self.assertFalse(Path(call["runtime_home"]).is_relative_to(self.root / "run"))
            self.assertIn("--ignore-user-config", call["args"])
            self.assertIn("features.hooks=false", call["args"])
            self.assertIn("features.plugins=false", call["args"])
            self.assertIn("skills.bundled.enabled=false", call["args"])
            self.assertIn("features.multi_agent=false", call["args"])
            self.assertIn("project_doc_max_bytes=0", call["args"])
            self.assertIn("workspace-write", call["args"])
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", call["args"])

    def test_explicit_model_and_effort_reach_both_isolated_arms(self):
        proc, records = self.run_evals("--case", "routine-control", "--model", "gpt-6.1-sol",
                                       "--effort", "medium")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(records[0]["model"], "gpt-6.1-sol")
        self.assertEqual(records[0]["requested_effort"], "medium")
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        for call in calls:
            args = call["args"]
            self.assertEqual(args[args.index("--model") + 1], "gpt-6.1-sol")
            self.assertIn('model_reasoning_effort="medium"', args)
            index = args.index('model_reasoning_effort="medium"')
            self.assertEqual(args[index - 1], "-c")
            self.assertIn("--ignore-user-config", args)

    def test_unauthorized_edits_fail_without_turning_baseline_success_into_failure(self):
        proc, records = self.run_evals("--case", "audit-scope", outcomes={"audit-scope:enabled":"fail"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([r["status"] for r in records if r.get("type") == "case"], ["fail", "pass"])
        self.assertEqual(records[-1]["pass_rate_delta"], -1)

    def test_failed_work_counts_and_budget_stops_admission_mid_pair(self):
        proc, records = self.run_evals("--token-budget", "100", outcomes={"assigned-worktree:enabled":"error"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([r for r in records if r.get("type") == "case"][0]["status"], "error")
        self.assertEqual(records[-1]["observed_tokens"], 120)
        self.assertEqual(records[-1]["admission_stop_reason"], "token_budget")
        self.assertEqual(records[-1]["comparable_pairs"], 0)
        self.assertTrue(all(r["status"] == "skipped" for r in [r for r in records if r.get("type") == "case"][1:]))
        self.assertFalse((self.root / "run/assigned-worktree/disabled").exists())

    def test_missing_usage_stays_unknown_and_stops_new_calls(self):
        proc, records = self.run_evals("--case", "memory-recall", outcomes={"memory-recall:enabled":"missing-usage"})
        self.assertEqual(proc.returncode, 1)
        self.assertIsNone(records[-1]["observed_tokens"])
        self.assertIsNone(records[-1]["total_tokens"])
        self.assertEqual(records[-1]["usage_missing_runs"], 1)
        self.assertEqual(records[-1]["admission_stop_reason"], "usage_unknown")

    def test_disabled_skill_read_invalidates_comparison(self):
        proc, records = self.run_evals("--case", "memory-recall", outcomes={"memory-recall:disabled":"contaminated"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([r for r in records if r.get("type") == "case"][1]["error"], "disabled_skill_read")
        self.assertEqual(records[-1]["comparable_pairs"], 0)

    def test_successful_fetch_without_fetch_head_is_valid(self):
        proc, records = self.run_evals("--case", "assigned-worktree", outcomes={
            "assigned-worktree:enabled": "fetch-no-head",
            "assigned-worktree:disabled": "fetch-verify",
        })
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        for run in (r for r in records if r.get("type") == "case"):
            check = next(c for c in run["checks"] if c["name"] == "fresh base retained")
            self.assertTrue(check["passed"])
            self.assertEqual(check["evidence"]["fetch_head"], "")
            self.assertTrue(check["evidence"]["successful_fetch_commands"])

    def test_timeout_retains_reported_usage_but_never_scores_success(self):
        proc, records = self.run_evals("--case", "audit-scope", "--timeout", "1",
                                      outcomes={"audit-scope:enabled": "timeout"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([r for r in records if r.get("type") == "case"][0]["error"], "timeout")
        self.assertEqual([r for r in records if r.get("type") == "case"][0]["checks"], [])
        self.assertEqual(records[-1]["observed_tokens"], 120)
        self.assertEqual([r for r in records if r.get("type") == "case"][1]["status"], "skipped")
        self.assertEqual(records[-1]["comparable_pairs"], 0)

    def test_invalid_artifact_is_a_failed_outcome(self):
        proc, records = self.run_evals("--case", "query-evidence", outcomes={"query-evidence:enabled":"fail"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([r for r in records if r.get("type") == "case"][0]["status"], "fail")
        self.assertFalse([r for r in records if r.get("type") == "case"][0]["checks"][0]["passed"])

    def test_list_invalid_limits_and_existing_output_do_not_start_model_calls(self):
        proc, records = self.run_evals("--list")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(len(json.loads(proc.stdout)), CASE_COUNT)
        for option in ("--timeout", "--token-budget"):
            for value in ("0", "-1"):
                proc, _ = self.run_evals(option, value)
                self.assertEqual(proc.returncode, 2)
        output = self.root / "run"
        output.mkdir()
        marker = output / "preserve.txt"
        marker.write_text("existing evidence")
        proc, records = self.run_evals("--case", "audit-scope")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(marker.read_text(), "existing evidence")
        self.assertFalse((self.root / "calls.jsonl").exists())
    def test_routine_control_detects_unnecessary_skill_use(self):
        proc, records = self.run_evals("--case", "routine-control", outcomes={"routine-control:enabled": "contaminated"})
        self.assertEqual(proc.returncode, 1)
        enabled = next(r for r in records if r.get("type") == "case" and r.get("arm") == "enabled")
        self.assertEqual(enabled["status"], "fail")
        self.assertTrue(next(c["passed"] for c in enabled["checks"] if c["name"] == "arithmetic outcomes corrected"))
        self.assertFalse(next(c["passed"] for c in enabled["checks"] if c["name"] == "unrelated skill not used"))

    def calls(self):
        return [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]

    def test_limit_resume_keeps_attempts_and_counts_all_consumption(self):
        proc, records = self.run_evals("--case", "audit-scope", outcomes={"audit-scope:enabled": "limit"})
        self.assertEqual(proc.returncode, 75, proc.stderr)
        self.assertEqual(len(self.calls()), 1)
        failed = next(r for r in records if r.get("type") == "case")
        artifact = Path(failed["artifacts"]) / "session.jsonl"
        before = artifact.read_bytes()
        proc, records = self.run_evals("--resume", str(self.root / "run"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.calls()), 3)
        self.assertEqual(artifact.read_bytes(), before)
        summary = records[-1]
        self.assertEqual(summary["attempts"], 3)
        self.assertEqual(summary["total_tokens"], 360)
        self.assertEqual(summary["comparable_pairs"], 1)
        self.assertEqual(summary["unfinished_arms"], 0)
        self.assertEqual(summary["paired_overhead"][0]["token_delta"], 0)
        self.assertTrue((self.root / "run/audit-scope/enabled-retry-1/session.jsonl").is_file())
        proc, _ = self.run_evals("--resume", str(self.root / "run"))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(len(self.calls()), 3)

    def test_resume_does_not_fill_in_unknown_failed_usage(self):
        proc, _ = self.run_evals("--case", "audit-scope", outcomes={"audit-scope:enabled": "limit-missing-usage"})
        self.assertEqual(proc.returncode, 75)
        proc, records = self.run_evals("--resume", str(self.root / "run"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(records[-1]["observed_tokens"], 240)
        self.assertIsNone(records[-1]["total_tokens"])
        self.assertEqual(records[-1]["usage_missing_runs"], 1)

    def test_resume_after_admission_budget_reuses_the_completed_arm(self):
        proc, _ = self.run_evals("--case", "audit-scope", "--token-budget", "100")
        self.assertEqual(proc.returncode, 1)
        proc, records = self.run_evals("--resume", str(self.root / "run"), "--token-budget", "1000")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual(records[-1]["total_tokens"], 240)

    def test_resume_rejects_changed_identity_before_launch(self):
        self.run_evals("--case", "audit-scope", outcomes={"audit-scope:enabled": "limit"})
        run = self.root / "run"
        metadata_path = run / "run.json"
        original = json.loads(metadata_path.read_text())
        for field, value in (("codex_version", "codex-cli 0.169.0"),
                             ("inputs_sha256", {}), ("contracts_sha256", "changed")):
            with self.subTest(changed=field):
                metadata_path.write_text(json.dumps({**original, field: value}))
                proc, _ = self.run_evals("--resume", str(run))
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(len(self.calls()), 1)
        metadata_path.write_text(json.dumps(original))
        proc, _ = self.run_evals("--resume", str(run), "--model", "different")
        self.assertEqual(proc.returncode, 2)
        candidate = run / "candidates/managed-audit/SKILL.md"
        candidate.write_text(candidate.read_text() + "\nChanged candidate\n")
        proc, _ = self.run_evals("--resume", str(run))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("frozen candidate changed", proc.stderr)
        self.assertEqual(len(self.calls()), 1)

    def test_resume_hashes_real_fixture_and_harness_bytes(self):
        package = self.root / "source"
        for name in ("evals", "plugins"):
            shutil.copytree(ROOT / name, package / name, ignore=shutil.ignore_patterns("__pycache__"))
        command = [sys.executable, "-B", str(package / "evals/run_outcome_evals.py")]
        env = dict(self.env, FAKE_OUTCOMES=json.dumps({"audit-scope:enabled": "limit"}))
        first = subprocess.run(command + ["--case", "audit-scope", "--model", "test-model", "--output", str(self.root / "run")],
                               env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(first.returncode, 75, first.stderr)
        for relative in ("evals/fixtures/data-rehearsal/migration.sql", "evals/codex_session.py",
                         "evals/outcome_contracts.codex.json"):
            with self.subTest(changed=relative):
                path = package / relative
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                # Contract whitespace is intentionally canonicalized; change a real field instead.
                if path.suffix == ".json":
                    definitions = json.loads(path.read_text())
                    definitions["design-sizing"]["query"] += " Changed request."
                    path.write_text(json.dumps(definitions))
                result = subprocess.run(command + ["--resume", str(self.root / "run")],
                                        env=env, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 2)
                self.assertIn("changed since", result.stderr)
                self.assertEqual(len(self.calls()), 1)
                path.write_bytes(original)

    def test_interrupted_attempt_and_torn_checkpoint_are_recoverable(self):
        self.run_evals("--case", "audit-scope", outcomes={"audit-scope:enabled": "limit"})
        report = self.root / "run/report.jsonl"
        lines = [json.loads(line) for line in report.read_text().splitlines()]
        # Simulate a killed launcher: the durable start survived, its result did not.
        kept = [r for r in lines if r["type"] in ("run", "attempt_started")]
        report.write_text("".join(json.dumps(r) + "\n" for r in kept) + '{"type":')
        proc, records = self.run_evals("--resume", str(self.root / "run"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(records[-1]["attempts"], 3)
        self.assertIsNone(records[-1]["total_tokens"])
        self.assertEqual(records[-1]["usage_missing_runs"], 1)
        self.assertIsNone(records[-1]["elapsed_seconds"]["enabled"])
        self.assertTrue(list((self.root / "run").glob("report-partial-*.txt")))

    @unittest.skipUnless(os.name == "posix", "POSIX advisory lock check")
    def test_resume_cannot_write_to_an_active_run(self):
        import fcntl
        self.run_evals("--case", "audit-scope", outcomes={"audit-scope:enabled": "limit"})
        run = self.root / "run"
        before = (run / "report.jsonl").read_bytes()
        with (run / "runner.lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result, _ = self.run_evals("--resume", str(run))
        self.assertEqual(result.returncode, 2)
        self.assertIn("another runner", result.stderr)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual((run / "report.jsonl").read_bytes(), before)

    def test_design_control_catches_unnecessary_activation(self):
        proc, records = self.run_evals("--case", "design-control", outcomes={"design-control:enabled": "contaminated"})
        self.assertEqual(proc.returncode, 1)
        enabled = next(r for r in records if r.get("type") == "case" and r["arm"] == "enabled")
        self.assertEqual(enabled["status"], "fail")
        self.assertEqual([c["passed"] for c in enabled["checks"]], [True, False])


class RecallCitationTests(unittest.TestCase):
    def test_source_date_accepts_equivalent_formats_and_rejects_wrong_dates(self):
        sys.path.insert(0, str(ROOT / "evals"))
        from outcome_cases import grade
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            (cwd / ".artifacts").mkdir()
            for date, expected in (("2026-10-15", True), ("October 15, 2026", True),
                                   ("15 October 2026", True), ("Oct. 15th, 2026", True),
                                   ("October 16, 2026", False), ("2025-10-15", False)):
                with self.subTest(date=date):
                    (cwd / ".artifacts/recall.md").write_text(
                        f"73 seconds, 90-second lease, 17 seconds for retries. Source: codex/notes/project-120abcdef0123456/cedar-current.md, {date}.")
                    checks = grade("memory-recall", {"cwd": cwd}, [])
                    cited = next(c for c in checks if c["name"] == "source and date cited")
                    self.assertEqual(cited["passed"], expected)
                    self.assertTrue(next(c["passed"] for c in checks if c["name"] == "superseded decision excluded"))
            note = cwd / ".artifacts/recall.md"
            note.write_text(note.read_text() + " The window is 120 seconds.")
            checks = grade("memory-recall", {"cwd": cwd}, [])
            self.assertFalse(next(c["passed"] for c in checks if c["name"] == "superseded decision excluded"))


if __name__ == "__main__":
    unittest.main()
