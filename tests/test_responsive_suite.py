"""Geometry regressions: essential chrome stays visible and inspector controls reachable."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import (
    QAbstractButton, QAbstractSpinBox, QApplication, QComboBox, QScrollArea, QSlider,
)
from PySide6.QtTest import QTest

from local_ai_photo_editor.ui.responsive import in_viewport

SIZES = ((640, 480), (960, 540), (1280, 800), (1920, 1080))


class ResponsiveSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def settle(self):
        self.app.processEvents()
        QTest.qWait(2)
        self.app.processEvents()

    def assert_chrome(self, window, controls):
        for control in controls:
            with self.subTest(control=control.accessibleName() or control.objectName()):
                self.assertTrue(control.isVisibleTo(window))
                self.assertTrue(in_viewport(control, window),
                    f"{control.objectName()}/{control.accessibleName()} outside {window.size()}: {control.geometry()}")
                self.assertGreater(control.width(), 20)
                self.assertGreater(control.height(), 18)

    def assert_scroll_controls_reachable(self, window):
        for scroll in window.findChildren(QScrollArea):
            if not scroll.isVisibleTo(window):
                continue
            page = scroll.widget()
            if page is None:
                continue
            widgets = page.findChildren(QAbstractButton) + page.findChildren(QAbstractSpinBox) + page.findChildren(QSlider) + page.findChildren(QComboBox)
            for control in widgets:
                if not control.isVisibleTo(page):
                    continue
                scroll.ensureWidgetVisible(control, 0, 0)
                self.settle()
                self.assertTrue(in_viewport(control, scroll.viewport()),
                    f"Unreachable {type(control).__name__}/{control.accessibleName()} in {window.windowTitle()} at {window.size()}")

    def test_launcher_reflows_and_direct_actions_remain_visible(self):
        from local_ai_photo_editor.ui.launcher import LauncherWindow
        w = LauncherWindow(lambda _: True)
        try:
            w.show()
            for language in (0, 1):
                w.language_combo.setCurrentIndex(language)
                for width, height in SIZES:
                    with self.subTest(language=language, size=(width, height)):
                        w.resize(width, height)
                        self.settle()
                        self.assertEqual(w.size(), QSize(width, height))
                        self.assert_chrome(w, [*w.quick_buttons.values(), w.language_combo])
        finally:
            w.close()
            w.deleteLater()

    def test_all_media_tabs_remain_reachable_at_supported_sizes(self):
        from local_ai_photo_editor.ui.sequence_window import SequenceWindow
        for kind in ("video", "audio"):
            w = SequenceWindow(kind)
            try:
                w.show()
                for language in (0, 1):
                    w.language_combo.setCurrentIndex(language)
                    for width, height in SIZES:
                        with self.subTest(kind=kind, language=language, size=(width, height)):
                            w.resize(width, height)
                            self.settle()
                            self.assertEqual(w.size(), QSize(width, height))
                            self.assert_chrome(w, [w.open_button, w.export_button, w.save_project_button,
                                w.play_button, w.stop_button, w.undo_button, w.redo_button,
                                w.add_button, w.remove_button, w.up_button, w.down_button,
                                w.duplicate_button, w.split_button, w.language_combo, w.timeline])
                            for index in range(w.inspector_tabs.count()):
                                w.inspector_tabs.setCurrentIndex(index)
                                self.settle()
                                self.assert_scroll_controls_reachable(w)
            finally:
                w._dirty = False
                w.close()
                w.deleteLater()
                self.settle()

    def test_photo_toolbar_navigation_and_tools_do_not_clip(self):
        from local_ai_photo_editor.ui import EditorWindow
        w = EditorWindow()
        try:
            w.set_document(Image.new("RGB", (320, 180), (30, 100, 150)))
            w.show()
            for language in ("de", "en"):
                w.set_language(language)
                for width, height in SIZES:
                    with self.subTest(language=language, size=(width, height)):
                        w.resize(width, height)
                        self.settle()
                        self.assertEqual(w.size(), QSize(width, height))
                        self.assert_chrome(w, [w.open_button, w.export_button, w.undo_button,
                            w.redo_button, w.original_button, w.language_combo,
                            w.nav_start, w.nav_photo, w.nav_video, w.nav_audio])
                        self.assert_scroll_controls_reachable(w)
        finally:
            w.close()
            w.deleteLater()

    def test_icon_only_buttons_keep_full_accessible_labels(self):
        from local_ai_photo_editor.ui.icons import IconButton
        button = IconButton("Rückgängig", icon_name="undo")
        button.setCompact(True)
        self.assertEqual(button.text(), "")
        self.assertEqual(button.accessibleName(), "Rückgängig")
        self.assertEqual(button.toolTip(), "Rückgängig")
        self.assertFalse(button.icon().pixmap(40, 40).isNull())
        button.setText("Undo")
        self.assertEqual(button.accessibleName(), "Undo")
        button.setCompact(False)
        self.assertEqual(button.text(), "Undo")
        button.deleteLater()
