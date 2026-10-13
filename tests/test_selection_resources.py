"""Selection-output resource cleanup under allocation failure."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from local_ai_photo_editor.core.selection_io import write_subject_result


class SelectionResourceTests(unittest.TestCase):
    def test_allocation_failure_closes_descriptor_and_preserves_previous_mask(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            mask = Image.new("L", (20, 20), 128)
            write_subject_result(mask, directory)
            original = (directory / "mask.png").read_bytes()
            descriptors = []
            real_mkstemp = tempfile.mkstemp

            def record_descriptor(*args, **kwargs):
                descriptor, name = real_mkstemp(*args, **kwargs)
                descriptors.append(descriptor)
                return descriptor, name

            try:
                with patch("local_ai_photo_editor.core.selection_io.tempfile.mkstemp", side_effect=record_descriptor), \
                     patch("local_ai_photo_editor.core.selection_io.Image.frombytes", side_effect=MemoryError("fixture")):
                    with self.assertRaises(MemoryError):
                        write_subject_result(mask, directory)
                self.assertEqual(len(descriptors), 1)
                with self.assertRaises(OSError):
                    os.fstat(descriptors[0])
                self.assertEqual((directory / "mask.png").read_bytes(), original)
                self.assertEqual([path.name for path in directory.iterdir()], ["mask.png"])
            finally:
                # Allow the test harness to clean up even when a regression
                # leaves a handle open on Windows.
                for descriptor in descriptors:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass


if __name__ == "__main__":
    unittest.main()
