"""Grade real scratch fetches without requiring a literal URL in the command."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from outcome_cases import grade, prepare


class FetchGradingTests(unittest.TestCase):
    def test_variable_remote_requires_the_correct_origin_and_fetched_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            context = prepare("assigned-worktree", Path(directory))
            scratch = Path(directory) / "verification.git"
            subprocess.run(["git", "init", "-q", "--bare", str(scratch)], check=True)
            fetched = subprocess.run(["git", "-C", str(scratch), "fetch", str(context["root"] / "origin.git"),
                                      "refs/heads/main:refs/heads/main"], check=True, capture_output=True, text=True)
            head = subprocess.check_output(["git", "-C", str(scratch), "rev-parse", "refs/heads/main"], text=True)
            output = fetched.stdout + fetched.stderr + head
            app = context["cwd"] / "calendar_app.py"
            app.write_text(app.read_text().replace(" + 1", ""))
            command = 'remote=$(git remote get-url origin); git --git-dir="$scratch" fetch "$remote" refs/heads/main:refs/heads/main'
            variants = [(command, output, True),
                        (command, output.replace(str(context["root"] / "origin"), "/unrelated/remote"), False),
                        (command, output.replace(context["base"], "0" * 40), False),
                        ("git rev-parse HEAD", output, False)]
            for invocation, evidence, expected in variants:
                with self.subTest(command=invocation, expected=expected):
                    events = [{"type": "item.completed", "item": {"type": "command_execution",
                               "command": invocation, "aggregated_output": evidence, "exit_code": 0}}]
                    checks = grade("assigned-worktree", context, events)
                    fresh = next(c for c in checks if c["name"] == "fresh base retained")
                    self.assertEqual(fresh["passed"], expected)
