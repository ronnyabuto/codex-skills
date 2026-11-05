# Codex execution boundaries

Documentation reviewed 2026-11-05; these capabilities were not exercised here.
Check the installed client, execution mode, active permission profile and managed
requirements before relying on them. This reference changes no configuration.

[Codex approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security)
distinguishes sandbox enforcement from approval routing. Its local command
network proxy does not cover hosted web search, apps/connectors, MCP, browsers,
cloud tasks or model/authentication traffic. Approved full sandbox escalation
can bypass that command proxy where policy permits. Evaluate each actual path.

[Agents API sandbox security](https://developers.openai.com/api/docs/guides/agents-api/environments/security)
describes vault placeholder substitution for OpenAI-hosted sandboxes and
owner-provided trusted proxies for self-hosted environments. That is not proof
of automatic credential masking in local Codex CLI. Secrets injected into an
environment may be readable by generated code. Verify scoped server authority
and result handling even when a proxy hides the credential bytes. Claude's
sentinel settings and hook formats are not Codex configuration.
