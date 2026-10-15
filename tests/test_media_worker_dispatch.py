"""Restoration and the older media workers must have exactly one process owner."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from local_ai_photo_editor.__main__ import main


class MediaWorkerRoutingTests(unittest.TestCase):
    def test_restoration_worker_is_reachable_without_a_second_windows_job(self) -> None:
        with tempfile.TemporaryDirectory() as folder, \
             patch("local_ai_photo_editor.ai.video_restoration.restoration_worker",
                   return_value=19) as restore, \
             patch("local_ai_photo_editor.core.process_tree.protect_media_ai_worker",
                   side_effect=AssertionError("Restoration must manage its own job")):
            self.assertEqual(main(["--media-ai-job", "restore", folder]), 19)
            self.assertEqual(restore.call_args.args[0], Path(folder))
            restore.assert_called_once()

    def test_voice_and_single_frame_keep_security_preflight(self) -> None:
        for operation, module, worker_name in (
            ("voice", "local_ai_photo_editor.ai.voice", "voice_worker"),
            ("frame", "local_ai_photo_editor.ai.video_frame", "frame_worker"),
        ):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as folder, \
                 patch("local_ai_photo_editor.core.process_tree.protect_media_ai_worker") as protect, \
                 patch(f"{module}.{worker_name}", return_value=0) as worker:
                self.assertEqual(main(["--media-ai-job", operation, folder]), 0)
                protect.assert_called_once_with()
                self.assertEqual(worker.call_args.args[0], Path(folder))

    def test_unexpected_operation_rejected_before_any_worker_starts(self) -> None:
        with patch("local_ai_photo_editor.core.process_tree.protect_media_ai_worker",
                   side_effect=AssertionError("No worker should run")):
            self.assertEqual(main(["--media-ai-job", "unknown", "/tmp"]), 2)


if __name__ == "__main__":
    unittest.main()
