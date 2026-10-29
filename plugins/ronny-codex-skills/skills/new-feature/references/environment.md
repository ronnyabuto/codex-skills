# Worktree environment

Fresh Git worktrees contain committed files, not untracked or gitignored `.env`
files or uncommitted changes from another checkout. Follow the repository's setup
command or restore an explicit list of approved local configuration before tests.
Preserve permissions and keep copies gitignored. Avoid blanket `.env*` copying or
shared symlinks that let tasks change each other's configuration.

Codex does not gain Claude's `.worktreeinclude` behavior from a skill. Use the
actual client's documented environment setup or explicit approved copies.
