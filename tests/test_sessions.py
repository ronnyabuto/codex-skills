"""Native exec stream boundaries: errors, recovery classification and usage."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from codex_session import analyze


class SessionTests(unittest.TestCase):
    def test_limits_come_from_native_failures_not_answer_or_tool_text(self):
        answer = {"type": "item.completed", "item": {"type": "agent_message", "text": "Explain rate limits and 429 errors."}}
        usage = {"type": "turn.completed", "usage": dict(input_tokens=100, output_tokens=20,
                  cached_input_tokens=90, reasoning_output_tokens=5)}
        for event, expected in (
            ({"type": "turn.failed", "error": {"message": "You've hit your usage limit"}}, "limit_reached"),
            ({"type": "error", "message": "429 Too Many Requests"}, "limit_reached"),
            ({"type": "turn.failed", "error": {"message": "Unauthorized"}}, "api_error"),
            ({"type": "item.completed", "item": {"type": "command_execution", "aggregated_output": "429 rate limit"}}, None),
        ):
            with self.subTest(event=event):
                stream = "\n".join(map(json.dumps, (answer, usage, event)))
                result, _ = analyze(stream, 0)
                self.assertEqual(result["error"], expected)
                self.assertEqual(result["reported_tokens"], 120)
                self.assertEqual(analyze(stream, 0, timed_out=True)[0]["error"], "timeout")
        failed, _ = analyze(json.dumps({"type": "turn.failed", "error": {"message": "Usage limit reached"}}), 1)
        self.assertEqual(failed["error"], "limit_reached")
        self.assertIsNone(failed["reported_tokens"])

    def test_incomplete_and_malformed_streams_never_score_success(self):
        for stream, expected in (("", "missing_answer"), ('{"type":', "malformed_events"),
                ('{"type":"item.completed","item":{"type":"agent_message","text":"Done"}}', "incomplete_turn"),
                ('{"type":"item.completed"}', "malformed_events")):
            with self.subTest(stream=stream):
                result, _ = analyze(stream, 0)
                self.assertEqual(result["error"], expected)
                self.assertIsNone(result["reported_tokens"])
