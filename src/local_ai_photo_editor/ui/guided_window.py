"""Public editor composition: existing document/AI workflow plus guided tools.

The base window retains project persistence, source protection, brush editing
and inference ownership. New editing UI stays in a separate testable component.
"""
from __future__ import annotations

from PySide6.QtGui import QCloseEvent, QKeySequence
from PySide6.QtWidgets import QDialog, QWidget

from .editing_dialog import EditingDialog
from .editing_strings import STRINGS, text
from .window import EditorWindow as BaseEditorWindow


class EditorWindow(BaseEditorWindow):
    def _editable(self) -> bool:
        return super()._editable() and getattr(self, "_editing_dialog", None) is None

    def _t(self, key: str, **values: object) -> str:
        if key.startswith("tools_") and key in STRINGS[self.language]:
            return text(self.language, key, **values)
        return super()._t(key, **values)

    def _build_ui(self) -> None:
        super()._build_ui()
        self._editing_dialog: EditingDialog | None = None
        card, layout = self._card("tools_title", "tools_hint")
        self.editing_buttons = []
        for section in ("light", "look", "shape", "background"):
            button = self._button("tools_" + section,
                                  lambda checked=False, selected=section: self.show_editing_tools(selected))
            layout.addWidget(button)
            self.editing_buttons.append(button)
        panel = self.findChild(QWidget, "toolsPanel")
        panel.layout().insertWidget(0, card)
        self.editing_action = self._action("tools_title", self.show_editing_tools)
        self.editing_action.setShortcut(QKeySequence("Ctrl+E"))
        self._edit_menu.addSeparator()
        self._edit_menu.addAction(self.editing_action)

    def _update_state(self) -> None:
        super()._update_state()
        if not hasattr(self, "editing_buttons"):
            return
        enabled = self._editable() and not self.crop_button.isChecked()
        for control in (*self.editing_buttons, self.editing_action):
            control.setEnabled(enabled)
            control.setToolTip(self._t("tools_hint" if enabled else "tools_unavailable"))

    def show_editing_tools(self, section: str = "light") -> None:
        if not isinstance(section, str):
            section = "light"
        if not self._editable() or self.crop_button.isChecked():
            return
        document, revision = self.document, self._revision
        try:
            dialog = EditingDialog(document.current, self.language, section, self)
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("edit_error", exc)
            return
        self._editing_dialog = dialog
        self._update_state()
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
        finally:
            self._editing_dialog = None
            self._update_state()
        try:
            if (accepted and dialog.result_image is not None
                    and self.document is document and self._revision == revision):
                self._accept_result(dialog.result_image, "tools_operation")
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("edit_error", exc)
        finally:
            dialog.deleteLater()

    def closeEvent(self, event: QCloseEvent) -> None:
        dialog = getattr(self, "_editing_dialog", None)
        if dialog is not None:
            dialog.reject()
            # Never destroy the parent of a running QThread.
            event.ignore()
            return
        super().closeEvent(event)
