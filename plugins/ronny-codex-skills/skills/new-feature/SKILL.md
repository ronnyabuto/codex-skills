---
name: new-feature
description: Start a fresh implementation task from fetched origin/main, or verify an assigned workspace. Use a worktree for requested isolation or concurrent writers. Skip reviews, questions and continuation of an existing task.
---

# Start a task from a fresh base

Before the first edit of a new task:

1. Inspect instructions, status, branch and existing worktrees. Preserve all
   existing work and the assigned workspace. Continuing the same task does not
   require restarting from main or fetching again.
2. Successfully fetch origin and record the refreshed `origin/main` commit,
   including on a harness-assigned branch or worktree. Assignment does not
   prove remote freshness. If the refspec excludes main, explicitly fetch
   `main:refs/remotes/origin/main`. Preserve an explicit release, PR or local
   base instead of substituting main.
3. For an assigned workspace, keep it and verify HEAD matches or descends from
   that base. Resolve a stale base without discarding work; report a gap that
   cannot be resolved within the task. If its metadata is read-only, fetch the
   same remote into a disposable scratch Git directory and compare the fetched
   commit with HEAD. A cached tracking ref alone is not fresh verification.
4. Otherwise run `git switch --no-track -c <unique-branch> origin/main` and
   verify HEAD equals the recorded base. Do not pull into or reset local main.
   Without `--no-track`, the branch can inherit main as its upstream.

If a fresh fetch is unavailable, report the limitation and obtain direction
before using a stale or different base. An overlapping PR is coordination
context; ask only when incompatible ownership or scope remains unresolved.

Use a worktree for requested isolation or concurrent writers. Choose a new
external or gitignored path; never force reuse of another session's workspace.
Restore required ignored configuration before checks, following
[worktree environments](references/environment.md). Worktrees share Git objects,
refs, ports, caches and external services. Verify the process being tested.

## Cleanup

Unless broader cleanup is requested, remove only branches and worktrees created
for this task. Verify integration into the intended base, no later unmerged
commits and clean status. Leave and remove the worktree, then prefer
`git branch -d`. Use `-D` after squash/rebase only when integration is verified.
Delete a remote branch only after its PR has merged. Report unfinished work's
location and preserve other sessions' branches.
