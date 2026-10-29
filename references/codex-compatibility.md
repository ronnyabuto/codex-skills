# Codex compatibility — public release 2.0.0

This release is reviewed against Codex CLI 0.165.0, Python 3.14.4 and SQLite
3.46.1. Markdown skills use the portable Agent Skills format; supporting
references remain on demand. The evidence skill already had separate recorder
and headless references, so its entry point remains concise.

## Invocation and context

The official [skills guidance](https://learn.chatgpt.com/docs/build-skills)
documents natural-language matching, explicit `$skill-name` invocation and
`/skills`. Automatic discovery stays enabled for this collection. Optional
`agents/openai.yaml` policy can make a skill explicit-only with
`allow_implicit_invocation: false`; that is a user choice, not a prerequisite
for updating a skill.

Codex can disable a local skill through `[[skills.config]]` with its path and
`enabled = false`. The paired outcome runner uses session-only `-c` overrides,
not permanent edits. It also omits the disabled entry point and uses private
transient runtime homes to prevent personal standing instructions or direct
file browsing from silently teaching the baseline. Claude's `disable-model-invocation`, `context: fork`,
`${CLAUDE_SKILL_DIR}`, `Skill` tool and `/skill-doctor` are not assumed to be
Codex interfaces. See the [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
for current supported keys.

Use `codex doctor` for local setup/configuration diagnostics and `/skills` to
inspect discovery. Use supported `codex plugin` commands to manage installed
plugins. Editing source does not update a cached installation: this package's
installer backs up prior configuration and marketplace source, installs through
the CLI, and verifies every plugin resource. Restart the Codex session after an
upgrade. The installer does not bypass hook trust or relocate the chosen vault.

## Cooperating with existing workflows

Reuse project launch and verification recipes, including results that already
cover the claim. `evidence-driven-testing` adds reproducible probes, captures and
assertion evidence; it does not mandate another full test pass. A completed
`codex review` can supply relevant diff findings. `project-audit` has a broader
requested project-health scope, and `managed-audit` coordinates workers only
when the user asks for that workflow. None of these grants implementation or
publication authority merely by being invoked.

Codex's built-in memory and this package's explicit Markdown archive serve
different workflows. Vault hooks remain user-level lifecycle hooks with their
existing trust requirements. The helper indexes only the private `codex/`
namespace, and does not read Claude archives. Initialization retries SQLite
busy errors for up to five seconds; refresh transactions keep their own
five-second busy timeout. Persistent locks and corrupt files remain errors.

## Evaluation

The official [skill evaluation article](https://developers.openai.com/blog/eval-skills)
recommends observable outcomes and native `codex exec --json` events. This
release preserves the catalog and system-reasoning smoke cases, and adds
fresh enabled/disabled outcome comparisons. The selected model, candidate
hashes, artifacts, elapsed time and native token usage are retained. Cache and
reasoning token counts are subsets; dollar cost remains unknown.

The paired runner requires Python 3.11+ for TOML configuration parsing and
Codex CLI >= 0.165.0 for the tested execution controls. It preserves the selected
model but ignores other personal config for fixture isolation. It is intended
for ordinary first-party Codex authentication; custom providers/profile layers
need a separately reviewed setup. See [evaluation instructions](../evals/README.md)
and the official [developer commands](https://learn.chatgpt.com/docs/developer-commands)
for session controls, ephemeral execution and sandboxing.

## Public packaging

The Git repository is `ronnyabuto/codex-skills`; the plugin identity remains
`ronny-codex-skills@ronny-local`. All installed resources are contained within
the plugin. The installer reads a hash-verified release inventory and copies
only that snapshot, excluding Git metadata and unrelated source-tree files.
The public release excludes the inherited recorder and provides an independently
written replacement under MIT. Its foreground command is `record`, annotations
are sidecar files, and FFmpeg itself verifies media; it no longer requires
ffprobe or ASS. See the recorder reference for migration and platform limits.
