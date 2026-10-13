"""Compose guided editing and local AI subject tools with the existing editor."""
from __future__ import annotations

from PySide6.QtGui import QCloseEvent, QKeySequence
from PySide6.QtWidgets import QDialog, QWidget

from .editing_dialog import EditingDialog
from .editing_strings import STRINGS, text
from .subject_dialog import SubjectDialog
from .subject_strings import text as subject_text
from .window import EditorWindow as BaseEditorWindow


class EditorWindow(BaseEditorWindow):
    def _editable(self) -> bool:
        return super()._editable() and getattr(self, "_editing_dialog", None) is None

    def _t(self, key: str, **values: object) -> str:
        if key.startswith("subject_"):
            return subject_text(self.language, key, **values)
        if key.startswith("tools_") and key in STRINGS[self.language]:
            return text(self.language, key, **values)
        return super()._t(key, **values)

    def _build_ui(self) -> None:
        super()._build_ui()
        self._editing_dialog: QDialog | None = None
        card, layout = self._card("tools_title", "tools_hint")
        self.editing_buttons = []
        for section in ("light", "look", "shape", "background"):
            button = self._button("tools_" + section,
                                  lambda checked=False, selected=section: self.show_editing_tools(selected))
            layout.addWidget(button)
            self.editing_buttons.append(button)
        panel = self.findChild(QWidget, "toolsPanel")
        panel.layout().insertWidget(0, card)
        ai_card, ai_layout = self._card("subject_title", "subject_hint")
        self.subject_buttons = [
            self._button("subject_blur_open", lambda: self.show_ai_tools("blur")),
            self._button("subject_open", lambda: self.show_ai_tools("color_pop")),
        ]
        for button in self.subject_buttons:
            ai_layout.addWidget(button)
        panel.layout().insertWidget(0, ai_card)
        self.editing_action = self._action("tools_title", self.show_editing_tools)
        self.editing_action.setShortcut(QKeySequence("Ctrl+E"))
        self.subject_action = self._action("subject_title", self.show_ai_tools)
        self.subject_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self._edit_menu.addSeparator()
        self._edit_menu.addActions([self.editing_action, self.subject_action])

    def _update_state(self) -> None:
        super()._update_state()
        if not hasattr(self, "editing_buttons"):
            return
        enabled = self._editable() and not self.crop_button.isChecked()
        for control in (*self.editing_buttons, self.editing_action):
            control.setEnabled(enabled)
            control.setToolTip(self._t("tools_hint" if enabled else "tools_unavailable"))
        for control in (*self.subject_buttons, self.subject_action):
            control.setEnabled(enabled)
            control.setToolTip(self._t("subject_hint" if enabled else "tools_unavailable"))

    def show_editing_tools(self, section: str = "light") -> None:
        if not isinstance(section, str):
            section = "light"
        self._run_workspace(EditingDialog, section, "tools_operation")

    def show_ai_tools(self, mode: str = "blur") -> None:
        if not isinstance(mode, str):
            mode = "blur"
        self._run_workspace(SubjectDialog, mode, "subject_operation")

    def _run_workspace(self, dialog_type, section: str, label: str) -> None:
        if not self._editable() or self.crop_button.isChecked():
            return
        document, revision = self.document, self._revision
        try:
            dialog = dialog_type(document.current, self.language, section, self)
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
                self._accept_result(dialog.result_image, label)
        except (ValueError, OSError, MemoryError) as exc:
            self._show_error("edit_error", exc)
        finally:
            dialog.deleteLater()

    def closeEvent(self, event: QCloseEvent) -> None:
        dialog = getattr(self, "_editing_dialog", None)
        if dialog is not None:
            dialog.reject()
            # Keep the parent alive until any child process/thread has stopped.
            event.ignore()
            return
        super().closeEvent(event)
