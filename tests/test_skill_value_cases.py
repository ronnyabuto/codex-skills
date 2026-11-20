"""Reference outcomes and one-check near misses for the added fixtures."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from outcome_cases import CASES, git, grade, prepare, write
from run_outcome_evals import command_blocks, skill_reads
from skill_value_cases import SOURCES


EXPORT = SOURCES["polish-export"]["export.py"]
ORDERS = SOURCES["polish-package"]["orders.py"]
REFUNDS = SOURCES["polish-package"]["refunds.py"]


def without_first_line(source):
    return source.split("\n", 1)[1]


REPLAY = """import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dispatcher import deliver

def probe(failures):
    calls = 0
    def send():
        nonlocal calls
        calls += 1
        if calls <= failures:
            raise TimeoutError
    return [deliver(send), calls]

print(json.dumps(dict(recovered=probe(1), exhausted=probe(2))))
"""
SHIP = "def count(rows):\n    return sum(r['status'] in ('shipped', 'delivered') for r in rows)\n"
IMPORT = "from shipment import count\n\ndef {}(rows):\n    return count(rows)\n"
LEGACY = SOURCES["legacy-reader"]["store.py"].replace(".lower()", "")
HOLD = "def active(hold, now):\n    return hold['expires_at'] > now\n"
LEASE = dict(refresh_minutes=36, expiry_minutes=45, source="2026-11-04.md")
RELAY = dict(send_timeout_seconds=1, last_retry_hours=23, reuse_event_id=True,
             rollback=dict(sender_enabled=False, pending_events_retained=True, orders_enabled=True))
TIMINGS = dict(file="catalog.py", line=4, seconds=[0.2, 0.21, 0.22, 0.23, 0.24],
               median=0.22, range=[0.2, 0.24])
PIN = dict(file="docs/sdk-1.md", line=2)
# The pilot correctly located the insufficient validation at the guard.
REFUND = dict(file="orders.py", line=3, input=-5, actual_refunded=15, expected_refunded=20)
CHECKOUT = dict(file="checkout.py", line=5, actual_total=-5, expected_total=0)
RECOVERY = dict(recovered=["delivered", 2], exhausted=["pending", 2])


def reference(files=None, result=None):
    return {**(files or {}), **({".artifacts/result.json": json.dumps(result)} if result is not None else {})}


EXAMPLES = {
    "shared-imports": (
        reference({"shipment.py": SHIP, "web.py": IMPORT.format("web_count"),
                   "worker.py": IMPORT.format("worker_count")}),
        [{"worker.py": "def worker_count(rows): return 1\n"},
         {"billing.py": "from shipment import count as billable\n"},
         {"shipment.py": "def count(rows): return sum(r['status'] in ('shipped','deli'+'vered') for r in rows)\n"}]),
    "pinned-delivery": (
        reference({"dispatch.py": "import parcel_sdk\ndef send(parcel): return parcel_sdk.enqueue(parcel,retry_count=2)\n"}, PIN),
        [{"dispatch.py": "import parcel_sdk\ndef send(parcel): return parcel_sdk.enqueue(parcel,retry_count=3)\n"},
         {"requirements.lock": "parcel_sdk==2.0\n"}, reference(result={**PIN, "line": 1})]),
    "polish-export": (reference({"export.py": without_first_line(EXPORT)}),
                      [{"export.py": EXPORT}, {"export.py": without_first_line(EXPORT).replace(" + '\\n'", "")},
                       {"vendor/reader.py": "# rewritten\n"}]),
    "polish-package": (reference({"orders.py": without_first_line(ORDERS), "refunds.py": without_first_line(REFUNDS)}),
                       [{"orders.py": ORDERS}, {"refunds.py": REFUNDS},
                        {"orders.py": without_first_line(ORDERS).replace("return order['id']", "return int(order['id'])")},
                        {"generated/schema.py": "# rewritten\n"}]),
    "refund-health": (reference(result=REFUND), [{"README.md": "# edited\n"},
                      reference(result={**REFUND, "line": 8}), reference(result={**REFUND, "actual_refunded": 20})]),
    "checkout-audit": (reference(result=CHECKOUT), [{"README.md": "# edited\n"},
                       reference(result={**CHECKOUT, "line": 4}), reference(result={**CHECKOUT, "actual_total": 0})]),
    "legacy-reader": (reference({"store.py": LEGACY}), [
        {"store.py": LEGACY.replace("return token.strip()", "return token.strip().lower() if 'code' in row else token.strip()")},
        {"store.py": LEGACY.replace("row.get('code', row.get('ref'))", "row.get('code')")},
        {"store.py": LEGACY.replace("row.get('code', row.get('ref'))", "row.get('code') or row.get('ref')")}]),
    "startup-delay": (reference(result=TIMINGS), [{"catalog.py": SOURCES["startup-delay"]["catalog.py"] + "\n"},
                      reference(result={**TIMINGS, "line": 3}), reference(result={**TIMINGS, "median": 0.2})]),
    "lease-recall": (reference(result=LEASE), [reference(result={**LEASE, "refresh_minutes": 44}),
                     reference(result={**LEASE, "source": "2026-10-12.md"})]),
    "recovery-evidence": (reference({".artifacts/probe.py": REPLAY}, RECOVERY),
                          [{"dispatcher.py": SOURCES["recovery-evidence"]["dispatcher.py"] + "\n"},
                           reference(result={**RECOVERY, "exhausted": ["pending", 1]})]),
    "relay-recovery": (reference(result=RELAY), [{"README.md": "# altered\n"},
                        reference(result={**RELAY, "send_timeout_seconds": 3}),
                        reference(result={**RELAY, "last_retry_hours": 24}),
                        reference(result={**RELAY, "rollback": {**RELAY["rollback"], "orders_enabled": False}})]),
}


class AddedCaseTests(unittest.TestCase):
    def assert_failures(self, case, context, expected):
        checks = grade(case, context, [])
        self.assertEqual([check["name"] for check in checks], CASES[case]["checks"])
        self.assertEqual([check["name"] for check in checks if not check["passed"]], expected)

    def test_reference_and_isolated_near_misses(self):
        self.assertEqual(set(EXAMPLES) | {"hold-expiry"}, set(SOURCES))
        for case, (correct, misses) in EXAMPLES.items():
            self.assertEqual(len(misses), len(CASES[case]["checks"]))
            for index, variant in enumerate(({}, *misses)):
                with self.subTest(case=case, variant=index), tempfile.TemporaryDirectory() as directory:
                    context = prepare(case, Path(directory))
                    for name, contents in {**correct, **variant}.items():
                        write(context["cwd"], name, contents)
                    expected = [] if not index else [CASES[case]["checks"][index - 1]]
                    self.assert_failures(case, context, expected)

    def test_feature_base_independent_of_local_main_and_bug_fix(self):
        case = "hold-expiry"
        for index in range(4):
            with self.subTest(variant=index), tempfile.TemporaryDirectory() as directory:
                context = prepare(case, Path(directory))
                cwd = context["cwd"]
                git(cwd, "fetch", "origin")
                git(cwd, "switch", "--no-track", "-c", "work",
                    context["local"] if index == 1 else "origin/main")
                if index == 2:
                    git(cwd, "branch", "-f", "main", "origin/main")
                if index != 3:
                    write(cwd, "holds.py", HOLD)
                self.assert_failures(case, context,
                                     [] if not index else [CASES[case]["checks"][index - 1]])


def event(command, output="", exit_code=0):
    return {"type": "item.completed", "item": {"type": "command_execution",
            "command": command, "aggregated_output": output, "exit_code": exit_code}}


class TranscriptTests(unittest.TestCase):
    def test_only_real_reads_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frozen = root / "candidates/skill/SKILL.md"
            write(root, str(frozen.relative_to(root)), "# Synthetic skill heading\n")
            deleted = root / "project/.agents/skills/skill/SKILL.md"
            calls = [event(f"echo cat {frozen}"), event(f"rg --files {frozen}", str(frozen)),
                     event(f"cat <<EOF > {frozen}", ""), event(f"cat {deleted} || true", "No such file"),
                     event(f"cat {frozen}", "Permission denied", 1)]
            self.assertEqual(skill_reads(calls, root, "skill", {frozen}), [])
            calls.append(event(f"/bin/bash -lc 'sed -n \"1,20p\" {frozen}; false'",
                               "# Synthetic skill heading", 1))
            self.assertEqual(skill_reads(calls, root, "skill", {frozen}), [str(frozen)])

    def test_blocked_commands_are_diagnostic_evidence(self):
        calls = [event("cat <<EOF", "approval required by policy", 126),
                 event("touch file", "Read-only file system", 1),
                 event("git status", "Permission denied", 1),
                 event("printf 'hello' | wc -c", "5"), event("false", "", 1),
                 event("ls -la && rg --files --hidden",
                       "Failed to create stream fd: Operation not permitted\n"
                       "Failed to create stream fd: Operation not permitted\n"
                       "total 20\nholds.py")]
        self.assertEqual([row["kinds"] for row in command_blocks(calls)],
                         [["approval"], ["sandbox"], ["denied"]])
