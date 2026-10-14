"""The same interactive trim timeline drives both Qt media editors.

These are widget and export-contract regressions; they do not replace the
real FFmpeg and packaged multimedia smoke checks.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

QT_AVAILABLE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(QT_AVAILABLE, "Qt runtime unavailable; Windows/Linux GUI CI required.")
class TrimTimelineQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from local_ai_photo_editor.ui.trim_timeline import TrimTimeline

        cls.app = QApplication.instance() or QApplication([])
        cls.Qt = Qt
        cls.QPoint = QPoint
        cls.QTest = QTest
        cls.timeline_type = TrimTimeline

    def setUp(self) -> None:
        self.timeline = self.timeline_type()
        self.timeline.resize(600, 110)
        self.timeline.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.timeline.close()
        self.timeline.deleteLater()
        self.app.processEvents()

    def test_empty_state_and_reset_range(self) -> None:
        w = self.timeline
        self.assertFalse(w.isEnabled())
        self.assertEqual(w.duration_ms, 0)
        w.set_duration(12_000)
        self.assertTrue(w.isEnabled())
        self.assertEqual((w.start_ms, w.end_ms, w.position_ms), (0, 12_000, 0))
        w.set_range(2_300, 7_800)
        self.assertEqual((w.start_ms, w.end_ms), (2_300, 7_800))
        w.set_position(15_000)
        self.assertEqual(w.position_ms, 12_000)
        w.set_duration(5_000)
        self.assertEqual((w.start_ms, w.end_ms, w.position_ms), (0, 5_000, 0))
        w.set_duration(0)
        self.assertFalse(w.isEnabled())

    def test_click_seeks_without_changing_export_range(self) -> None:
        w = self.timeline
        w.set_duration(10_000)
        w.set_range(2_000, 8_000)
        received_seeks, received_ranges = [], []
        w.seekRequested.connect(received_seeks.append)
        w.rangeChanged.connect(lambda start, end: received_ranges.append((start, end)))

        x = round(w._x_at(5_000))
        self.QTest.mouseClick(w, self.Qt.MouseButton.LeftButton, pos=self.QPoint(x, 52))
        self.assertTrue(received_seeks)
        self.assertAlmostEqual(received_seeks[-1], 5_000, delta=30)
        self.assertEqual((w.start_ms, w.end_ms), (2_000, 8_000))
        self.assertEqual(received_ranges, [])

    def test_clock_labels_do_not_seek(self) -> None:
        w = self.timeline
        w.set_duration(10_000)
        w.set_range(2_000, 8_000)
        seeks = []
        w.seekRequested.connect(seeks.append)
        self.QTest.mouseClick(
            w, self.Qt.MouseButton.LeftButton,
            pos=self.QPoint(round(w._x_at(5_000)), 8),
        )
        self.assertEqual(seeks, [])

    def test_draggable_start_and_end_are_bounded(self) -> None:
        w = self.timeline
        w.set_duration(10_000)
        w.set_range(2_000, 8_000)
        received = []
        w.rangeChanged.connect(lambda start, end: received.append((start, end)))

        start_x = round(w._x_at(2_000))
        self.QTest.mousePress(w, self.Qt.MouseButton.LeftButton, pos=self.QPoint(start_x, 52))
        self.QTest.mouseMove(w, self.QPoint(round(w._x_at(4_000)), 52))
        self.QTest.mouseRelease(w, self.Qt.MouseButton.LeftButton,
                                pos=self.QPoint(round(w._x_at(4_000)), 52))
        self.assertAlmostEqual(w.start_ms, 4_000, delta=35)
        self.assertEqual(w.end_ms, 8_000)
        self.assertTrue(received)

        end_x = round(w._x_at(8_000))
        self.QTest.mousePress(w, self.Qt.MouseButton.LeftButton, pos=self.QPoint(end_x, 52))
        self.QTest.mouseMove(w, self.QPoint(round(w._x_at(1_000)), 52))
        self.QTest.mouseRelease(w, self.Qt.MouseButton.LeftButton, pos=self.QPoint(60, 52))
        self.assertEqual(w.end_ms - w.start_ms, 100)

    def test_keyboard_fine_and_coarse_adjustment(self) -> None:
        w = self.timeline
        w.set_duration(10_000)
        w.set_range(2_000, 8_000)
        w.active_handle = "start"
        w.setFocus()
        self.QTest.keyClick(w, self.Qt.Key.Key_Right)
        self.assertEqual(w.start_ms, 2_100)
        self.QTest.keyClick(w, self.Qt.Key.Key_Left,
                            self.Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(w.start_ms, 1_100)
        w.active_handle = "end"
        self.QTest.keyClick(w, self.Qt.Key.Key_Left)
        self.assertEqual(w.end_ms, 7_900)
        w.set_range(7_800, 7_900)
        self.QTest.keyClick(w, self.Qt.Key.Key_Left)
        self.assertEqual(w.end_ms, 7_900)

    def test_spinners_timeline_and_export_share_exact_selection(self) -> None:
        from local_ai_photo_editor.ui.media_window import MediaWindow

        with tempfile.TemporaryDirectory() as tmp:
            for kind, suffix, output in (
                ("video", ".mp4", ".mp4"), ("audio", ".wav", ".wav")
            ):
                with self.subTest(kind=kind):
                    src = Path(tmp) / f"source-{kind}{suffix}"
                    src.write_bytes(b"fake bytes used only for range validation")
                    w = MediaWindow(kind)
                    w.show()
                    self.app.processEvents()
                    try:
                        w.source = src
                        w._duration_changed(10_000)
                        self.assertTrue(w.timeline.isEnabled())
                        w.start_spin.setValue(1.250)
                        w.end_spin.setValue(8.500)
                        self.assertEqual((w.timeline.start_ms, w.timeline.end_ms),
                                         (1_250, 8_500))

                        w.timeline._edit_boundary("start", 2_250)
                        self.assertEqual(w.start_spin.value(), 2.250)
                        w.timeline._edit_boundary("end", 7_750)
                        self.assertEqual(w.end_spin.value(), 7.750)
                        export = w._build_export(Path(tmp) / f"output-{kind}{output}")
                        self.assertEqual((export.start_ms, export.end_ms), (2_250, 7_750))

                        w._reset_range()
                        self.assertEqual((w.start_spin.value(), w.end_spin.value()),
                                         (0, 10))
                        self.assertEqual((w.timeline.start_ms, w.timeline.end_ms),
                                         (0, 10_000))
                    finally:
                        w.close()
                        w.deleteLater()
                        self.app.processEvents()

    def test_waveform_image_survives_language_changes(self) -> None:
        from PySide6.QtGui import QPixmap
        from local_ai_photo_editor.ui.media_window import MediaWindow

        w = MediaWindow("audio")
        w.show()
        self.app.processEvents()
        try:
            preview = QPixmap(32, 12)
            preview.fill(self.Qt.GlobalColor.white)
            w._wave_pixmap = preview
            w.wave_label.setPixmap(preview)
            w.duration_ms = 901_000
            w.language_combo.setCurrentIndex(1)
            self.assertFalse(w.wave_label.pixmap().isNull())
            self.assertIn("first 15 minutes", w.wave_label.toolTip())
            w.language_combo.setCurrentIndex(0)
            self.assertFalse(w.wave_label.pixmap().isNull())
            self.assertIn("ersten 15 Minuten", w.wave_label.toolTip())
        finally:
            w.close()
            w.deleteLater()
            self.app.processEvents()

    def test_fade_duration_invalidates_a_short_audio_range(self) -> None:
        from local_ai_photo_editor.ui.media_window import MediaWindow

        with tempfile.TemporaryDirectory() as tmp:
            w = MediaWindow("audio")
            w.show()
            self.app.processEvents()
            try:
                src = Path(tmp) / "sound.wav"
                src.write_bytes(b"fake but safe for window selection validation")
                w.source = src
                w._duration_changed(5_000)
                w.fade_in.setValue(1.5)
                w.fade_out.setValue(1.0)
                w.timeline._edit_boundary("end", 2_000)
                self.assertFalse(w.export_button.isEnabled())
                self.assertIn("Ausschnitt", w.status.text())
            finally:
                w.close()
                w.deleteLater()
                self.app.processEvents()
