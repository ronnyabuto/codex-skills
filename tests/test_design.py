"""Check load arithmetic without pretending keywords establish design correctness."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from outcome_cases import grade, load_contracts, prepare


class DesignTests(unittest.TestCase):
    def test_peak_must_follow_volume_window_and_burst_assumption(self):
        reference = dict(daily_messages=2000, active_hours=10, burst_multiplier=10,
                         peak_messages_per_second=2000 / 36000 * 10)
        variants = [({}, True), ({"peak_messages_per_second": 0.005}, False),
                    ({"burst_multiplier": 0.5}, False), ({"active_hours": 0}, False),
                    ({"daily_messages": 500}, False), ({"burst_multiplier": True}, False),
                    ({"peak_messages_per_second": float("nan")}, False)]
        for change, expected in variants:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                context = prepare("design-sizing", Path(directory))
                artifacts = context["cwd"] / ".artifacts"
                (artifacts / "load.json").write_text(json.dumps({**reference, **change}))
                # Prose wording is left for review; rejected alternatives must not trip a keyword gate.
                (artifacts / "design.md").write_text("Reject Redis and RabbitMQ at this load.\nDelivery semantics need review.")
                checks = grade("design-sizing", context, [])
                self.assertEqual(all(c["passed"] for c in checks), expected)
                self.assertTrue(checks[0]["passed"])
                if expected:
                    (context["cwd"] / "app.py").write_text("unauthorized implementation")
                    self.assertFalse(grade("design-sizing", context, [])[0]["passed"])

    def test_platform_cases_cannot_redefine_shared_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("outcome_contracts.json", "outcome_contracts.codex.json"):
                (root / name).write_text(json.dumps({"same-case": {}}))
            with self.assertRaisesRegex(ValueError, "duplicate case"):
                load_contracts(root)
