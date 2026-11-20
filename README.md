# codex-skills

Twelve on-demand development, review, verification and decision-memory workflows
for Codex. The package is independent of other clients and licensed under
[MIT](LICENSE). Its stable plugin identity is
`ronny-codex-skills@ronny-local`.

| Skill | Use |
|---|---|
| `new-feature` | Fresh task bases, assigned workspaces and task-owned cleanup |
| `current-docs` | Uncertain behavior in version-specific official documentation |
| `system-reasoning` | Root causes, architectural choices and load-sized designs |
| `understand-before-changing` | Risky changes to unfamiliar behavior |
| `code-structure` | Concrete module ownership and shared-behavior questions |
| `project-audit` | Evidence-backed project health findings |
| `managed-audit` | Explicitly requested specialist or station audits |
| `ux-speed-audit` | Measured loading and interaction performance |
| `no-ai-tells` | Requested readability cleanup of a diff |
| `no-ai-tells-audit` | Requested repository-wide readability remediation |
| `evidence-driven-testing` | Realistic tests, replayable probes and captures |
| `vault-memory` | Bounded recall and authorized decision notes |

Skills match natural requests or explicit `$skill-name` mentions. Use the
namespaced selector shown by Codex when names overlap. They do not authorize
production changes, external publication or unrelated cleanup. The readability
skills make no claims about authorship.

## Install and upgrade

```bash
git clone https://github.com/ronnyabuto/codex-skills.git ~/.local/src/codex-skills
cd ~/.local/src/codex-skills
python3 scripts/install_local.py --dry-run
python3 scripts/install_local.py
```

The installer verifies `release-files.json`, backs up existing configuration,
copies the inventoried release to `~/.codex/local-marketplaces/ronny-codex-skills`,
installs through supported `codex plugin` commands and verifies cached resources.
It refuses modified release sources, conflicting marketplace names and unknown
duplicates. Verification lists only the local marketplace; CLI calls are bounded
to 120 seconds. Run upgrades from the Git checkout; do not edit the plugin cache.
The installer enables the plugin in the user-level Codex home, so it is available
across local workspaces using that home. Restart open Codex sessions to refresh
their plugin context.

`--migrate-duplicates` backs up only recognized byte-identical standalone skills
after verifying the plugin. Other clients' settings and skills are neither inspected nor changed.
For a manual marketplace installation, keep the checkout at a stable path:

```bash
codex plugin marketplace add /absolute/path/to/codex-skills --json
codex plugin add ronny-codex-skills@ronny-local --json
codex plugin list --json
```

## Optional memory and guidance

Choose a private vault outside source trees and public sync:

```bash
python3 scripts/install_local.py --vault ~/agent-vault --memory-hooks --agent-guidance
```

These flags explicitly change user-level configuration. The installer preserves
an existing vault selection; `CODEX_MEMORY_VAULT` can override it. Later upgrades
can omit `--vault`. Review and trust hooks with `/hooks`; installation never
bypasses trust. `--agent-guidance` updates only this package's marked block in
`~/.codex/AGENTS.md`, preserving other text.

Memory uses only the vault's `codex/` namespace. Local hooks recall a bounded
pointer at session start and archive before compaction and at session end.
Transcript formats can change; cloud orchestration does not run these local
command hooks. Pattern redaction is a backstop, not protection for all private
prose. See [memory commands and limits](plugins/ronny-codex-skills/skills/vault-memory/SKILL.md).

## Verification and maintenance

The evaluation harness requires Python 3.11+ and Codex CLI 0.170.0+. Memory
requires Python 3.10+ and SQLite FTS5 with window functions. This package
excludes the inherited recorder.

```bash
python3 scripts/build_release.py
python3 scripts/build_release.py --check
python3 scripts/validate.py
python3 -B -m unittest discover -s tests -v
```

Rebuild the inventory after public source changes. Tests use synthetic state;
live model evaluations consume usage and run only when requested. Inspect cases
without a model call using `python3 -B evals/run_outcome_evals.py --list`. The
paired runner covers all 12 skills, supports fresh rounds with `--runs N`, and
resumes from private evidence under `~/agent-eval-runs/` by default.

- [Evaluation, resume and grading limits](evals/README.md)
- [Current compatibility](references/codex-compatibility.md)
- [Efficient model and skill use](references/efficient-use.md)
- [Validation evidence and limits](VALIDATION.md)
- [Provenance](plugins/ronny-codex-skills/PROVENANCE.md)

For substantial designs, use [system-reasoning](plugins/ronny-codex-skills/skills/system-reasoning/SKILL.md).
Production-data rehearsals use the testing skill's
[project-owned workflow guidance](plugins/ronny-codex-skills/skills/evidence-driven-testing/references/data-workflows.md).
Concurrent writers need separate workspaces; performance measurements need a
quiet machine. Keep transcripts, vaults, credentials and captures out of the
release; Git ignores do not govern zip files or workspace shares.
