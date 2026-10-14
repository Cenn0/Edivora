"""User model preferences: one shared DE/EN UI, no silent downloads."""
from __future__ import annotations

import importlib.util
import os
import unittest
from unittest.mock import patch

from local_ai_photo_editor.ai.catalog import SystemMemory, TASK_IMAGE, TASK_TRANSCRIBE

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT_AVAILABLE, "Qt widgets are available in CI.")
class ModelSettingsQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_auto_and_manual_preferences_persist_without_loading_models(self):
        from local_ai_photo_editor.ui.model_settings import (
            ModelSettingsDialog, get_preference,
        )
        settings = {}
        class MemorySettings:
            def __init__(self, *args):
                pass
            def value(self, key, default=None):
                return settings.get(key, default)
            def setValue(self, key, value):
                settings[key] = value
            def sync(self):
                pass

        strong = SystemMemory(16 * 1024**3, 12 * 1024**3, 12)
        with (
            patch("local_ai_photo_editor.ui.model_settings.QSettings", MemorySettings),
            patch("local_ai_photo_editor.ui.model_settings.detect_hardware", return_value=strong),
            patch("local_ai_photo_editor.ui.model_settings.model_installed", return_value=True),
            patch("local_ai_photo_editor.ai.catalog.model_installed", return_value=True),
        ):
            dialog = ModelSettingsDialog("de")
            dialog.show()
            self.app.processEvents()
            self.assertIn("IS-Net", dialog.summary.text())
            dialog.combos[TASK_IMAGE].setCurrentIndex(
                dialog.combos[TASK_IMAGE].findData("isnet-general-use")
            )
            dialog.combos[TASK_TRANSCRIBE].setCurrentIndex(
                dialog.combos[TASK_TRANSCRIBE].findData("whisper-tiny")
            )
            dialog._save()
            self.assertEqual(get_preference(TASK_IMAGE), "isnet-general-use")
            self.assertEqual(get_preference(TASK_TRANSCRIBE), "whisper-tiny")
            dialog.deleteLater()
            dialog_en = ModelSettingsDialog("en")
            self.assertIn("GPU acceleration is not released", dialog_en.layout().itemAt(2).widget().text())
            dialog_en.close()
            dialog_en.deleteLater()
            self.app.processEvents()
