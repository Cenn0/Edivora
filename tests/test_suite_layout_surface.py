"""Keep native-desktop evidence distinct from exact oversized client layouts."""
from __future__ import annotations

import os
import unittest

from PySide6.QtCore import QSize, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QPushButton, QVBoxLayout

from local_ai_photo_editor.suite_smoke import _LayoutSurface


class LayoutSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def settle(self):
        self.app.processEvents()
        QTest.qWait(20)
        self.app.processEvents()

    def test_oversized_client_then_native_window_restores_flags_and_actions(self):
        window = QMainWindow()
        button = QPushButton("Open another workspace")
        window.setCentralWidget(button)
        surface = _LayoutSurface(window)
        original_flags = window.windowFlags()
        clicked = []
        button.clicked.connect(lambda: clicked.append(True))
        try:
            available = window.screen().availableGeometry()
            large = QSize(available.width() + 160, available.height() + 120)
            self.assertEqual(surface.resize(large.width(), large.height()),
                             "embedded-native-client-layout")
            self.settle()
            host = surface.host
            self.assertIs(window.parentWidget(), host)
            self.assertFalse(window.isWindow())
            self.assertEqual(window.size(), large)
            self.assertEqual(window.grab().deviceIndependentSize().toSize(), large)
            button.click()
            self.assertEqual(clicked, [True])
            # Reuse the host, rather than leaking a window on every matrix cell.
            surface.resize(large.width() + 16, large.height() + 16)
            self.settle()
            self.assertIs(surface.host, host)
            self.assertEqual(window.size(), large + QSize(16, 16))
            small = QSize(260, 120)
            self.assertEqual(surface.resize(small.width(), small.height()), "native-top-level")
            self.settle()
            self.assertIsNone(window.parentWidget())
            self.assertTrue(window.isWindow())
            self.assertEqual(window.windowFlags(), original_flags)
            self.assertEqual(window.size(), small)
            self.assertFalse(host.isVisible())
            button.click()
            self.assertEqual(clicked, [True, True])
        finally:
            window.close()
            window.deleteLater()
            surface.close()
            self.settle()

    def test_embedded_dialog_keeps_explicit_acceptance_and_full_capture(self):
        dialog = QDialog()
        layout = QVBoxLayout(dialog)
        button = QPushButton("Apply")
        layout.addWidget(button)
        button.clicked.connect(dialog.accept)
        surface = _LayoutSurface(dialog)
        try:
            available = dialog.screen().availableGeometry()
            size = QSize(available.width() + 80, available.height() + 80)
            self.assertEqual(surface.resize(size.width(), size.height()),
                             "embedded-native-client-layout")
            self.settle()
            self.assertEqual(dialog.size(), size)
            self.assertEqual(dialog.grab().deviceIndependentSize().toSize(), size)
            self.assertTrue(button.isVisibleTo(dialog))
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        finally:
            dialog.close()
            dialog.deleteLater()
            surface.close()
            self.settle()
