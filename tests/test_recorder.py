"""Verify the original recorder's lifecycle, evidence labels and failure boundaries."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/ronny-codex-skills/skills/evidence-driven-testing/scripts/evidence.py"
spec = importlib.util.spec_from_file_location("evidence_recorder", SCRIPT)
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)
FFMPEG = os.environ.get("EVIDENCE_FFMPEG") or shutil.which("ffmpeg")


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-recorder-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def cli(self, *args, ffmpeg=None):
        command = [sys.executable, "-B", str(SCRIPT)]
        if ffmpeg:
            command += ["--ffmpeg", str(ffmpeg)]
        return subprocess.run(command + list(args), capture_output=True, text=True, timeout=30)

    def session(self, state="recording"):
        session = self.root / "session"
        session.mkdir()
        (session / "events").mkdir()
        (session / "manifest.json").write_text(json.dumps(dict(
            format="codex-evidence-v1", state=state, started_monotonic=time.monotonic())))
        return session

    def test_missing_toolchain_is_reported_without_creating_a_session(self):
        result = self.cli("doctor", ffmpeg=self.root / "missing-ffmpeg")
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["capture_ready"])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_display_selection_has_explicit_requirements(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "platform", "linux"):
            with self.assertRaisesRegex(ValueError, "no desktop source"):
                recorder.source_options("auto", None, "640x360", 15)
            source, options = recorder.source_options("x11", ":99", "640x360", 15)
            self.assertEqual(source, "x11")
            self.assertIn(":99", options)
        with self.assertRaisesRegex(ValueError, "explicit screen input"):
            recorder.source_options("avfoundation", None, "640x360", 15)

    def test_assertions_require_a_result_and_stop_prevents_late_annotations(self):
        session = self.session()
        result = self.cli("annotate", str(session), "--kind", "assertion", "--message", "Observed outcome")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(list((session / "events").iterdir()), [])
        result = self.cli("annotate", str(session), "--kind", "assertion", "--message", "Observed outcome", "--result", "untested")
        self.assertEqual(result.returncode, 0, result.stderr)
        event = json.loads(result.stdout)
        self.assertEqual(event["result"], "untested")
        self.assertGreaterEqual(event["elapsed_seconds"], 0)
        self.assertTrue(json.loads(self.cli("stop", str(session)).stdout)["stop_requested"])
        self.assertNotEqual(self.cli("annotate", str(session), "--kind", "test", "--message", "Too late").returncode, 0)
        self.assertEqual(len(list((session / "events").iterdir())), 1)

    def test_stop_is_idempotent_for_a_completed_session(self):
        session = self.session("complete")
        before = (session / "manifest.json").read_bytes()
        result = self.cli("stop", str(session))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)["stop_requested"])
        self.assertFalse((session / "STOP").exists())
        self.assertEqual((session / "manifest.json").read_bytes(), before)

    def test_capture_failure_is_retained_and_never_marked_verified(self):
        binary = self.root / "ffmpeg"
        binary.write_text('''#!/usr/bin/env python3
import sys
if "-encoders" in sys.argv:
    print("libx264")
elif "-filters" in sys.argv:
    print("testsrc2")
else:
    sys.exit(7)
''')
        binary.chmod(0o755)
        session = self.root / "failure"
        result = self.cli("record", "--source", "test", "--output", str(session),
                          "--title", "Failed toolchain", "--max-seconds", "1", ffmpeg=binary)
        self.assertNotEqual(result.returncode, 0)
        manifest = json.loads((session / "manifest.json").read_text())
        self.assertEqual(manifest["state"], "failed")
        self.assertFalse(manifest["media_verified"])
        self.assertIn("exited 7", manifest["error"])
        before = (session / "manifest.json").read_bytes()
        retry = self.cli("record", "--source", "test", "--output", str(session),
                         "--title", "Do not overwrite", ffmpeg=binary)
        self.assertNotEqual(retry.returncode, 0)
        self.assertEqual((session / "manifest.json").read_bytes(), before)

    @unittest.skipUnless(FFMPEG, "FFmpeg is optional; set EVIDENCE_FFMPEG for the real media checks")
    def test_real_capture_concurrent_annotations_stop_and_media_decode(self):
        session = self.root / "synthetic"
        worker = subprocess.Popen([sys.executable, "-B", str(SCRIPT), "--ffmpeg", FFMPEG,
                                   "record", "--source", "test", "--size", "640x360",
                                   "--output", str(session), "--title", "Synthetic toolchain check",
                                   "--max-seconds", "8"], stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            first = worker.stdout.readline()
            self.assertTrue(first, "recorder exited before the first frame")
            self.assertTrue(json.loads(first)["capture_started"])
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda i: self.cli(
                    "annotate", str(session), "--kind", "assertion", "--message", f"Synthetic phase {i}",
                    "--result", "passed"), range(8)))
            self.assertTrue(all(result.returncode == 0 for result in results))
            self.assertTrue(json.loads(self.cli("stop", str(session)).stdout)["stop_requested"])
            _, stderr = worker.communicate(timeout=30)
            self.assertEqual(worker.returncode, 0, stderr)
        finally:
            if worker.poll() is None:
                worker.kill()
            worker.communicate()
        data = json.loads((session / "manifest.json").read_text())
        self.assertEqual(data["state"], "complete")
        self.assertTrue(data["synthetic"])
        self.assertTrue(data["media_verified"])
        self.assertGreater(data["decoded_frames"], 0)
        self.assertEqual(len(data["events"]), 8)
        self.assertGreater((session / "evidence.mp4").stat().st_size, 1000)
        self.assertIn("SYNTHETIC TOOLCHAIN CHECK", (session / "report.md").read_text())
        self.assertFalse(json.loads(self.cli("stop", str(session)).stdout)["stop_requested"])

    @unittest.skipUnless(FFMPEG, "FFmpeg is optional; set EVIDENCE_FFMPEG for the real media checks")
    def test_duration_bound_finalizes_and_corrupt_media_is_rejected(self):
        session = self.root / "bounded"
        result = self.cli("record", "--source", "test", "--size", "640x360", "--output", str(session),
                          "--title", "Bounded synthetic check", "--max-seconds", "0.6", ffmpeg=FFMPEG)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((session / "manifest.json").read_text())
        self.assertTrue(data["media_verified"])
        corrupt = self.root / "corrupt"
        corrupt.mkdir()
        (corrupt / "capture.mkv").write_bytes(b"not a video")
        with self.assertRaisesRegex(ValueError, "finalization failed"):
            recorder.finalize(corrupt, {}, FFMPEG)


if __name__ == "__main__":
    unittest.main()
