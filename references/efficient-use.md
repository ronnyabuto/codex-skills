# Using the skills efficiently with GPT-6.1 Sol medium

Keep the twelve skills discoverable. Give Codex the requested outcome,
constraints and acceptance check; load a procedure when it answers an actual
question. Do not turn routine edits into a checklist of skill reads.

| Task | Relevant procedure |
|---|---|
| Fresh implementation | `new-feature` once; preserve existing work and verify the base |
| Established local fix | Inspect the owner and callers, fix it, run the affected check |
| Unknown workaround or risky removal | `understand-before-changing` |
| Concrete ownership or duplication question | `code-structure` |
| Unclear recurring failure or architecture decision | `system-reasoning` |
| Uncertain version-specific integration | `current-docs` |
| Requested proof, test design or measured improvement | `evidence-driven-testing`; choose the relevant reference |
| Previous decision needed | `vault-memory`; search distinctive terms, then read matching lines |
| Requested audit | The audit matching the scope; `managed-audit` only for requested coordination |
| Requested readability cleanup | `no-ai-tells` for a diff; `no-ai-tells-audit` for repository-wide remediation |

## Operating preference

The compact preference is part of [standing guidance](agent-guidance.md), installed
only with the existing `--agent-guidance` opt-in. Keep one copy there rather than
adding it to each skill; preserve unrelated personal and project instructions.

Bound reads by relevance, not an arbitrary line count: the complete function or
contract may be necessary. Reuse context only while it is available and complete.
Keep full diagnostic logs when displaying excerpts, and preserve the command's
exit status; piping a failed check into `tail` can report success without
`pipefail`. Batch independent operations, not dependent edits or checks. Generated
files may need regeneration rather than a hand-edited fragment. Brief progress
updates remain useful for substantial work; final answers should lead with the
result. Documentation required to explain changed behavior is part of the task.

## Model and effort

For Sol 6.1 medium, use explicit session overrides without changing global defaults:

```bash
codex --model gpt-6.1-sol -c 'model_reasoning_effort="medium"'
```

Sol supports complex coding and professional work, with medium its default
reasoning effort. Keep concise requirements, dependency tracing, meaningful
failure cases and verification for consequential work. OpenAI's published
maintenance comparison found medium economical but less comprehensive than
higher-effort runs; that is evidence from one workload, not a universal ranking.
Do not silently increase effort or remove useful checks based on a different
model's strengths. See [Sol specifications](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[maintenance example](https://developers.openai.com/blog/maintaining-software-with-the-gpt-6-family)
and [session overrides](https://learn.chatgpt.com/docs/developer-settings).

## Context, installation and memory

Codex initially exposes skill names, descriptions and paths, then reads selected
instructions. A discovery-list budget does not cap the selected SKILL.md's
content. A Markdown reference is guidance, not an automatic invocation. Preserve
conditional reads and do not preload every reference. See
[skill loading](https://learn.chatgpt.com/docs/build-skills).

Source changes reach the installed plugin through the verified release inventory
and supported installer/client workflow; editing an installed cache is not an
upgrade. Keep this package independent of other clients' installations.

Keep the trusted user-level vault hooks and Python adapter. SessionStart emits a
recall pointer when this repository has memory. PreCompact and SessionEnd archive
locally without injecting archive bodies. Search only when the current task
depends on prior decisions; read matching line ranges, not whole sessions.
Repository instructions must remain useful to contributors without your personal
AGENTS.md. Do not remove useful project contracts merely to deduplicate your own
global guidance.

## Measure a proposed improvement

Choose one observed unnecessary read, repeated check or misleading instruction.
Use fresh sessions from the same source snapshot, with the same exact model,
effort, tools and acceptance criteria. The [paired runner](../evals/README.md)
accepts explicit effort; live runs consume model usage. Offline harness checks
establish harness behavior, not model quality or savings.

The paired runner disables user/project standing instructions. It compares a
selected skill, not the global operating preference. Evaluating that preference
requires a separate controlled comparison with the same source, tools, model and
effort, changing only the injected policy. Do not interpret the existing runner's
passing grades as evidence that a global policy preserves quality or saves tokens.

Compare correct outcomes and preserved scope first, then tool calls, input/cache
categories, output, elapsed time and any available actual cost. Codex input
includes cached input, and output includes reasoning tokens: do not add those
subsets again. Cumulative input across calls is not unique simultaneous context
or a final subscription charge. Compare complete tasks rather than file length,
keep passing baselines, and retain a change only when its benefit is measured
without weakening useful safeguards.
