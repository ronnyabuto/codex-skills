# Validation — 2.2.0

Reviewed 2026-11-19 with Codex CLI 0.170.0. The final offline suite covers
81 tests, including privacy, concurrency, recovery, installer boundaries and
real Git fetch grading. Two optional FFmpeg checks require an external binary;
their absence does not establish media or GUI correctness.

```bash
python3 scripts/build_release.py --check
python3 scripts/validate.py
python3 -B -m unittest discover -s tests -v
```

## Live evaluations

The [aggregate results](evals/results/2026-11-19.json) retain requested model and
effort, candidate hashes, per-arm grades and reported usage. Raw native events,
fixtures, original grades and regraded evidence stay outside the repository.
No private transcripts, credentials or real vault notes are published.

Eight pairs requested GPT-6.2 Sol at medium effort. Five cases passed in both
arms. Assigned-workspace freshness, audit limitation disclosure and bounded
retrieval failed the original full rubrics. Both audit arms found the defect;
the enabled arm also reproduced it. Memory answers recovered the correct
decision but did not use bounded source reads.

A fresh pair tested the clarified assigned-workspace rule: the enabled arm
fetched into a scratch repository and compared the fresh commit to HEAD; the
baseline omitted the fetch. Its original grade was corrected after the trace
showed a valid variable-based remote. Equivalent human-readable dates are now
accepted, while wrong dates remain rejected. A deterministic hash containing
`120` protects against confusing a repository ID with the superseded value.
Original grades are retained rather than overwritten.

Both design answers covered load arithmetic, component choice, bounded calls,
acknowledgement loss, rollout/rollback and the 10x bottleneck on primary-agent
review. The added reference showed no benefit and used 19,841 more reported
tokens in its arm, so it was removed. The existing system-reasoning skill and
arithmetic evaluation remain. No human approval or production email test is claimed.

The first outer-sandbox run was excluded after file/tool failures; known usage
and its interrupted attempt remain disclosed. The valid full run resumed after
its admission threshold without repeating completed arms. These small comparisons
do not establish statistical quality, speed or billing gains. Known audit and
retrieval limitations remain explicit, not reclassified as passing outcomes.

## Other verification

Native event definitions and isolation settings were checked against official
0.170.0 source. Resume tests cover all-attempt accounting, unknown usage, torn
checkpoints, locks and changed-input rejection. Injected lost-attempt accounting,
impossible peaks and stale sibling inventory were detected by regression tests.
Installer tests preserve existing configuration and reject reads of other clients.

Historical evidence: four 2026-10-29 pairs used CLI 0.165.0 and GPT-6.1 Sol;
all enabled arms and three baselines passed. The difference was bounded recall,
not improved factual recall. The release-2.0.0 recorder was verified with FFmpeg
7.0.2 on synthetic media; that does not establish current GUI capture.
See [provenance](plugins/ronny-codex-skills/PROVENANCE.md).
