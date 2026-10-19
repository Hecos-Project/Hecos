"""
Unit tests for the Hecos unified progress system.
Uses stdlib unittest.
"""
import io
import time
import unittest
from hecos.core.progress.model import Task, Phase, CancellationRequested
from hecos.core.progress.main import ProgressManager
from hecos.core.progress.sinks.cli_plain import CliPlainSink
from hecos.core.progress.adapters.pip import _PROGRESS_RAW_RE


class TestProgressSystem(unittest.TestCase):
    def test_task_weighted_phases(self):
        phases = [
            ("download", 40.0, "Download"),
            ("verify", 10.0, "Verifica"),
            ("install", 50.0, "Installazione"),
        ]
        t = Task("test_weighted", "Test Task", phases=phases)
        self.assertEqual(t.overall_percent(), 0.0)

        # Halfway through download (50% of 40 weight = 20% overall)
        t.phase("download")
        t.advance(percent=50.0)
        self.assertEqual(t.overall_percent(), 20.0)

        # Moving to verify phase completes download automatically (40% overall)
        t.phase("verify")
        self.assertEqual(t.overall_percent(), 40.0)

        # Halfway through verify (40 + 5 = 45% overall)
        t.advance(percent=50.0)
        self.assertEqual(t.overall_percent(), 45.0)

        # Moving to install (40 + 10 = 50% overall)
        t.phase("install")
        self.assertEqual(t.overall_percent(), 50.0)

        # 80% through install (50 + 40 = 90% overall)
        t.advance(percent=80.0)
        self.assertEqual(t.overall_percent(), 90.0)

        # Done marks 100%
        t.done()
        self.assertEqual(t.overall_percent(), 100.0)
        self.assertEqual(t.state, "done")

    def test_task_cancellation(self):
        cancelled_called = []
        def on_cancel_hook():
            cancelled_called.append(True)

        t = Task("test_cancel", "Cancellable Task", on_cancel=on_cancel_hook)
        self.assertFalse(t.is_cancelled)
        t.check_cancelled()  # Should not raise

        t.cancel("Motivo annullamento")
        self.assertTrue(t.is_cancelled)
        self.assertEqual(t.state, "cancelled")
        self.assertEqual(len(cancelled_called), 1)

        with self.assertRaises(CancellationRequested):
            t.check_cancelled()

    def test_progress_manager_context(self):
        pm = ProgressManager()

        # Successful run
        with pm.task("ctx_success", "Success Context") as t:
            t.advance(percent=50.0)
        self.assertEqual(t.state, "done")
        self.assertEqual(t.overall_percent(), 100.0)

        # Cancelled run
        with pm.task("ctx_cancel", "Cancel Context") as t:
            t.cancel("User cancel")
            t.check_cancelled()
        self.assertEqual(t.state, "cancelled")

        # Errored run
        with self.assertRaises(ValueError):
            with pm.task("ctx_error", "Error Context") as t:
                raise ValueError("Something broke")
        self.assertEqual(t.state, "error")
        self.assertIn("Something broke", t.error)

    def test_pip_regex(self):
        line1 = "Progress 12345 of 67890\n"
        m = _PROGRESS_RAW_RE.match(line1)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), 12345)
        self.assertEqual(int(m.group(2)), 67890)

        line2 = "Collecting torch>=2.0\n"
        self.assertIsNone(_PROGRESS_RAW_RE.match(line2))

    def test_cli_plain_sink(self):
        stream = io.StringIO()
        sink = CliPlainSink(stream=stream)
        t = Task("cli_test", "CLI Output Test")

        t.advance(bytes_done=1024 * 1024, total_bytes=2 * 1024 * 1024, message="Scaricamento")
        sink.update(t)

        t.done("Finito")
        sink.update(t)

        output = stream.getvalue()
        self.assertIn("CLI Output Test", output)
        self.assertTrue("DONE" in output or "100%" in output)


if __name__ == "__main__":
    unittest.main()
