"""Branding and forward-compatible identity checks."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import unittest
from xml.etree import ElementTree

from local_ai_photo_editor.branding import (
    APP_NAME, PHOTO_EDITOR_TITLE, BRAND_TAGLINE_DE, BRAND_TAGLINE_EN, mark_path,
)


class BrandIdentityTests(unittest.TestCase):
    def test_brand_is_media_neutral_and_local(self) -> None:
        self.assertEqual(APP_NAME, "Edivora")
        self.assertIn(APP_NAME, PHOTO_EDITOR_TITLE)
        self.assertIn("lokal", BRAND_TAGLINE_DE.lower())
        self.assertIn("local", BRAND_TAGLINE_EN.lower())

    def test_brand_assets_are_valid_self_contained_svg(self) -> None:
        assets = mark_path().parent
        for name in ("edivora-mark.svg", "edivora-wordmark.svg",
                     "edivora-mark-mono.svg", "edivora-banner.svg"):
            with self.subTest(name=name):
                data = (assets / name).read_text(encoding="utf-8")
                root = ElementTree.fromstring(data)
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                self.assertIn("viewBox", root.attrib)
                self.assertNotIn("http://", data.replace("http://www.w3.org/2000/svg", ""))
                self.assertNotIn("https://", data)
                self.assertNotIn("Planned</text>", data)

    @unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt is unavailable")
    def test_qt_icon_renders_from_svg(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from local_ai_photo_editor.branding import app_icon
        app = QApplication.instance() or QApplication([])
        icon = app_icon()
        self.assertFalse(icon.isNull())
        self.assertFalse(icon.pixmap(64, 64).isNull())
        self.assertGreater(icon.pixmap(64, 64).toImage().pixelColor(64//2, 64//2).alpha(), 0)
