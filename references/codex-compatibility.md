# Codex compatibility

Reviewed 2026-11-19 against Codex CLI **0.170.0**, released November 18.
The paired runner requires that version for the reviewed configuration and
native JSONL schema. Structural/offline checks do not establish native hook
delivery, GUI capture or model compliance. See [validation](../VALIDATION.md).

## Skills and discovery

The package keeps `SKILL.md` instructions and resources inside the plugin.
Current Codex supports explicit `$skill-name` or `/skills` selection and
implicit matching by description. `agents/openai.yaml` remains optional;
`allow_implicit_invocation: false` is an explicit-only policy, not an upgrade
requirement. Automatic matching remains enabled here.

The initial skill list normally uses at most 2% of context, or 8,000 characters
when context is unknown. Codex shortens descriptions before omitting skills.
`skills.max_context_tokens` can configure that budget up to 10,000 tokens;
it does not cap the full instructions read for a selected skill. Put useful
triggers first and keep references conditional.

Local skills live in `.agents/skills` at repository, ancestor or user scope;
plugins remain the distribution route for this collection. `skills.config`
supports path or name selectors, with the last matching entry taking effect.
`skills.bundled.enabled=false` disables bundled skills. The paired runner uses
session-only controls; it does not change the user's normal discovery settings.

Source edits do not update an installed cache. Use the verified installer and
supported plugin commands, then start a new session. Use `codex doctor` for
local diagnostics. Claude-specific invocation fields and `${CLAUDE_SKILL_DIR}`
are not assumed to be Codex interfaces.

## Hooks and memory

The package retains authorized user-level `SessionStart`, `PreCompact` and
`SessionEnd` hooks, including fork recall. The merger preserves unrelated
handlers and custom filters. SQLite lock waits are bounded; persistent locks
and corrupt indexes remain reported, nonfatal hook errors.

Codex now documents plugin-bundled hooks through `hooks/hooks.json` or a manifest
entry, with `PLUGIN_ROOT`/`PLUGIN_DATA` and review after script changes. Moving
this package's hooks is optional. A migration must remove duplicate registration,
preserve the selected vault and verify native lifecycle/trust behavior first.

Local command/plugin hooks are not supported by cloud orchestration.
`transcript_path` may be null, and its file format is not a stable hook API.
The adapter does not scan unrelated sessions when a transcript is unavailable.

## Models and evaluations

GPT-6.2 Sol and Astra became available in Codex on November 17. Use current
account-supported models; preserve explicit user choices and historical benchmark
versions. A newer model alone does not establish skill value or token savings.

Exec 0.170.0 emits `turn.completed` usage and message-only `error`/`turn.failed`
events. The runners classify usage/rate limits only from failed native event
messages, never from ordinary answers or tool output. No app-server error-code
fields or Claude spending flags are assumed. Failed attempts count toward
consumption; absent usage remains unknown. See [evaluation controls](../evals/README.md).

## Official sources

- [Changelog](https://learn.chatgpt.com/docs/changelog)
- [Skills](https://learn.chatgpt.com/docs/build-skills)
- [Configuration](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Hooks and trust](https://learn.chatgpt.com/docs/hooks)
- [Models](https://learn.chatgpt.com/docs/model-selection)
- [Native exec event schema, 0.170.0](https://github.com/openai/codex/blob/rust-v0.170.0/codex-rs/exec/src/exec_events.rs)
