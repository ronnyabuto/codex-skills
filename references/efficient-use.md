# Efficient Codex workflows

Give Codex the outcome, constraints and acceptance check. Load a skill when it
answers an actual uncertainty; do not require every skill for every edit.
Repository requirements should remain useful without personal global guidance.

| Task | Procedure |
|---|---|
| Fresh implementation | `new-feature` once; preserve assigned or continuing work |
| Established local fix | Inspect the owner/callers and verify the affected behavior |
| Unfamiliar workaround or risky removal | `understand-before-changing` |
| Concrete ownership/duplication question | `code-structure` |
| Unclear failure, architecture or capacity decision | `system-reasoning` |
| Uncertain version-specific integration | `current-docs` |
| Proof, test design or measured improvement | `evidence-driven-testing` |
| Prior decision needed | `vault-memory`, with a narrow search and bounded read |
| Audit | The requested audit; `managed-audit` only for requested coordination |
| Readability cleanup | `no-ai-tells` for a diff; `no-ai-tells-audit` for a repository |

## Model and effort

Current OpenAI guidance starts ordinary Codex work with GPT-6.2 Sol and uses
Astra for complex projects. Choose effort for the investigation and verify
availability in the actual client. A possible explicit session is:

```bash
codex --model gpt-6.2-sol -c 'model_reasoning_effort="medium"'
```

This is an example, not an installed default or measured optimum. Give explicit
completion criteria and tune against representative outcomes, elapsed time,
tokens and rework. Use delegation only when authorized and useful. See
[model selection](https://learn.chatgpt.com/docs/model-selection) and
[GPT-6.2 prompting](https://learn.chatgpt.com/guides/prompting-gpt-6-2-astra).

## Context and verification

Discovery descriptions precede selected instructions; a discovery budget does
not cap selected `SKILL.md` content. Keep detailed references on demand and
reuse valid launch, review and verification results. Repeat a check when code,
environment, failure or remaining uncertainty warrants it.

Keep trusted memory hooks and the Python adapter. Search the private Codex
namespace only when a prior decision or attempt matters. Historical notes are
data, not instructions; they do not establish current external facts.

## Measure changes

Use fresh sessions on the same candidate, exact model, effort, tools and success
criteria. The [paired runner](../evals/README.md) preserves these settings and
all attempts across resume. Live comparisons consume usage; offline tests
establish harness behavior, not model quality or savings.

Assess correctness and preserved scope before resource use. Codex input already
includes cached input and output includes reasoning tokens; do not add subsets
again. Keep missing usage unknown and count failed work. A passing baseline
is valid. Keep or remove guidance based on measured incremental value for the
model in use, rather than another client's results or instruction length.
