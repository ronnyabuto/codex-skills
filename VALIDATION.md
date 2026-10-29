# Public release validation — 2.0.0

- All 57 offline tests pass on Python 3.14.4 / SQLite 3.46.1. This includes the
  existing 48 memory, hooks, installer and eval cases, two release-inventory
  installation cases, and seven original-recorder cases.
- The independently written recorder was tested with FFmpeg 7.0.2 from an
  isolated test dependency outside this repository. Real synthetic video was
  encoded, finalized to MP4 and decoded. Concurrent annotations, graceful stop,
  automatic duration limits, corrupt media, missing dependencies, capture
  failure, completed-session idempotence and output preservation were checked.
- These media tests establish recorder/toolchain behavior. Desktop capture
  permissions and real application interaction were not tested on Linux,
  macOS or Windows for this release. Native Wayland capture is not implemented.
  No synthetic frame is presented as GUI evidence.
- Root and bundled plugin MIT licenses match. The inherited recorder is excluded
  from this public source and initial Git history; its known hash is rejected
  by structural validation. The new recorder has a different command and
  sidecar-report protocol, documented in its reference.
- The release inventory is rebuilt from Git-visible, non-ignored source files.
  Installation validates file contents before changing configuration and copies
  only that snapshot. Tests reject modified resources, traversal, Git/private
  artifact paths and symlinks that escape the package. An unrelated local file
  cannot enter the installed package merely by being in the source checkout.
- All twelve skills, portable and compatibility manifests, contained references
  and Python syntax pass structural validation. Plugin resources resolve inside
  the installed plugin; the license is bundled as well as present at repo root.
- The CI workflow checks Python 3.11 and 3.14 with FFmpeg and no model calls.
  Its actions are pinned to verified upstream release commits. CI results are
  independent of the local results recorded here.
- Previously completed live outcome comparisons are retained below as historical
  local-release evidence. They are not new model evaluations of release 2.0.0.
  Raw transcripts, private notes, authentication data, captures and installation
  backups are excluded from public release contents.
- The installed plugin identifier remains `ronny-codex-skills@ronny-local`.
  The source repository is `ronnyabuto/codex-skills`. Installation retains the
  chosen vault and existing hook definitions/trust and does not target Claude.

## Local release validation — 2026-10-29 (1.4.0)

- All 48 offline tests pass. Existing memory, hooks, installer and smoke-runner
  tests are retained. New cases cover WAL lock release, persistent-lock recovery,
  corrupt-index/nonfatal-hook failure, native event grading, paired fixture and
  snapshot isolation, token admission, unknown usage, timeout cleanup, baseline
  contamination, valid sandbox-compatible fetches and protected output files.
- All twelve entrypoints, manifests, contained references, Python syntax and
  unchanged recorder provenance pass package validation. Python 3.14.4 and
  SQLite 3.46.1 were used; the paired runner requires Python 3.11+.
- The original Python helper failed concurrent cold startup on round 5 with
  eight workers. After the bounded WAL initialization correction, 30 rounds
  of eight workers completed without failures (240 successful starts).
- Four live synthetic enabled/disabled comparisons were completed with Codex
  CLI 0.165.0 and the user's selected `gpt-6.1-sol` model. All four enabled arms
  pass. Three baselines pass; the memory baseline recalls the correct decision
  but reads whole notes and fails only the bounded-retrieval criterion.
  This is a procedural difference, not evidence of better factual recall or
  a statistically established quality/speed improvement.
- Fresh-base grading was corrected to accept successful fetches without
  FETCH_HEAD and fresh verification through a scratch repository. The worktree
  pair was regraded against retained native traces and actual Git state;
  original grades were preserved. Both arms pass under the corrected rubric.
- The earlier non-isolated comparison is invalid: its disabled arm manually
  opened the skill despite its discovery override. Final comparisons use
  private transient runtime homes and omit the disabled entry point. Only an
  authentication-file link enters the temporary home; credentials are not
  retained with evidence. Commands still use Codex workspace-write sandboxing.
- The smoke catalog and prior results remain historical evidence. Shared native
  parsing now serves both runners, with cache/reasoning subsets counted once.
  No unsupported dollar/turn caps, Claude invocation fields or permanent skill
  visibility changes were added. Dollar cost remains unknown.
- Evidence is retained locally in `/tmp/codex-skills-evidence-1029/`: cold-start
  before/after results, `live-worktree-isolated/regraded-summary.json`, and the
  six remaining arms under `live-remaining-isolated/`. Invalid, incomplete and
  sandbox-blocked attempts remain separate; their usage is not hidden or
  presented as valid comparisons.
- This source is upgraded through `scripts/install_local.py`, which backs up
  configuration and the prior marketplace, uses supported Codex plugin commands,
  compares every installed resource, and verifies Claude state is unchanged.
  Existing vault selection and hooks are preserved; no trust bypass is used.
  A new Codex session is required to load the updated plugin instructions.
- No GUI recorder changes or new desktop recording claims are part of this
  release. Structural checks and these small rubrics do not establish complete
  model workflow compliance or resistance to deliberate rubric gaming.

## Release validation — 2026-10-16 (1.3.0)

- All 36 offline tests pass. The two added cases cover incomplete terminal
  streams and admission after failed-work token consumption or unknown usage.
  Existing usage checks now use a realistic completed-turn event and verify
  that cache/reasoning subsets are not counted twice.
- All twelve entrypoints, manifests, contained references, Python syntax and
  unchanged recorder provenance pass package validation.
- Codex CLI 0.163.0 help and current official documentation were checked for
  JSONL usage, sandboxing, ephemeral runs and scheduled-task boundaries.
- Loop and test-selection guidance is adapted to Codex. No Claude commands,
  completion-hook fields, or unsupported dollar/turn cap flags are assumed.
- This release adds two unrun behavioral scenarios and preserves previous IDs.
  No paid model benchmark or GUI recording was run for this release.
- The offline suite reports a pre-existing Python 3.14 ResourceWarning for an
  installer SQLite probe; all tests pass. That unrelated issue remains outside
  this change.

## Release validation — 2026-10-13 (1.2.2)

- All 34 offline tests pass; all twelve skill entrypoints, manifests, contained
  references, Python syntax and recorder provenance pass structural validation.
- Synthetic reproductions verify search diversity, redaction/context preservation,
  Codex-only namespace isolation, concurrent indexing and rollback, hook payload
  validation, independent eval memory and error reporting.
- Python 3.14.4 / SQLite 3.46.1 supplies FTS5 on this PC. The installer now checks
  runtime query capabilities before touching user configuration.
- The installed 1.2.1 source and cache matched before the upgrade. Version 1.2.2
  is installed through Codex plugin commands, not cache-file edits.
- The chosen private Codex vault is preserved. Global guidance changes only this
  package's marked block. Existing hook definitions/trust and Claude configuration
  are preserved. Native session restarts are needed to load the new plugin.
- No new paid agent evals or GUI recordings were run; prior live smoke results
  below are historical evidence, not results for this release.

## Release validation — 2026-10-09 (1.2.0)

- Package validation and all twelve skill entrypoints pass structural checks.
- Twenty-four isolated tests pass: memory scoping/imports, installation safety,
  guidance preservation, hook preservation/idempotence, archive updates,
  exclusions, redaction, malformed/torn transcripts, search/read, and recall.
- Five live system-reasoning smoke cases passed on this PC with Codex CLI
  0.161.0 and its default GPT-6.1-Sol model. Three positive cases read the skill;
  routine CRUD and an established local bug did not. Answers and harmless
  probes were reviewed; all fixture hashes remained unchanged. See
  [evals/system-reasoning-results.json](evals/system-reasoning-results.json).
  These are single runs on synthetic fixtures, without a comparative baseline.
  The other catalog scenarios have not been run.
- The installed/enabled 1.2.0 plugin contains all twelve skill entrypoints and
  resources. Global Codex AGENTS.md includes the scoped guidance block.
  Installation preserves Claude settings/skills and the existing Codex vault.
- This CLI's hook browser did not discover bundled plugin hooks. Installation
  uses user-level ~/.codex/hooks.json instead. All three exact hook definitions
  were reviewed and trusted through the native `/hooks` interface; the browser
  reports one installed and active handler for each event.
- A real local Codex session archived on shutdown into the configured vault;
  search and bounded reads recovered its unique test marker. A native `/compact`
  archived another session before compaction completed. The immediate model
  continuation identified the correct vault and pre-compaction archive from
  its injected pointer without tools. Hook JSON recall and compaction pointers
  also pass isolated tests. These results concern local
  Codex execution, not cloud-orchestrated hook support.

## Previous release — 2026-10-02

- All eleven skills pass Codex's bundled quick_validate.py.
- Portable/Codex compatibility manifests, marketplace, relative references, entrypoint lengths, Python syntax and retained recorder hash pass scripts/validate.py.
- Fifteen isolated tests pass: ten memory tests and five installation safety tests. They cover scoped recall, worktree identity, bounded output, fresh indexes, redaction examples, supersession, concurrent note writes, containment, explicit transcript imports, preserved duplicates after a failed plugin verification, modified/symlink duplicate refusal, mutation-free dry runs and a local upgrade that preserves Claude/memory configuration without attempting a Git-marketplace refresh.
- One hundred ten behavioral scenarios are provided, ten per skill. They are marked not-run; no paid model evaluations were performed. The new managed-audit cases cover manager requests, narrow non-trigger requests, evidence without commits, missing tools and preservation of audit permissions.
- The retained recorder's doctor was run during the preceding review and reported missing ffmpeg/ffprobe and no capture source in that execution environment. GUI recording, interruption recovery and browser capture are not end-to-end validated here.
- Local installation is checked with codex plugin list --json and byte comparisons against all installed skill entrypoints. The installer compares Claude settings, skill contents and symlink targets before/after the operation. The original three standalone Codex skills were backed up during initial installation; updates retain those backups and the memory configuration.

The structural checks use this package's supported subset, not full remote JSON Schema validation. Passing them does not prove agent workflow quality. The unit tests use only synthetic notes/transcripts and disposable Git fixtures.
