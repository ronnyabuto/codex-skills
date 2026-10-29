# Recurring Codex work

Measure productive steps, unchanged polls, retries, tokens, elapsed time, and
completed outcomes before changing the architecture. Prefer events or background
watchers where supported. Otherwise poll in code with suitable backoff. Compare
identifiers, versions, hashes, and timestamps before invoking a model; an unchanged
queue needs no classifier. A check inside a model prompt still pays for that prompt.

## Admit and execute bounded work

Give each item a stable identity and content version. Claim it atomically before
launching a worker; record its job/thread ID and outcome. Handle expired claims
so crashes neither lose items nor start duplicate workers. Recheck freshness
before acting on an earlier classification. Isolate concurrent writers in
worktrees; worktrees do not isolate external services, databases, or ports.

Use desktop scheduled tasks when the supported client provides them and the work
needs local projects. The machine and app must remain available. For CLI workers,
use an external scheduler or event source plus `codex exec`; the CLI has no
scheduled-task management interface. Verify capabilities in the actual client.
Do not translate Claude `/loop`, `/goal`, Stop-hook fields, or spending flags into
assumed Codex equivalents.

Define the permitted deliverable, observable acceptance criteria, and terminal
outcomes: completed, blocked, failed, or budget exhausted. Code should check exact
conditions such as exit codes, artifacts, and persisted state. A successful CLI
turn or the worker's assertion alone does not establish correctness. If a harness
provides goal tools, follow their actual semantics; a prompt to stop at a limit
is not a hard execution limit.

Enforce elapsed time, attempt counts, and admission budgets in the launcher.
Use the narrowest sandbox that supports the task. Retry transient failures
within the allowance; retry unsuccessful tasks only with a recorded reason,
such as changed evidence or a corrected approach. Preserve partial output and
state for review after exhaustion. A subprocess timeout may not terminate every
descendant; account for child processes when designing a hard runtime limit.

## Observe usage honestly

On the locally verified Codex CLI 0.163.0, `codex exec --json` emits
`turn.completed` usage and error/failed-turn events. Retain events, thread IDs,
exit status, elapsed time, relevant commands, and outcomes. Missing final answers
or incomplete/failed streams are errors even if some useful output appeared.
Use `--ephemeral` for disposable evaluations, with separate memory vault/cache
paths when lifecycle hooks are installed.

Keep input, cached-input, output, and reasoning-output counts distinguishable.
Cached input is a subset of input; reasoning output is a subset of output, so
do not add them again. This installed CLI has no `--max-budget-usd` or
`--max-turns` flag. A budget checked after a case finishes prevents subsequent
launches but cannot cap that case; state this limitation explicitly.

Include failed work in usage totals and cost per completed task. Missing usage
stays unknown. Convert tokens to dollars only with verified model, cache,
provider, and pricing information; subscription usage is not incremental billed
spend. A smaller or cheaper model may cost more per successful outcome.

## Add semantic routing only when justified

Compare code, native client features, and a separate classifier against measured
workload, latency, operational effort, external data handling, missed work, and
correction costs. A returned probability is neither demonstrated accuracy on
this workload nor permission to act. Keep permissions independently enforced.

If justified, start in shadow mode on representative labeled items, including
ambiguous/adversarial cases. Measure incorrect admissions and missed eligible
work on held-out examples. Pin model/question versions; route uncertainty and
errors to a recoverable review path. Retain a bypass to the earlier workflow
without losing pending items. Re-evaluate when workload, criteria, or model
changes justify it; do not add a provider merely because its tokens are cheap.

## Sources

Checked 2026-10-16; recheck flags and availability for the installed client:

- [Non-interactive runs and usage](https://learn.chatgpt.com/docs/non-interactive-mode)
- [CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
- [Scheduled tasks and local projects](https://learn.chatgpt.com/docs/automations?surface=app)
- [Outcome-based skill evals](https://developers.openai.com/blog/eval-skills)
