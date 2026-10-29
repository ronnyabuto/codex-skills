import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "evals/run_system_reasoning.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("eval_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class EvalTests(unittest.TestCase):
    def run_case(self, output, result=None, timeout=False, options=()):
        execute = subprocess.run
        environments = []
        def fake_run(command, **kwargs):
            if command[0] == "git":
                return execute(command, **kwargs)
            environments.append(kwargs["env"])
            if timeout:
                raise subprocess.TimeoutExpired(command, 240, output=b'{"type":')
            return subprocess.CompletedProcess(command, 0, result or "", "")
        with patch.object(sys, "argv", [str(SCRIPT), str(output), "--case", "known-local-bug", *options]), patch.object(subprocess, "run", side_effect=fake_run), patch("builtins.print"):
            runner.main()
        return json.loads((output / "summary.json").read_text())[0], environments

    def test_synthetic_vault_and_successful_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results"
            event = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Remove the extra day."}})
            report, environments = self.run_case(output, event + '\n' + json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 90, "output_tokens": 10, "reasoning_output_tokens": 5}}))
            self.assertFalse(report["error"])
            self.assertTrue(report["fixture_unchanged"])
            summary = json.loads((output / "run-summary.json").read_text())
            self.assertEqual(report["reported_tokens"], 110)
            self.assertEqual(summary["tokens_per_completed_eval"], 110)
            self.assertIsNone(summary["estimated_cost_usd"])
            self.assertTrue(Path(environments[0]["CODEX_MEMORY_VAULT"]).is_relative_to(output))
            self.assertTrue(Path(environments[0]["CODEX_MEMORY_CACHE"]).is_relative_to(output))

    def test_timeout_still_writes_an_error_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            report, _ = self.run_case(Path(directory) / "results", timeout=True)
            self.assertTrue(report["error"])

    def test_empty_or_malformed_events_are_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, stdout in enumerate(("", '{"type":')):
                report, _ = self.run_case(Path(directory) / str(index), stdout)
                self.assertTrue(report["error"])

    def test_final_answer_without_completed_turn_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            event = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Looks done."}})
            output = Path(directory) / "results"
            report, _ = self.run_case(output, event)
            self.assertTrue(report["error"])
            summary = json.loads((output / "run-summary.json").read_text())
            self.assertEqual(summary["usage_missing_cases"], 1)
            self.assertIsNone(summary["observed_tokens"])
            self.assertIsNone(summary["tokens_per_completed_eval"])

    def test_budget_includes_failed_work_and_stops_new_launches(self):
        for missing_usage in (False, True):
            with self.subTest(missing_usage=missing_usage), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "results"
                case = runner.CASES[-1]
                cases = [("first", *case[1:]), ("second", *case[1:])]
                events = [{"type": "turn.failed", "error": {"message": "Interrupted"}}]
                if not missing_usage:
                    events.insert(0, {"type": "turn.completed", "usage": {"input_tokens": 90, "output_tokens": 20}})
                execute = subprocess.run
                calls = []
                def fake_run(command, **kwargs):
                    if command[0] == "git":
                        return execute(command, **kwargs)
                    calls.append(command)
                    return subprocess.CompletedProcess(command, 1, "\n".join(map(json.dumps, events)), "")
                with patch.object(runner, "CASES", cases), patch.object(sys, "argv", [str(SCRIPT), str(output), "--token-budget", "100"]), patch.object(subprocess, "run", side_effect=fake_run), patch("builtins.print"):
                    self.assertEqual(runner.main(), 1)
                reports = json.loads((output / "summary.json").read_text())
                summary = json.loads((output / "run-summary.json").read_text())
                self.assertEqual(len(calls), 1)
                self.assertTrue(reports[0]["error"])
                self.assertTrue(reports[1]["skipped"])
                self.assertFalse((output / "second").exists())
                self.assertEqual(summary["observed_tokens"], None if missing_usage else 110)
                self.assertEqual(summary["admission_stop_reason"], "usage_unknown" if missing_usage else "token_budget")

    def test_existing_output_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                self.run_case(Path(directory))


if __name__ == "__main__":
    unittest.main()
