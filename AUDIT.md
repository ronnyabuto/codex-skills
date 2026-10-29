# Codex skills audit — 2026-10-13

Audited local plugin 1.2.1 with Codex CLI 0.162.1, Python 3.14.4 and SQLite 3.46.1.
Baseline: 24 tests pass, release inventory and installed resources match.
Release 1.2.2 applies the verified corrections below. All payloads and fixtures
used for reproductions are synthetic; no private transcript excerpts are recorded.

| Concern | Evidence | Correction |
|---|---|---|
| Runtime compatibility | Python FTS5 works here; installer did not probe it. Node version floor does not apply. | Probe FTS5, materialization and window functions before installation writes. |
| Locking | Existing timeout is 30 seconds, unlike Claude's zero timeout. Journal mode is DELETE and indexing starts writes after earlier reads. | WAL, bounded five-second wait, BEGIN IMMEDIATE before schema/state reads; rollback and eight-way concurrency tested. |
| Search diversity | Long synthetic archive consumes all eight results; no per-file cap. No repeated-title/heading weighting exists. | Materialized FTS matches and ROW_NUMBER per file: eight results from seven files. |
| Redaction | Bare sk_live/rk_live keys survive; greedy assignments delete numeric metrics and the remaining line. Short passwords already redact. | Stripe/Google key coverage, bounded assignment values, preserve numeric metrics and trailing context; idempotence tested. |
| Filename privacy | Unsanitized titles feed note slugs even when saved content is redacted. | Redact titles before constructing filenames. |
| Transcript noise | Task notifications and injected AGENTS/bootstrap messages are archived as user text. | Filter known wrappers and bootstrap messages before archiving. |
| Cross-client boundaries | open_index scans every Markdown file in a vault; explicit read permits non-Codex content. | Confine resolution and indexing to codex/; reject namespace-escaping symlinks. |
| Storage | Existing private vault and cache live outside source trees, with 0700 directories and 0600 config/index files. | Preserve those locations and permissions; scrub existing Codex archives and rebuild the local cache after installation. |
| Hook payloads | Non-string cwd/transcript_path causes uncaught TypeError. | Explicit field validation reports nonblocking errors. Existing event definitions and native trust are preserved. |
| Standing rules | Global AGENTS.md covers diagnosis/memory/delegation but omits several ongoing coding invariants. | Update only the package's managed block, preserving other user instructions. |
| Worktree environments | Fresh Git worktrees lack ignored local configuration. | Codex-specific setup/approved-copy guidance; no assumption of Claude .worktreeinclude support. |
| Evals | Fresh code fixtures still inherit the user's real memory environment; timeouts abort summary creation and empty/malformed streams are not reliable results. | Independent synthetic vault/cache per case, error summaries, reject reused output directories. |
| Browser evidence | Existing headless reference already isolates Playwright correctly; desktop recorder requirements are explicit. | Retain this behavior and original recorder provenance. |
| Source/cache ownership | Installed plugin is a cached copy; source changes alone can leave loaded skills stale. | Bump both manifests and reinstall through the supported Codex CLI, then compare every resource. |

All 34 offline tests pass, including eight-way indexing, rollback, privacy scoping,
redaction, search diversity, transcript filtering, hook payloads, eval isolation
and installer preservation. Structural validation passes for all twelve skills.
No paid model evaluations or desktop recordings were performed in this audit.
Standing instructions guide behavior; they are not a hard enforcement layer.

## Primary references

- [Global and project AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Skill discovery and progressive disclosure](https://learn.chatgpt.com/docs/build-skills)
- [Native hooks and trust review](https://learn.chatgpt.com/docs/hooks)
- [Plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Python SQLite transactions](https://docs.python.org/3/library/sqlite3.html)
- [SQLite isolation and immediate transactions](https://sqlite.org/isolation.html)
- [SQLite BM25](https://sqlite.org/fts5.html#the_bm25_function)
