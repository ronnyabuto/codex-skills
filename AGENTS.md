# Repository layout

The repository is `codex-skills`; the stable installed plugin identity is
`ronny-codex-skills@ronny-local`. Keep plugin metadata and resources inside
`plugins/ronny-codex-skills/`. Do not introduce dependencies on a Claude checkout
or on files outside the installed plugin.

Memory belongs to `skills/vault-memory/scripts/`; the recorder belongs to
`skills/evidence-driven-testing/scripts/`. Keep tests synthetic. Store raw
model transcripts, captures, vaults and credentials outside the source tree.
Live model evaluations consume usage and are separate from offline checks.

After public source changes, run `python3 scripts/build_release.py`,
`python3 scripts/build_release.py --check`, `python3 scripts/validate.py` and
proportionate tests. The installer verifies and copies only the release
inventory. Do not edit the installed plugin cache.

The inherited recorder is excluded from this repository and its history.
Preserve the provenance notice; do not reintroduce that material by copying
it from old local releases or from the Claude package.
