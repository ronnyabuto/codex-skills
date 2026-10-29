import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import sqlite3

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "plugins/ronny-codex-skills/skills/vault-memory/scripts/memory.py"
spec = importlib.util.spec_from_file_location("memory", SCRIPT)
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="codex-memory-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "vault"
        self.root.mkdir()
        self.cwd = self.base / "project"
        self.cwd.mkdir()
        self.env = dict(os.environ, CODEX_MEMORY_VAULT=str(self.root), CODEX_MEMORY_CACHE=str(self.base / "cache"), CODEX_MEMORY_EXCLUDE="", XDG_CONFIG_HOME=str(self.base / "config"))

    def cli(self, *args, body=None, cwd=None, env=None, success=True):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--cwd", str(cwd or self.cwd), *args], input=body, capture_output=True, text=True, env=env or self.env)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def test_note_search_read_and_redaction(self):
        path = self.cli("note", "--title", "Refresh ownership", body="Refresh race stays in the caller. API_TOKEN=very-secret-value").stdout.strip()
        text = self.cli("read", path).stdout
        self.assertNotIn("very-secret-value", text)
        self.assertIn("[REDACTED]", text)
        hit = self.cli("search", "refresh race").stdout
        self.assertIn(path + ":", hit)
        self.assertLess(len(hit), 1500)

    def test_vault_required_and_project_exclusion(self):
        env = dict(self.env)
        env.pop("CODEX_MEMORY_VAULT")
        self.cli("note", "--title", "Decision", body="Reason", env=env, success=False)
        env = dict(self.env, CODEX_MEMORY_EXCLUDE="project")
        self.cli("note", "--title", "Decision", body="Reason", env=env, success=False)
        self.assertEqual(list(self.root.rglob("*.md")), [])

    def test_explicit_saved_vault_configuration(self):
        config = self.base / "config" / "ronny-codex-skills" / "memory.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"vault": str(self.root)}))
        env = dict(self.env)
        env.pop("CODEX_MEMORY_VAULT")
        path = self.cli("note", "--title", "Configured", body="Explicit location", env=env).stdout.strip()
        self.assertTrue((self.root / path).is_file())

    def test_escape_and_symlink_rejected(self):
        outside = self.base / "outside.md"
        outside.write_text("OUTSIDE FIXTURE")
        (self.root / "alias.md").symlink_to(outside)
        self.cli("read", "../outside.md", success=False)
        self.cli("read", "alias.md", success=False)
        self.cli("read", str(outside), success=False)
        self.assertNotIn("OUTSIDE FIXTURE", self.cli("search", "OUTSIDE", "--all-projects").stdout)
        directory = self.root / "codex"
        directory.symlink_to(self.base / "elsewhere", target_is_directory=True)
        self.cli("note", "--title", "Escape", body="Must stay in vault", success=False)

    def test_same_titles_concurrently_do_not_overwrite(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            paths = list(pool.map(lambda i: self.cli("note", "--title", "Same title", body=f"Distinct decision {i}").stdout.strip(), range(8)))
        self.assertEqual(len(set(paths)), 8)
        self.assertEqual(len(list(self.root.rglob("*.md"))), 8)
        for index, path in enumerate(paths):
            self.assertIn(f"Distinct decision {index}", (self.root / path).read_text())

    def test_repositories_separate_and_worktrees_share_identity(self):
        first = self.base / "first" / "app"
        second = self.base / "second" / "app"
        for path in (first, second):
            path.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(path)], check=True)
        self.assertNotEqual(memory.project_id(first), memory.project_id(second))
        subprocess.run(["git", "-C", str(first), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "Fixture"], check=True)
        worktree = self.base / "worktree"
        subprocess.run(["git", "-C", str(first), "worktree", "add", "-q", "-b", "fixture-branch", str(worktree)], check=True)
        self.assertEqual(memory.project_id(first), memory.project_id(worktree))
        path = self.cli("note", "--title", "Owner", body="Repository one", cwd=first).stdout.strip()
        self.assertIn(path, self.cli("search", "Repository", cwd=worktree).stdout)
        self.assertEqual(self.cli("search", "Repository", cwd=second).stdout, "")

    def test_content_hash_freshness_and_deleted_notes(self):
        path = self.cli("note", "--title", "Index", body="alpha-key").stdout.strip()
        self.assertIn(path, self.cli("search", "alpha").stdout)
        file = self.root / path
        stat = file.stat()
        file.write_text(file.read_text().replace("alpha-key", "omega-key"))
        os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertIn(path, self.cli("search", "omega").stdout)
        self.assertEqual(self.cli("search", "alpha").stdout, "")
        file.unlink()
        self.assertEqual(self.cli("search", "omega").stdout, "")

    def test_superseded_notes_hidden(self):
        old = self.cli("note", "--title", "Old", body="Old race policy").stdout.strip()
        new = self.cli("note", "--title", "New", body="New race policy").stdout.strip()
        self.cli("supersede", old, "--by", new)
        self.assertNotIn(old, self.cli("search", "race").stdout)
        self.assertIn(new, self.cli("search", "race").stdout)
        self.assertIn(old, self.cli("search", "race", "--include-superseded").stdout)

    def test_output_bounds_and_search_punctuation(self):
        path = self.cli("note", "--title", "Large", body="\n".join("bounded text " * 100 for _ in range(80))).stdout.strip()
        output = self.cli("read", path, "--lines", "1:100", "--max-chars", "200").stdout
        self.assertLess(len(output), 260)
        self.cli("read", path, "--max-chars", "999999", success=False)
        self.cli("search", '" OR *'); self.cli("search", "!!!", success=False)

    def test_codex_transcript_import_omits_reasoning_outputs_arguments(self):
        rows = [
            {"type": "event_msg", "payload": {"type": "user_message", "message": "User decision"}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "User decision"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Keep retry ownership"}]}},
            {"type": "response_item", "payload": {"type": "function_call", "name": "exec_command", "arguments": "ARGUMENT_SENTINEL"}},
            {"type": "response_item", "payload": {"type": "function_call_output", "output": "OUTPUT_SENTINEL"}},
            {"type": "response_item", "payload": {"type": "reasoning", "text": "REASONING_SENTINEL"}},
            {"type": "compacted", "payload": {"message": "A compacted decision"}},
        ]
        source = self.base / "session.jsonl"
        source.write_text("\n".join(json.dumps(row) for row in rows))
        path = self.cli("import-session", str(source)).stdout.strip()
        text = (self.root / path).read_text()
        self.assertEqual(text.count("User decision"), 1)
        self.assertIn("exec_command", text)
        self.assertIn("A compacted decision", text)
        for sentinel in ("ARGUMENT_SENTINEL", "OUTPUT_SENTINEL", "REASONING_SENTINEL"):
            self.assertNotIn(sentinel, text)
        source.write_text(json.dumps({"type": "unknown"}))
        self.cli("import-session", str(source), success=False)
        source.write_text("not json")
        self.cli("import-session", str(source), success=False)

    def test_redaction_preserves_metrics_context_and_secret_titles(self):
        for prefix in ("sk_live_", "rk_live_"):
            self.assertEqual(memory.redact(prefix + "A" * 24), "[REDACTED]")
        self.assertEqual(memory.redact("PASSWORD=abcdefghijk retain explanation"), "PASSWORD=[REDACTED] retain explanation")
        self.assertEqual(memory.redact("context_tokens: 182340 retain explanation"), "context_tokens: 182340 retain explanation")
        path = self.cli("note", "--title", "sk_live_" + "A" * 24, body="Decision").stdout.strip()
        self.assertNotIn("a" * 24, path)
        self.assertEqual(memory.redact(memory.redact("API_TOKEN=synthetic-secret context")), "API_TOKEN=[REDACTED] context")

    def test_search_cannot_be_saturated_by_one_archive(self):
        self.cli("note", "--title", "Archive", body="\n".join("oauth race" for _ in range(100)))
        for i in range(8):
            self.cli("note", "--title", f"Note {i}", body="filler " * 80 + "oauth race")
        output = self.cli("search", "--all-projects", "oauth race").stdout
        paths = [line.split(":")[0] for line in output.splitlines() if line and not line.startswith(" ")]
        self.assertEqual(len(paths), 8)
        self.assertGreaterEqual(len(set(paths)), 7)

    def test_index_and_read_exclude_claude_and_other_vault_content(self):
        for relative in ("claude/private.md", "personal.md"):
            file = self.root / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("cross-client-private-marker")
            self.cli("read", relative, success=False)
        self.assertEqual(self.cli("search", "cross client private", "--all-projects").stdout, "")
        (self.root / "codex").mkdir()
        (self.root / "codex/alias.md").symlink_to(self.root / "claude/private.md")
        self.cli("read", "codex/alias.md", success=False)
        self.assertEqual(self.cli("search", "cross client private", "--all-projects").stdout, "")

    def test_concurrent_indexing_and_failed_refresh_rollback(self):
        for i in range(30):
            self.cli("note", "--title", f"Note {i}", body="Decision")
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: self.cli("recent"), range(8)))
        with patch.dict(os.environ, self.env):
            db = memory.open_index(self.root)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM files").fetchone()[0], 30)
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(db.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
            db.close()
            note = next(self.root.rglob("*.md"))
            note.write_text(note.read_text() + "\nChanged")
            with patch.object(memory, "metadata", side_effect=ValueError("synthetic refresh failure")):
                with self.assertRaisesRegex(ValueError, "refresh failure"):
                    memory.open_index(self.root)
            db = sqlite3.connect(self.base / "cache" / (memory.digest(str(self.root)) + ".sqlite"))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM files").fetchone()[0], 30)
            db.close()
            memory.open_index(self.root).close()

    def locked_index(self):
        cache = self.base / "cache"
        cache.mkdir()
        db = sqlite3.connect(cache / (memory.digest(str(self.root)) + ".sqlite"))
        self.addCleanup(db.close)
        db.execute("CREATE TABLE blocker (id INTEGER)")
        db.commit()
        db.execute("BEGIN")
        db.execute("SELECT * FROM blocker").fetchall()
        return db

    def test_wal_initialization_recovers_after_reader_releases_lock(self):
        self.cli("note", "--title", "Recoverable", body="Recovery decision")
        db = self.locked_index()
        worker = subprocess.Popen([sys.executable, "-B", str(SCRIPT), "--cwd", str(self.cwd), "recent"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
        try:
            time.sleep(0.3)
            self.assertIsNone(worker.poll(), "indexing should wait for the reader")
            db.rollback()
            out, err = worker.communicate(timeout=10)
            self.assertEqual(worker.returncode, 0, err)
            self.assertIn("Recoverable", out)
        finally:
            if worker.poll() is None:
                worker.kill()
            worker.communicate()

    def test_persistent_lock_fails_within_budget_then_recovers(self):
        self.cli("note", "--title", "Recoverable", body="Recovery decision")
        db = self.locked_index()
        started = time.monotonic()
        self.assertIn("database is locked", self.cli("recent", success=False).stderr)
        elapsed = time.monotonic() - started
        self.assertGreaterEqual(elapsed, 4.5)
        self.assertLess(elapsed, 10)
        db.rollback()
        self.assertIn("Recoverable", self.cli("recent").stdout)
        with patch.dict(os.environ, self.env):
            index = memory.open_index(self.root)
            try:
                self.assertEqual(index.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
            finally:
                index.close()

    def test_corrupt_index_is_not_replaced_and_hook_failure_is_nonfatal(self):
        self.cli("recent")
        cache = next((self.base / "cache").glob("*.sqlite"))
        cache.write_bytes(b"not a SQLite database")
        started = time.monotonic()
        self.assertIn("not a database", self.cli("recent", success=False).stderr)
        self.assertLess(time.monotonic() - started, 4)
        hook = subprocess.run([sys.executable, "-B", str(SCRIPT.with_name("hooks.py"))],
                              input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.cwd)}),
                              capture_output=True, text=True, env=self.env, timeout=10)
        self.assertEqual(hook.returncode, 0)
        self.assertIn("codex-vault-memory:", hook.stderr)
        self.assertEqual(cache.read_bytes(), b"not a SQLite database")

    def test_transcript_filters_notifications_and_bootstrap_context(self):
        source = self.base / "noise.jsonl"
        rows = [
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "# AGENTS.md instructions for /tmp/project\n<INSTRUCTIONS>bootstrap-only-marker</INSTRUCTIONS><environment_context>injected environment</environment_context>"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Actual request<task-notification>internal noise</task-notification>"}]}},
        ]
        source.write_text("\n".join(json.dumps(row) for row in rows))
        body = memory.transcript_body(source)
        self.assertIn("Actual request", body)
        for marker in ("bootstrap-only-marker", "injected environment", "internal noise"):
            self.assertNotIn(marker, body)


if __name__ == "__main__":
    unittest.main()
