"""Opt-in application composition; the existing default entry point is unchanged."""
from __future__ import annotations

from functools import partial

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QWidget

from .detail_strings import text
from .guided_window import EditorWindow as StandardEditorWindow
from .precision_dialog import PrecisionDialog


class EditorWindow(StandardEditorWindow):
    def _t(self, key: str, **values: object) -> str:
        if key.startswith("detail_"):
            return text(self.language, key, **values)
        return super()._t(key, **values)

    def _build_ui(self) -> None:
        super()._build_ui()
        card, layout = self._card("detail_title", "detail_hint")
        self.detail_ai_button = self._button("detail_ai", self.show_ai_tools)
        self.manual_selection_button = self._button("detail_manual", self.show_manual_selection)
        layout.addWidget(self.detail_ai_button)
        layout.addWidget(self.manual_selection_button)
        self.findChild(QWidget, "toolsPanel").layout().insertWidget(0, card)
        self.manual_selection_action = self._action("detail_manual", self.show_manual_selection)
        self.manual_selection_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self._edit_menu.addAction(self.manual_selection_action)

    def _update_state(self) -> None:
        super()._update_state()
        if not hasattr(self, "manual_selection_button"):
            return
        enabled = self._editable() and not self.crop_button.isChecked()
        for control in (self.detail_ai_button, self.manual_selection_button, self.manual_selection_action):
            control.setEnabled(enabled)

    def show_ai_tools(self, mode: str = "blur") -> None:
        if not isinstance(mode, str):
            mode = "blur"
        self._run_workspace(PrecisionDialog, mode, "detail_operation")

    def show_manual_selection(self) -> None:
        dialog_type = partial(PrecisionDialog, manual=True, start_immediately=False)
        self._run_workspace(dialog_type, "light", "detail_operation")
