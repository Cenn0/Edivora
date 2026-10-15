"""Local AI speech detection controls and bounded, meaningful segments."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from local_ai_photo_editor.ai import voice

from local_ai_photo_editor.ai.voice import (
    MAX_ANALYSIS_MS, VOICE_MODEL_SIZE, detect_speech, verified_voice_model,
    voice_worker,
)


class VoiceSegmentTests(unittest.TestCase):
    def test_speech_hysteresis_padding_and_join(self) -> None:
        # [silence, speech, short silence, speech, long silence]
        probabilities = [0.0] * 10 + [0.85] * 20 + [0.0] * 4 + [0.9] * 20 + [0.0] * 30
        segments = detect_speech(probabilities, length_ms=len(probabilities) * 32)
        self.assertEqual(len(segments), 1)
        start, end = segments[0]
        self.assertLessEqual(start, 10 * 32)
        self.assertGreater(end, 50 * 32)

    def test_silence_and_short_transients_are_not_speech(self) -> None:
        self.assertEqual(detect_speech(np.zeros(300)), [])
        self.assertEqual(detect_speech([0.9] * 3 + [0.0] * 20), [])

    def test_invalid_and_nonfinite_outputs_are_rejected(self) -> None:
        for case in ([float("nan")], [float("inf")], [-0.3], [2.0]):
            with self.subTest(case=case), self.assertRaises(ValueError):
                detect_speech(case)

    def test_model_verification_rejects_damaged_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.onnx"
            path.write_bytes(b"not a real model")
            with self.assertRaises(ValueError):
                verified_voice_model(path)

    def test_pcm_decoder_discards_stderr_and_checks_size_before_reading(self) -> None:
        def mock_decoder(args, **kwargs):
            self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
            self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
            self.assertNotEqual(kwargs["stdout"], subprocess.PIPE)
            self.assertEqual(kwargs["timeout"], 120)
            kwargs["stdout"].write(bytes.fromhex("0100") * voice.FRAME_SAMPLES)
            return subprocess.CompletedProcess(args, 0)

        with patch.object(voice.subprocess, "run", side_effect=mock_decoder):
            decoded = voice._read_pcm(Path("mocked.wav"), 0, 1000, "fake-ffmpeg")
        self.assertEqual(len(decoded), voice.FRAME_SAMPLES)

    def test_oversized_pcm_rejected_without_reading_into_memory(self) -> None:
        def mock_decoder(args, **kwargs):
            # Sparse file: no 29 MiB allocation required for the regression.
            kwargs["stdout"].seek(voice.MAX_AUDIO_OUTPUT_BYTES + 1)
            kwargs["stdout"].write(b"x")
            return subprocess.CompletedProcess(args, 0)

        with patch.object(voice.subprocess, "run", side_effect=mock_decoder):
            with self.assertRaisesRegex(ValueError, "audio size"):
                voice._read_pcm(Path("mocked.wav"), 0, 1000, "fake-ffmpeg")

    def test_voice_worker_fails_closed_on_untrusted_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "request.json").write_text('{"source":"http://example.com/s.wav"}', encoding="utf-8")
            result = voice_worker(root)
            self.assertEqual(result, 1)
            self.assertIn('"ok": false', (root / "result.json").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
