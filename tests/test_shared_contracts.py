"""Exercise drift detection on two independent synthetic source checkouts."""
import json
from pathlib import Path
import tempfile
import unittest

from evals.check_sibling_contracts import compare


class SharedContractTests(unittest.TestCase):
    def test_independent_layouts_match_and_contract_drift_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = (Path(directory) / name for name in ("claude", "codex"))
            for repo in (first, second):
                (repo / "evals").mkdir(parents=True)
                (repo / "evals/outcome_contracts.json").write_text(json.dumps({"case": {"query": "natural task"}}))
                skills = repo if repo == first else repo / "plugins/ronny-codex-skills/skills"
                for name in ("current-docs",):
                    (skills / name).mkdir(parents=True)
                    (skills / name / "SKILL.md").write_text("shared guidance")
                for reference in ("evidence-driven-testing/references/data-workflows.md",):
                    target = skills / reference
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("shared data guidance")
            codex_only = second / "plugins/ronny-codex-skills/skills/code-structure"
            codex_only.mkdir()
            (codex_only / "SKILL.md").write_text("Codex-only guidance; absent in the sibling")
            self.assertEqual(compare(first, second), [])
            (second / "evals/outcome_contracts.json").write_text(json.dumps({"case": {"query": "changed task"}}))
            self.assertEqual(len(compare(first, second)), 1)
            (first / "current-docs/SKILL.md").write_text("changed policy")
            self.assertEqual(len(compare(first, second)), 2)
            (first / "evidence-driven-testing/references/data-workflows.md").write_text("changed data policy")
            self.assertEqual(len(compare(first, second)), 3)


if __name__ == "__main__":
    unittest.main()
