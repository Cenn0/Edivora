"""Four-model capability routing, resource gates and true model contracts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from local_ai_photo_editor.ai.catalog import (
    ISNET_SHA256, MODEL_IDS, SPECS, SystemMemory, TASK_IMAGE,
    TASK_TRANSCRIBE, TASK_VOICE, choose_model, model_installed, recommended,
)
from local_ai_photo_editor.ai.background import _predict_isnet
from local_ai_photo_editor.ai.models import ModelIntegrityError
from local_ai_photo_editor.ai.transcribe import _export_text, transcribe
from local_ai_photo_editor import __main__ as entry


GiB = 1024 ** 3


class HardwareSelectionTests(unittest.TestCase):
    def test_four_distinct_pinned_capabilities_and_cpu_only_contract(self) -> None:
        self.assertEqual(set(MODEL_IDS),
                         {"u2netp", "isnet-general-use", "silero-vad", "whisper-tiny"})
        self.assertEqual({s.task for s in SPECS.values()},
                         {TASK_IMAGE, TASK_VOICE, TASK_TRANSCRIBE})
        self.assertEqual(len(ISNET_SHA256), 64)

    def test_auto_selects_best_available_model_that_fits_real_resources(self) -> None:
        healthy = SystemMemory(16 * GiB, 6 * GiB, 8)
        constrained = SystemMemory(4 * GiB, 2 * GiB, 4)
        tiny = SystemMemory(2 * GiB, 1 * GiB, 2)
        with patch("local_ai_photo_editor.ai.catalog.model_installed", return_value=True):
            self.assertEqual(choose_model(TASK_IMAGE, hardware=healthy), "isnet-general-use")
            self.assertEqual(choose_model(TASK_IMAGE, hardware=constrained), "u2netp")
            self.assertEqual(choose_model(TASK_IMAGE, hardware=tiny), "u2netp")
            self.assertEqual(choose_model(TASK_TRANSCRIBE, hardware=healthy), "whisper-tiny")
            self.assertIsNone(choose_model(TASK_TRANSCRIBE, hardware=tiny))
            self.assertEqual(choose_model(TASK_VOICE, hardware=tiny), "silero-vad")

    def test_no_hardware_signal_conservatively_chooses_lightweight(self) -> None:
        unknown = SystemMemory(0, 0, 6, False)
        with patch("local_ai_photo_editor.ai.catalog.model_installed", return_value=True):
            self.assertEqual(choose_model(TASK_IMAGE, hardware=unknown), "u2netp")
            self.assertIsNone(choose_model(TASK_TRANSCRIBE, hardware=unknown))
        self.assertFalse(recommended("isnet-general-use", unknown))

    def test_manual_override_is_allowed_but_not_unknown_or_missing(self) -> None:
        low_memory = SystemMemory(2 * GiB, 1 * GiB, 2)
        with patch("local_ai_photo_editor.ai.catalog.model_installed", return_value=True):
            self.assertEqual(choose_model(TASK_IMAGE, "isnet-general-use",
                                          hardware=low_memory), "isnet-general-use")
            with self.assertRaises(ValueError):
                choose_model(TASK_IMAGE, "whisper-tiny", hardware=low_memory)
            with self.assertRaises(ValueError):
                choose_model(TASK_IMAGE, "__import__('os')", hardware=low_memory)
        with patch("local_ai_photo_editor.ai.catalog.model_installed", return_value=False):
            with self.assertRaises(FileNotFoundError):
                choose_model(TASK_IMAGE, "u2netp", hardware=low_memory)
            self.assertIsNone(choose_model(TASK_IMAGE, hardware=low_memory))


class StrongISNetAdapterTests(unittest.TestCase):
    def test_model_input_shape_preprocessing_and_rgba_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "isnet.onnx"
            artifact.write_bytes(b"synthetic-model-bytes")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            class FakeInput:
                name = "input_image"
                shape = [1, 3, 1024, 1024]
            class FakeOutput:
                name = "output_image"
            class FakeSession:
                def get_inputs(self):
                    return [FakeInput()]
                def get_outputs(self):
                    return [FakeOutput()]
                def run(self, names, arguments):
                    arr = arguments["input_image"]
                    assert arr.shape == (1, 3, 1024, 1024)
                    assert arr.dtype == np.float32
                    assert np.isfinite(arr).all()
                    arr = np.linspace(0, 1, 1024 * 1024, dtype=np.float32)
                    return [arr.reshape((1, 1, 1024, 1024))]
            with (
                patch("local_ai_photo_editor.ai.catalog.model_file", return_value=artifact),
                patch("local_ai_photo_editor.ai.catalog.ISNET_SHA256", digest),
                patch("onnxruntime.InferenceSession", return_value=FakeSession()),
            ):
                result = _predict_isnet(Image.new("RGB", (53, 31), "purple"))
            self.assertEqual(result.mode, "L")
            self.assertEqual(result.size, (53, 31))
            minimum, maximum = result.getextrema()
            # Lanczos downsampling cannot retain the outermost values for
            # an artificial ramp, but the mask still spans almost the range.
            self.assertLess(minimum, 20)
            self.assertGreater(maximum, 235)

    def test_model_rejects_corrupt_hash(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "invalid.onnx"
            path.write_bytes(b"not-onxx")
            with patch("local_ai_photo_editor.ai.catalog.model_file", return_value=path):
                with self.assertRaises(ModelIntegrityError):
                    _predict_isnet(Image.new("RGB", (20, 20), "red"))


class WhisperContractTests(unittest.TestCase):
    def test_two_languages_use_documented_offline_sherpa_api(self) -> None:
        class FakeResult:
            text = "Testtranskript"
        class Stream:
            result = FakeResult()
            def accept_waveform(self, sample_rate, waveform):
                self.sample_rate = sample_rate
                self.waveform = waveform
        class Recognizer:
            def create_stream(self):
                return Stream()
            def decode_stream(self, stream):
                self.assert_not_missing = stream
        received = []
        class Factory:
            @staticmethod
            def from_whisper(**kwargs):
                received.append(kwargs)
                return Recognizer()
        fake_audio = np.ones(16_000 * 22, dtype=np.float32)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "test.wav"
            source.write_bytes(b"source fixture")
            with (
                patch("local_ai_photo_editor.ai.transcribe.model_installed", return_value=True),
                patch("local_ai_photo_editor.ai.transcribe.model_file",
                      side_effect=lambda mid, name: source),
                patch("local_ai_photo_editor.ai.transcribe._read_pcm", return_value=fake_audio),
                patch("sherpa_onnx.OfflineRecognizer", Factory),
            ):
                items = transcribe(source, "audio", 0, 22_000, "de", ffmpeg="ffmpeg")
            self.assertEqual(len(items), 2)
            self.assertEqual(received[0]["provider"], "cpu")
            self.assertEqual(received[0]["language"], "de")
            self.assertEqual(received[0]["task"], "transcribe")

    def test_srt_is_chunk_labeled_not_word_aligned(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            srt = Path(folder) / "preview.srt"
            _export_text([{"start_ms": 1200, "end_ms": 20_000,
                           "text": "Hallo und guten Tag."}], srt)
            content = srt.read_text("utf-8")
            self.assertIn("00:00:01,200 --> 00:00:20,000", content)
            self.assertIn("Hallo und guten Tag", content)

    def test_transcription_worker_arguments_are_allowlisted(self) -> None:
        self.assertEqual(
            entry.media_job_command("transcribe", "work")[1][-3:],
            ["--media-ai-job", "transcribe", "work"],
        )
        with self.assertRaises(ValueError):
            entry.media_job_command("remote_transcribe", "work")
