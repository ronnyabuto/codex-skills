# Evaluate skill outcomes

Offline tests exercise helpers and real synthetic fixtures through a local CLI
stand-in. They do not call a model or establish that Codex follows a skill:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B evals/run_outcome_evals.py --list
```

`cases.json` is the generated manual scenario catalog, not completed benchmark
results. Edit `scripts/build_eval_cases.py` and regenerate it when scenarios change.

## Paired runs

Live runs consume usage and require explicit authorization, Python 3.11+, Git
and Codex CLI 0.170.0+. They compare fresh enabled/disabled sessions on identical
synthetic starting state. Select the same exact model and effort for both arms:

```bash
python3 -B evals/run_outcome_evals.py --model gpt-6.2-sol --effort medium \
  --case design-sizing --case design-control --runs 3 --token-budget 250000
```

Without `--model`, the runner reads the selected user model. It does not inherit
custom provider/profile configuration or personal effort settings. Requested
settings are recorded; they are not proof of the server's effective settings.

| Case | Observable contract |
|---|---|
| `assigned-worktree` | Preserve the assigned branch/base and main checkout; correct calendar results |
| `audit-scope` | Keep source unchanged; report the actual defect, reproduction and unavailable delegation |
| `memory-recall` | Recover the current dated decision with bounded reads; exclude superseded advice |
| `query-evidence` | Retain/replay a probe, preserve returned customers and measure query counts |
| `data-rehearsal` | Expose the legacy collision through the approved job without exporting, deploying or editing the workflow |
| `routine-control` | Fix arithmetic without activating unrelated documentation guidance |
| `design-sizing` | Preserve source and derive consistent daily/peak arithmetic; leave design quality for review |
| `design-control` | Fix arithmetic without activating system-reasoning |
| `shared-imports` | Reuse the shipment rule through both callers and preserve billing policy |
| `pinned-delivery` | Cite the pinned contract and exercise the actual SDK call |
| `polish-export` | Remove redundant narration while retaining export behavior and scope |
| `polish-package` | Clean up multiple modules while retaining behavior and generated sources |
| `refund-health` | Locate and reproduce an invalid refund state without editing source |
| `legacy-reader` | Restore case preservation while keeping fallback and tombstones |
| `startup-delay` | Identify the blocking startup path and report a measured distribution |
| `checkout-audit` | Locate the checkout defect and reproduce the incorrect total |
| `hold-expiry` | Branch from a genuinely newer local remote tip and fix the expiry boundary |
| `lease-recall` | Recover the current decision from a local session with a superseded decoy |
| `recovery-evidence` | Replay delivery after a transient failure and after retry exhaustion |
| `relay-recovery` | Bound calls, respect deduplication retention and back out sending safely |

Contracts marked `held_out` were written for this comparison. Use the pilot
to review graders and isolation in both arms. Preserve the original pilot when
correcting a grader, then run blind repetitions without changing the candidate
skills. A control case measures unnecessary activation and doesn't establish
value on a task that needs the skill. The managed audit fixtures exercise
direct investigation when workers are unavailable. The current-docs fixture
uses local vendor documentation and does not measure online research.

The six common contracts remain in `outcome_contracts.json`; Codex-only cases
live in `outcome_contracts.codex.json`. Duplicate names are rejected. Only the
natural request and output serialization reach the model; hidden check names
and review criteria are not injected.

The design case checks the stated volume and active window against an explicit
burst multiplier and computed rate. It rejects below-average peaks, invalid
units-as-values and inconsistent arithmetic. It does not grade prose by mentions
of brokers, idempotency or timeouts. `design_review: pending` and the retained
criteria require a person to assess component choices, acknowledgement-loss
semantics, call bounds, rollout/rollback and the 10× bottleneck. An automated
pass is not a completed design review.

## Limits and resume

`--runs N` creates N fresh pairs per case. Cases run in rounds and the first arm
of each pair alternates between rounds. `summary.json` includes per-case pass counts, observed tokens, skill reads, and command
blocks by arm. Round one uses the original case directories. Later rounds get their
own `round-N` directories, and retries preserve the original round and attempt.

`--timeout` defaults to 180 seconds per CLI process; POSIX cleanup kills the
process group. `--token-budget` defaults to 60,000 reported input + output tokens
per invocation. It controls admission after an arm completes, not the tokens of
an active arm. Cached input and reasoning output remain subsets, counted once.

A failed native `error` or `turn.failed` message reporting a usage/rate limit
stops the run with exit **75**. Ordinary answers and tool output mentioning limits
are not limit signals. Other errors, missing usage and an exhausted admission
budget also stop new launches. Resume unfinished or limited work later:

```bash
python3 -B evals/run_outcome_evals.py --resume ~/agent-eval-runs/codex-skill-outcomes-RUN \
  --token-budget 250000
```

Resume preserves model, effort, timeout, cases and repetition count. Only the new invocation's
admission allowance may change. It rejects changed client versions, evaluation
code, fixture bytes, contract definitions or frozen candidates before launching.
Passing/failed terminal outcomes are not rerun. Missing, skipped, limited and
interrupted attempts can continue in fresh fixtures. Each retry gets a new
artifact directory; previous worktrees and transcripts stay at their original paths.
A run lock prevents simultaneous writers. A torn final checkpoint is retained
separately before recovery; corruption earlier in the history is rejected.

Grades and paired overhead use final attempts. Consumption and elapsed work
include **all** attempts, including failed ones. Unknown usage stays unknown
after resume; known consumption remains visible as `observed_tokens`. A launcher
interrupted before saving usage creates an unknown attempt, not a zero-cost one.
Dollar cost stays unknown. A passing baseline is valid; errors/skipped arms do
not form comparable pairs. Other failures exit nonzero, including enabled-arm
rubric failures. Pending design reviews remain explicitly reported.

## Isolation and retained evidence

Each run freezes selected skills under `candidates/` and records hashes, settings,
native events, stderr, answers, fixtures and grading evidence. Outputs default
to a private new `~/agent-eval-runs/codex-skill-outcomes-*` directory; explicit destinations
must be new and outside Git worktrees.

Each arm gets a temporary `CODEX_HOME` with only a link to existing authentication
when available. No credentials are retained in the evidence tree. Session-only
controls disable bundled skills, plugins, hooks, apps, memory, delegation,
browser/web search, standing instruction loading and user rules/configuration.
The disabled entry point is also omitted; helper files stay available. Shell
commands use workspace-write sandboxing without per-command prefix rules.
Inspect the retained blocked command records and per-arm counts before trusting
a comparison. The counts flag denial text in command results and require
transcript review to tell runner restrictions from ordinary program errors.
The read detector matches observed shell readers against actual skill files.
Naming an absent entry point is not evidence of contamination.

These controls isolate ordinary first-party Codex sessions, not the operating
system or managed policy. Use trusted candidates and inspect transcripts before
sharing. Rubrics do not establish every reasoning step or resistance to deliberate
gaming. One pair is not a statistical quality, latency or cost benchmark.

## Other checks

`run_system_reasoning.py OUTPUT` retains five read-only smoke scenarios using
the installed plugin and normal client configuration. It accepts `--model`,
`--effort`, `--timeout` and `--token-budget`; it stops on failed sessions and
requires human review of outcomes. It is not a source-snapshot comparison.

An optional `check_sibling_contracts.py /path/to/other-source` compares only the
common contracts, `current-docs` and the shared data-workflow reference. Codex-only
skills are deliberately absent from that inventory. No sibling checkout is
needed for installation or offline tests.

[Data workflow scenarios](data-workflow-scenarios.json) add manual confidentiality,
authority and proportionality checks. The paired rehearsal uses disposable SQLite
state; it does not establish production isolation or database compatibility.
