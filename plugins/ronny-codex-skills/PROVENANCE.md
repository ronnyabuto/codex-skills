# Provenance and licensing

The code and instructions distributed in this repository are licensed under
the bundled [MIT license](LICENSE). External tools such as FFmpeg and Git
are separate dependencies; their binaries and source are not bundled here.

## Earlier local package

This collection grew from locally authored Codex workflows, informed by the
workflow ideas in [ronnyabuto/agent-skills](https://github.com/ronnyabuto/agent-skills)
and the upstream [michaelshimeles/rstack](https://github.com/michaelshimeles/rstack)
collection. The Codex entry points, Python memory helper, lifecycle adapter,
installers and evaluation harness were written for the Codex package. This
attribution acknowledges the workflow lineage without granting a license to
material in those external repositories.

The local releases through 1.4.0 included an inherited screen recorder. That
file had SHA-256 `d246b499991d495bf2f972f852d2dae0851b5bff2b5a64347f610242808ae8eb`.
It is excluded from this public repository, including its initial Git history.
The package validator rejects that retained file if it is reintroduced.
Historical validation notes describe the earlier local releases, not a license
grant or a claim that their recorder is included in this release.

## Public release 2.0.0

The new `evidence-driven-testing/scripts/evidence.py` was written independently
for this release using Python's standard library and FFmpeg's documented CLI.
It owns a foreground capture process, accepts timestamped sidecar annotations,
uses a stop-request file instead of external PID signaling, and verifies media
by decoding it. Its command interface and report format differ from the old
recorder. No inherited recorder implementation or FFmpeg binary is distributed.

The repository contains synthetic fixtures and aggregate historical validation
results. Private vault notes, authentication data, raw model-session transcripts,
installation backups and local capture artifacts are not release contents.
The installer copies only files verified by `release-files.json`.

## Primary implementation references

- [Codex skills](https://learn.chatgpt.com/docs/build-skills)
- [Codex plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Codex lifecycle hooks](https://learn.chatgpt.com/docs/hooks)
- [Codex developer commands](https://learn.chatgpt.com/docs/developer-commands)
- [Skill evaluation](https://developers.openai.com/blog/eval-skills)
- [Agent Skills format](https://agentskills.io/specification)
- [FFmpeg input devices](https://ffmpeg.org/ffmpeg-devices.html)
- [FFmpeg CLI](https://ffmpeg.org/ffmpeg.html)
- [Python subprocess lifecycle](https://docs.python.org/3/library/subprocess.html)
