# Review — November 5, 2026

I kept the data and migration guidance inside the testing skill and left the
actual commands, sanitizers and grants with each project. The new rehearsal
case catches an edge case that masking can hide.

I fixed forked-session recall without replacing the memory runtime or changing
custom hook filters. Claude and Codex still have separate adapters; sharing
Markdown does not make their permissions or hooks interchangeable.

The release inventory checks out. All 64 executed offline tests pass; two
optional media tests are skipped. Native hook delivery and model-performance
gains remain untested.

# Review — November 2, 2026

The existing Codex guidance was already fairly compact. I kept it and fixed the
identity split for repositories using a separate Git directory. Older notes
remain searchable without rewriting them.

I separated the eval requests from their output contracts, added a routine-task
control and recorded paired overhead. The sibling check covers shared contracts
without tying either installation to the other checkout.

The release inventory validates. Of 60 offline tests, 58 pass and two media tests
are skipped because FFmpeg is missing. These checks don’t establish a model
performance gain.
