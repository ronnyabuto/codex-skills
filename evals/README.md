# Behavioral evaluation plan

cases.json contains positive, negative and boundary requests with observable success criteria. These are scenarios, not completed benchmark results. Evaluate each with and without the selected skill using the same Codex model and tools. Create a fresh disposable fixture for every case, with no live credentials or production access. Repeat ambiguous/stochastic cases and capture task outcomes, invocation, unintended changes, commands, elapsed time and token use. Do not score merely whether a skill was opened.

Fixtures should provide the actual prerequisite for each case: pinned packages and matching documentation for current-docs, known faults and harmless executable tests for project-audit, a runnable production app with controlled timings for ux-speed-audit, committed code/history for legacy reasoning, separate worktrees and local remotes for isolation, and synthetic notes/transcripts for memory. Use local PR-shaped fixture data rather than real account mutations. Do not import personal archives into evaluations.

The package's unit tests validate concrete memory and installation invariants. They do not substitute for agent behavior evaluation. The catalog remains unrun unless a retained release report says otherwise;
there is no live desktop capture result for this release.

The system-reasoning smoke runner sets an independent `CODEX_MEMORY_VAULT` and
`CODEX_MEMORY_CACHE` for each synthetic case, including hook execution. Timeouts,
malformed streams, missing final answers and nonzero exits are unscored errors.
It requires a new output directory to prevent mixing evidence across runs.

The smoke runner records terminal events and rejects a final answer without a
completed turn. `--timeout` sets per-case runtime; `--token-budget` stops new
cases after the reported threshold or unknown usage. It does not cap a running
case. `run-summary.json` retains failures and missing usage, and leaves dollar
cost unknown. Token accounting counts input + output once, keeping cache and
reasoning subsets separate. Behavior still needs outcome review.

## Paired outcome runner (1.4.0)

`run_outcome_evals.py` compares the current package's selected skill with a
fresh disabled baseline. It requires Python 3.11+, Git and Codex CLI >= 0.165.0.
The helper scripts retain their existing Python 3.10+ requirement.

```bash
python3 -B evals/run_outcome_evals.py --list
python3 -B evals/run_outcome_evals.py --case memory-recall --token-budget 250000
python3 -B evals/run_outcome_evals.py --output /tmp/codex-skill-outcomes --token-budget 1000000
```

Omit `--case` to select all four cases; repeat it to select several. The model
comes from `--model` or the user's top-level `model` setting. The selected name
is retained, not replaced with a newer alias. The runner ignores other user
configuration; custom provider/profile configuration is not inherited. It uses
ordinary Codex authentication, which is not copied into fixtures or reports.

| Case | Observable checks |
|---|---|
| `assigned-worktree` | Preserve the assigned branch/worktree and fresh local-origin base, correct calendar results, and leave the main checkout untouched. |
| `audit-scope` | Keep source unchanged, identify the validation failure with a location and reproduction, and disclose unavailable delegation. |
| `memory-recall` | Recover the current decision and constraint, cite the dated source, reject superseded advice, and retrieve bounded source lines. |
| `query-evidence` | Retain and execute a replayable probe, preserve the implementation and customer names, and measure six SQL requests becoming one. |

Each run freezes the selected skill once under `candidates/`. Both arms get a
copy of that snapshot under project `.agents/skills/`; a session-only
`skills.config` override enables/disables its `SKILL.md` path. The disabled arm
also omits the entry-point file so file browsing cannot silently load its
instructions. Helpers and references remain available as fixture resources.
`candidate_sha256` identifies the frozen source in both arms;
`available_sha256` identifies the actual per-arm directory. No global skill
configuration changes. The runner records successful commands that read the
skill, separately from outcome grades; a disabled arm that reads it invalidates
the comparison. An enabled arm need not read the skill to pass the outcome.

The default private output directory is `/tmp/codex-skill-outcomes-<timestamp>/`.
An explicit `--output` must be new, outside this package and Git worktrees.
Outputs include `run.json`, `report.jsonl`, `summary.json`, frozen candidates,
and per-arm fixtures, native `session.jsonl`, stderr, final answers and
`grading.json` with the evidence behind every check. The synthetic Git origins
and worktrees stay in place so their metadata and replay paths remain valid.

`--timeout` bounds each CLI process (180 seconds by default). On POSIX, timeout
cleanup kills the CLI process group. `--token-budget` defaults to 60,000 reported
input + output tokens across both arms and all cases. It stops admitting new
arms after the threshold or missing usage; a running arm can exceed it. A
larger explicit allowance may be needed to finish a full comparison because
reported input includes cached input. Cache/reasoning counts remain subsets of
the reported usage, not extra tokens. Dollar cost stays unknown. No dollar or
turn-cap flags are invented for Codex.

A session error stops further admission. Errors and skipped arms are unscored
and exclude their pair; their available usage still counts. Missing usage
stays unknown. The runner exits nonzero on session errors, skipped arms,
enabled-arm failures or no complete pairs. A passing baseline is valid and
does not fail the run. Complete pairs report the enabled-minus-disabled
pass-rate difference; no positive improvement is assumed.

Each session gets a private temporary `CODEX_HOME` outside the evidence tree,
with only a link to the existing authentication file when present. No personal
AGENTS.md or plugin state is copied. The runtime home and any refreshed local
authentication data are removed afterward; credentials are not retained among
the artifacts. Both arms still use the same selected model and account.

The runner uses `--no-daemon`, `--ephemeral`, strict configuration,
`--ignore-user-config`, `--ignore-rules`, `project_doc_max_bytes=0`, disabled
plugins/hooks/apps/memory/delegation/browser features, and disabled web search.
This avoids teaching the baseline through global/project standing instructions
or the installed plugin. Built-in skills and managed policy can still affect
both arms. Synthetic environment variables isolate vaults/caches; no real notes
are imported. Shell commands use workspace-write sandboxing, with the synthetic
arm directory writable for local Git metadata, and no approval bypass.

These deterministic rubrics cover the stated observable contract; they do not
prove every reasoning step or prevent deliberate rubric gaming. Review the
retained transcripts for consequential claims. In particular, the audit case
checks the direct fallback when delegation is unavailable, not specialist
coordination. Do not describe one run per arm as a statistically established
quality or speed improvement. This package's formats are independent of the
Claude and skill-creator evaluation formats.

Offline checks use a local Codex stand-in and real fixtures/graders:

```bash
python3 -B -m unittest discover -s tests -v
```

They establish harness behavior, not model compliance. Keep full outcome
transcripts private and inspect them before sharing. Evaluate only trusted
skills; a read-capable process can access data outside the fixture, and the
runner does not isolate authentication or the whole operating system. No
production account mutations, uploads or personal configuration changes are
part of these synthetic evaluations.
