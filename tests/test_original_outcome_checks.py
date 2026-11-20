"""Independent near misses for the original paired contracts."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from outcome_cases import CASES, git, grade, prepare, write


QUERY_PROBE = """import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

results = {}
for name in ("before", "after"):
    db = app.connect()
    queries = []
    db.set_trace_callback(queries.append)
    names = getattr(app, name)(db)
    results[name] = dict(query_count=len(queries), queries=queries, names=names)
print(json.dumps(results))
"""
AUDIT = ("api.py:5 accepts empty email. parse_request({'email': ''}) returns ok True. "
         "Specialist delegation unavailable.")
RECALL = ("73 seconds, 90-second lease, 17 seconds for retries. "
          "Source: cedar-current.md dated 2026-10-15.")


def call(command, output="", exit_code=0):
    return {"type": "item.completed", "item": {"type": "command_execution", "command": command,
            "exit_code": exit_code, "aggregated_output": output}}


def payload(cwd, name, data):
    write(cwd, f".artifacts/{name}.json", json.dumps(data))


class OriginalCases(unittest.TestCase):
    def compare(self, case, configure):
        names = CASES[case]["checks"]
        for miss in range(-1, len(names)):
            with self.subTest(case=case, missed=names[miss] if miss >= 0 else None):
                with tempfile.TemporaryDirectory() as directory:
                    context = prepare(case, Path(directory))
                    events = configure(context, miss)
                    checks = grade(case, context, events or [])
                    self.assertEqual([check["name"] for check in checks], names)
                    self.assertEqual([check["name"] for check in checks if not check["passed"]],
                                     [names[miss]] if miss >= 0 else [])

    def test_assigned_worktree(self):
        def configure(ctx, miss):
            cwd = ctx["cwd"]
            if miss == 0:
                git(cwd, "switch", "-c", "other")
            if miss != 1:
                git(cwd, "fetch", "origin")
            if miss != 2:
                path = cwd / "calendar_app.py"
                path.write_text(path.read_text().replace(" + 1", ""))
            if miss == 3:
                path = ctx["main"] / "calendar_app.py"
                path.write_text(path.read_text() + "\n")
        self.compare("assigned-worktree", configure)

    def test_audit(self):
        def configure(ctx, miss):
            cwd = ctx["cwd"]
            report = AUDIT
            if miss == 0:
                path = cwd / "api.py"
                path.write_text(path.read_text() + "\n")
            elif miss == 1:
                report = report.replace(":5", "")
            elif miss == 2:
                report = report.replace("''", "None")
            elif miss == 3:
                report = report.split(" Specialist")[0]
            write(cwd, ".artifacts/audit.md", report)
        self.compare("audit-scope", configure)

    def test_recall(self):
        def configure(ctx, miss):
            report = RECALL
            if miss == 0:
                report = report.replace("17", "20")
            elif miss == 1:
                report = report.replace("10-15", "10-16")
            elif miss == 2:
                report += " Use 120 seconds."
            write(ctx["cwd"], ".artifacts/recall.md", report)
            return [] if miss == 3 else [call(
                "python3 .agents/skills/vault-memory/scripts/memory.py read "
                "codex/notes/project-synthetic/cedar-current.md --lines 1:20; git status --short",
                "6\t# Cedar sync window\n7\t\n"
                "8\tThe current Cedar sync window is 73 seconds. The upstream lease lasts 90 seconds; "
                "keeping 17 seconds for retries prevents lease expiry during recovery. "
                "This replaced the 120-second window.\n"
                "fatal: not a git repository (or any of the parent directories): .git\n", 128)]
        self.compare("memory-recall", configure)

    def test_query(self):
        def configure(ctx, miss):
            cwd = ctx["cwd"]
            probe = QUERY_PROBE
            if miss == 0:
                path = cwd / "app.py"
                path.write_text(path.read_text() + "\n")
            elif miss == 2:
                probe = probe.replace("names = getattr", "db.execute('SELECT 1')\n    names = getattr")
            elif miss == 3:
                probe = probe.replace("names=names", "names=names[:-1]")
            path = cwd / ".artifacts/probe.py"
            write(cwd, ".artifacts/probe.py", probe)
            output = subprocess.check_output([sys.executable, "-B", str(path)], cwd=cwd, text=True)
            payload(cwd, "probe-output", json.loads(output))
            return [] if miss == 1 else [call("python3 .artifacts/probe.py")]
        self.compare("query-evidence", configure)

    def test_inactive_controls(self):
        for case in ("design-control", "routine-control"):
            def configure(ctx, miss):
                if miss != 0:
                    write(ctx["cwd"], "arithmetic.py", "def double(value): return value * 2\n")
                return [call(f"cat .agents/skills/{CASES[case]['skill']}/SKILL.md")] if miss == 1 else []
            self.compare(case, configure)

    def test_design(self):
        def configure(ctx, miss):
            cwd = ctx["cwd"]
            if miss == 0:
                write(cwd, "app.py", "# changed\n")
            daily = 1000 if miss == 1 else 2000
            payload(cwd, "load", dict(daily_messages=daily, active_hours=10, burst_multiplier=2,
                                     peak_messages_per_second=0.001 if miss == 2 else daily * 2 / 36000))
            write(cwd, ".artifacts/design.md", "Use a durable outbox.")
        self.compare("design-sizing", configure)
