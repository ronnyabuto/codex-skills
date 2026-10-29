"""Exercise paired Codex runs through a local executable and real outcome graders."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "evals/run_outcome_evals.py"
FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys, time
if "--version" in sys.argv:
    print("codex-cli 0.165.0")
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
if arm == "enabled" or mode == "contaminated":
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
elif case == "query-evidence":
    script=pathlib.Path(".artifacts/probe.py")
    script.write_text("import json,sys\\nfrom pathlib import Path\\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]))\\nimport app\\nout={}\\nfor name in ('before','after'):\\n    db=app.connect()\\n    queries=[]\\n    db.set_trace_callback(queries.append)\\n    names=getattr(app,name)(db)\\n    out[name]=dict(query_count=len(queries),queries=queries,names=names)\\n    db.close()\\nprint(json.dumps(out))\\n")
    r=subprocess.run([sys.executable,str(script)],check=True,capture_output=True,text=True)
    pathlib.Path(".artifacts/probe-output.json").write_text(r.stdout if mode != "fail" else "not JSON")
    command("python3 .artifacts/probe.py")
print(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"Completed synthetic task."}}))
if mode == "error":
    print(json.dumps({"type":"turn.failed","error":{"message":"synthetic API failure"}}))
usage=None if mode == "missing-usage" else dict(input_tokens=100,output_tokens=20,cached_input_tokens=90,reasoning_output_tokens=5)
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
        proc = subprocess.run([sys.executable, "-B", str(RUNNER), "--model", "test-model",
                               "--output", str(self.root / "run"), *options],
                              capture_output=True, text=True, timeout=30,
                              env=dict(self.env, FAKE_OUTCOMES=json.dumps(outcomes or {})))
        report = self.root / "run/report.jsonl"
        records = [json.loads(line) for line in report.read_text().splitlines()] if report.exists() else []
        return proc, records

    def test_real_grading_isolated_pairs_snapshot_identity_and_native_controls(self):
        proc, records = self.run_evals()
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        runs = [r for r in records if r["type"] == "case"]
        self.assertEqual(len(runs), 8)
        self.assertTrue(all(r["status"] == "pass" for r in runs))
        self.assertEqual(records[-1]["comparable_pairs"], 4)
        self.assertEqual(records[-1]["pass_rate_delta"], 0)
        self.assertEqual(records[-1]["total_tokens"], 960)
        self.assertIsNone(records[-1]["estimated_cost_usd"])
        for run in runs:
            self.assertEqual(run["candidate_sha256"], records[0]["candidate_sha256"][run["skill"]])
            self.assertEqual(run["skill_read"], run["arm"] == "enabled")
            local = Path(run["artifacts"]) / ("assigned" if run["case"] == "assigned-worktree" else "project")
            self.assertEqual((local / ".agents/skills" / run["skill"] / "SKILL.md").exists(), run["arm"] == "enabled")
            self.assertEqual(run["reported_tokens"], 120)
            self.assertTrue((Path(run["artifacts"]) / "session.jsonl").is_file())
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(len({call["cwd"] for call in calls}), 8)
        for call in calls:
            self.assertFalse(Path(call["runtime_home"]).exists())
            self.assertFalse(Path(call["runtime_home"]).is_relative_to(self.root / "run"))
            self.assertIn("--ignore-user-config", call["args"])
            self.assertIn("features.hooks=false", call["args"])
            self.assertIn("features.plugins=false", call["args"])
            self.assertIn("features.multi_agent=false", call["args"])
            self.assertIn("project_doc_max_bytes=0", call["args"])
            self.assertIn("workspace-write", call["args"])
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", call["args"])

    def test_unauthorized_edits_fail_without_turning_baseline_success_into_failure(self):
        proc, records = self.run_evals("--case", "audit-scope", outcomes={"audit-scope:enabled":"fail"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([r["status"] for r in records[1:-1]], ["fail", "pass"])
        self.assertEqual(records[-1]["pass_rate_delta"], -1)

    def test_failed_work_counts_and_budget_stops_admission_mid_pair(self):
        proc, records = self.run_evals("--token-budget", "100", outcomes={"assigned-worktree:enabled":"error"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(records[1]["status"], "error")
        self.assertEqual(records[-1]["observed_tokens"], 120)
        self.assertEqual(records[-1]["admission_stop_reason"], "token_budget")
        self.assertEqual(records[-1]["comparable_pairs"], 0)
        self.assertTrue(all(r["status"] == "skipped" for r in records[2:-1]))
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
        self.assertEqual(records[2]["error"], "disabled_skill_read")
        self.assertEqual(records[-1]["comparable_pairs"], 0)

    def test_successful_fetch_without_fetch_head_is_valid(self):
        proc, records = self.run_evals("--case", "assigned-worktree", outcomes={
            "assigned-worktree:enabled": "fetch-no-head",
            "assigned-worktree:disabled": "fetch-verify",
        })
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        for run in records[1:-1]:
            check = next(c for c in run["checks"] if c["name"] == "fresh base retained")
            self.assertTrue(check["passed"])
            self.assertEqual(check["evidence"]["fetch_head"], "")
            self.assertTrue(check["evidence"]["successful_fetch_commands"])

    def test_timeout_retains_reported_usage_but_never_scores_success(self):
        proc, records = self.run_evals("--case", "audit-scope", "--timeout", "1",
                                      outcomes={"audit-scope:enabled": "timeout"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(records[1]["error"], "timeout")
        self.assertEqual(records[1]["checks"], [])
        self.assertEqual(records[-1]["observed_tokens"], 120)
        self.assertEqual(records[2]["status"], "skipped")
        self.assertEqual(records[-1]["comparable_pairs"], 0)

    def test_invalid_artifact_is_a_failed_outcome(self):
        proc, records = self.run_evals("--case", "query-evidence", outcomes={"query-evidence:enabled":"fail"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(records[1]["status"], "fail")
        self.assertFalse(records[1]["checks"][0]["passed"])

    def test_list_invalid_limits_and_existing_output_do_not_start_model_calls(self):
        proc, records = self.run_evals("--list")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(len(json.loads(proc.stdout)), 4)
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


if __name__ == "__main__":
    unittest.main()
