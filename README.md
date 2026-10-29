# codex-skills

Twelve development, review, verification and decision-memory workflows for Codex,
maintained independently from the Claude collection and licensed under [MIT](LICENSE). It uses the portable plugin manifest plus the supported Codex compatibility manifest, with a local marketplace at .agents/plugins/marketplace.json. No external connector or authentication service is required. Optional vault-memory lifecycle hooks require user authorization and Codex hook trust.

## Contents

current-docs, project-audit, ux-speed-audit, understand-before-changing, code-structure, no-ai-tells, no-ai-tells-audit, new-feature, evidence-driven-testing, vault-memory, managed-audit and system-reasoning.

For recurring workers, see [Codex loop admission and budgets](plugins/ronny-codex-skills/skills/system-reasoning/references/agent-loops.md).
For test design and maintenance, see [useful tests](plugins/ronny-codex-skills/skills/evidence-driven-testing/references/useful-tests.md).
The shared Codex guidance favors proportionate verification, meaningful retained
tests, realistic failure/recovery checks, and stopping after the relevant checks pass.

Use system-reasoning before substantial design decisions or unclear bug fixes:
derive requirements and invariants, separate evidence from assumptions, test
causal explanations, and verify the correction. Routine CRUD and established
local causes stay lightweight. code-structure and managed-audit hand off to this
skill when the decision needs it.

The historical no-ai-tells names remain recognizable, but their instructions concern readability rather than authorship detection. Skills are available for automatic matching and explicit invocation; their narrow descriptions do not mandate running every skill on every task. Use the namespaced selector shown by Codex if another plugin offers the same skill name.

## Managed audits

New task branches default to freshly fetched origin/main. The new-feature skill requires a successful fetch and base verification, preserves explicit release/PR bases, and does not pull into or reset local main just to create a branch.

Invoke `$managed-audit` for a manager-led audit with specialist workers or a station-by-station role/dashboard review. The manager owns task scope, live state, questions and final synthesis. Worker targets default to 15-minute checkpoints and a 60-minute assignment, with observable evidence instead of mandatory commits. These are operating targets; the skill does not install a timer or external supervisor. It provides bounded replacement and handoff guidance.

Keep platform URLs, account identities, credentials, reset permissions, implementation authority and station pacing in your task prompt. The skill does not confer them. Example:

```text
Use $managed-audit to understand this platform, map its actual roles and
customer journey, and audit one station at a time. Inspect each role's
rendered dashboard and perform an orientation walkthrough with the
designated test client. Ask focused questions as needed. Give me supported
findings and the simplest adequate improvements; discuss this station
with me before advancing. Do not implement changes yet.
```

## Install

Store the complete marketplace directory at a stable user-owned location, then run:

```bash
codex plugin marketplace add /absolute/path/to/codex-skills --json
codex plugin add ronny-codex-skills@ronny-local --json
codex plugin list --json
```

Clone the public repository to a stable source directory, then install:

```bash
git clone https://github.com/ronnyabuto/codex-skills.git ~/.local/src/codex-skills
cd ~/.local/src/codex-skills
python3 scripts/install_local.py --dry-run
python3 scripts/install_local.py
```

The repository is `codex-skills`; the installed plugin name remains
`ronny-codex-skills@ronny-local` for compatibility. The installed marketplace is
a separate verified release copy. Run upgrades from the Git source, not the
cache. Prior local installations can retain their vault, hooks and guidance.

Use codex plugin commands to manage configuration. Codex installs a cached copy; editing the source does not necessarily update the loaded plugin. Refresh the marketplace and reinstall/update through the supported client, then start a new session. Do not hand-edit the plugin cache.

The provided scripts/install_local.py copies only files verified by the release
inventory under ~/.codex/local-marketplaces/ronny-codex-skills, backs up Codex configuration, invokes the supported CLI commands and verifies installed/enabled status. With --migrate-duplicates it moves only byte-identical copies of the three skills installed during the preceding review into a backup, after the plugin is verified. It refuses unknown source directories, marketplace-name conflicts or modified duplicates rather than overwriting them. Use --dry-run to inspect targets. Claude paths are never install targets.

## Memory

The installer preserves the chosen vault in ~/.config/ronny-codex-skills/memory.json;
CODEX_MEMORY_VAULT can override it. Saving decisions and importing selected
Codex transcripts remain explicit operations. When authorized, trust the three
user-level memory hooks in Codex `/hooks` to archive before compaction and at session end,
and receive a bounded recall pointer at session start. The helper never reads
Claude archives or modifies Claude settings. See the memory skill for exclusions
and transcript-format limitations.

To upgrade from this repository while retaining an already configured vault:

```bash
python3 scripts/install_local.py --agent-guidance --memory-hooks
```

The optional --agent-guidance flag preserves existing global Codex AGENTS.md
text and updates only this package's marked block. Configuration and prior
marketplace source are backed up. Review and trust new hooks in `/hooks`; the
installer does not bypass trust. Restart Codex after plugin upgrades.

--memory-hooks merges three user-level handlers into ~/.codex/hooks.json and
preserves unrelated hooks. Commands use the stable installed marketplace path,
so the cache's version directory is not embedded in configuration. This route
was verified on the local CLI; bundled plugin-hook discovery was unavailable
there. Archive before compaction and at shutdown, not continuously; local
hooks do not imply support in cloud-orchestrated sessions.

## Validation

```bash
python3 scripts/validate.py
python3 -B -m unittest discover -s tests -v
```

Validation checks manifests, skill frontmatter, contained references, Python
syntax and exclusion of the inherited recorder. Tests cover memory scoping, realpath containment, concurrent notes, redaction, index freshness, transcript import and superseded notes. evals/cases.json retains independent positive/negative behavior scenarios; the
paired outcome runner now implements four synthetic enabled/disabled comparisons.
The catalog itself is not a completed model benchmark. Do not run paid agent evaluations without authorization. Each behavioral case needs a fresh disposable fixture and comparison with/without the skill.
See [paired outcome instructions and rubrics](evals/README.md) and
[Codex compatibility](references/codex-compatibility.md).

`python3 evals/run_system_reasoning.py <new-output-directory>` runs five
read-only Codex cases with fresh synthetic fixtures and saves JSONL events,
answers, token usage, and fixture-integrity checks. It uses the installed plugin
and configured Codex model. Invocation checks supplement human review of actual
answers; this smoke suite alone is not a comparative benchmark. API failures
are reported as errors. Keep output outside the package directory. `--timeout` bounds each case's
CLI process (240 seconds by default). `--token-budget` optionally stops admitting
cases after reported input + output tokens reach the threshold; an in-flight
case can exceed it. Missing usage stops further admission when a budget is set.
There is no invented dollar cap or fixed-price estimate: the installed CLI has
no Claude-style `--max-budget-usd` or `--max-turns` flag.

Each run retains the existing per-case `summary.json` plus `run-summary.json`
with executed/completed/error/skipped counts, elapsed time per case, reported
tokens, missing-usage counts, and tokens per completed eval when all executed
cases reported usage. Failed work counts toward observed usage. Cache and
reasoning subsets are retained without adding them twice. Empty, incomplete,
failed, timed-out or fixture-mutating runs are errors and produce nonzero exit
status. Dollar cost remains unknown. Full behavior review remains a separate
step from a successful CLI run.

Inspect paired cases without a model call:

```bash
python3 -B evals/run_outcome_evals.py --list
```

Run a paired comparison of the source snapshot (consumes model usage):

```bash
python3 -B evals/run_outcome_evals.py --case memory-recall --token-budget 250000
```

Outputs retain the exact candidate, native events and grading evidence outside
the package. Tokens are reported without a dollar estimate. The default
60,000-token admission threshold may stop before both arms complete; it does
not cap an active arm. Passing baselines are valid, and session errors remain
unscored. The existing smoke tests remain available.

Release 2.0.0 replaces the inherited recorder with an independently written
foreground FFmpeg recorder. Its `record`, `annotate` and `stop` commands retain
timestamped sidecar assertions; media verification decodes the captured video.
FFmpeg is a separate optional dependency. See the
[recorder interface](plugins/ronny-codex-skills/skills/evidence-driven-testing/references/recorder.md)
and [provenance](plugins/ronny-codex-skills/PROVENANCE.md). Synthetic media checks
do not establish that a real GUI flow works.

## Maintaining a release

Keep platform/runtime behavior local to this package. Skills, helper scripts
and references resolve inside the plugin tree; no sibling checkout is required.
After editing public source files, rebuild the inventory and run the checks:

```bash
python3 scripts/build_release.py
python3 scripts/build_release.py --check
python3 scripts/validate.py
python3 -B -m unittest discover -s tests -v
```

`build_release.py` inventories tracked and non-ignored public files. The
installer verifies those bytes before changing configuration and copies only
that inventory. Git metadata, ignored captures, caches, vault data and unrelated
local files are excluded from installation. Review `git diff` and the staged
file list before publishing; Git ignores are not a substitute for reviewing
what is being shared.

The CI workflow runs structural/inventory checks and the offline suite,
including synthetic recorder tests with FFmpeg. Paid model evaluations remain
explicit operations. The real media tests also accept `EVIDENCE_FFMPEG` as an
absolute binary path for an isolated test environment; no FFmpeg binary is
bundled or installed by this package.

## Reliability and privacy standards

Global coding invariants live in the managed block of `~/.codex/AGENTS.md`;
full skill procedures remain on demand. Project instructions and Codex's
`AGENTS.override.md` precedence still apply. The shared rules cover existing-code
investigation, module ownership, readability, version-sensitive documentation,
verification, task isolation and quiet performance measurements.

Memory reads and indexing are confined to `codex/` inside the chosen private
vault, including when another client shares the parent folder. Keep vaults and
indexes outside source trees and public sync; Git ignores do not govern zip/tar
or workspace shares. The current local vault is retained on upgrades.

The index retries SQLite busy errors during WAL initialization for at most five
seconds, then restores a five-second busy timeout and an immediate transaction.
Search limits each file to two chunks before applying the overall result limit.
Content hashes retain freshness, and failed refreshes roll back. Longer locks
can still fail; hooks report errors without blocking the session.

Redaction preserves numeric metrics and text after secret assignments, covers
Stripe secret/restricted keys, and redacts titles before filename generation.
Transcript import filters task notifications and injected repository bootstrap
instructions. Pattern redaction cannot guarantee removal of confidential prose.

The installer probes SQLite FTS5, materialized queries and window functions before
writing configuration. Eval cases get independent synthetic vaults and caches;
timeouts and malformed/empty answers are errors, and existing output directories
are never reused. Offline tests establish these boundaries; they are not paid
agent benchmarks. See [AUDIT.md](AUDIT.md) for findings and primary references.
