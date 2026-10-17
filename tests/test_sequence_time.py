"""Timeline round trips and exact cut-boundary semantics."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from local_ai_photo_editor.core.media_project import MediaClip, MediaSequence
from local_ai_photo_editor.core.sequence_time import SequenceTimebase


class SequenceTimebaseTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        media = root / "s.wav"
        media.write_bytes(b"wave-data" * 120)
        a = MediaClip.create("audio", media, 5000, start_ms=200, end_ms=2300)
        b = MediaClip.create("audio", media, 5000, start_ms=800, end_ms=1600)
        c = MediaClip.create("audio", media, 5000, start_ms=3000, end_ms=4500)
        self.a, self.b, self.c = a, b, c
        self.t = SequenceTimebase(MediaSequence("audio", (a,b,c)))

    def test_mapping_start_boundaries_and_exact_end(self):
        self.assertEqual(self.t.total_ms, 4400)
        self.assertEqual(self.t.at(0).source_ms, 200)
        self.assertEqual(self.t.at(2099).source_ms, 2299)
        self.assertEqual(self.t.at(2100).clip_id, self.b.id)
        self.assertEqual(self.t.at(2100).source_ms, 800)
        self.assertEqual(self.t.at(2900).clip_id, self.c.id)
        self.assertEqual(self.t.at(4400).source_ms, 4500)
        self.assertTrue(self.t.at(4400).at_end)
        self.assertFalse(self.t.at(4399).at_end)

    def test_inverse_roundtrip_and_bounds(self):
        for position in (0,1,2099,2100,2500,2899,2900,3600,4399,4400):
            with self.subTest(position=position):
                point = self.t.at(position)
                self.assertEqual(self.t.to_sequence(point.clip_id, point.source_ms), position)
        self.assertEqual(self.t.clip_bounds(self.b.id),(2100,2900))

    def test_rejects_bad_time_and_unknown_clip(self):
        for value in (-1,4401,True,False,1.5,"1",None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.t.at(value)
        for val in (-1,2301,True,4000):
            with self.assertRaises(ValueError):
                self.t.to_sequence(self.a.id, val)
        with self.assertRaises(ValueError):
            self.t.clip_bounds("unknown")

if __name__ == "__main__":
    unittest.main()
