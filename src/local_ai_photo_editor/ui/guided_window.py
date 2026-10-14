"""Compose a task-first editor with progressively disclosed precision controls."""
from __future__ import annotations

from PySide6.QtGui import QCloseEvent, QKeySequence
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from .editing_dialog import EditingDialog
from .editing_strings import STRINGS, text
from .subject_dialog import SubjectDialog
from .subject_strings import text as subject_text
from .window import EditorWindow as BaseEditorWindow


class EditorWindow(BaseEditorWindow):
    """Show common photo tasks first; retain the full editor on demand."""

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

        # Keep the original editor's controls and signal connections intact.
        # They are reparented into the optional section, not recreated.
        panel = self.findChild(QWidget, "toolsPanel")
        panel_layout = panel.layout()
        original_cards = []
        while panel_layout.count():
            item = panel_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                original_cards.append(widget)
        ai_card, mask_card, adjustments_card, shape_card = original_cards

        quick_card, quick_layout = self._card("quick_title", "quick_description")
        self.quick_hint_label = self._label("quick_empty", "stepHint", wrap=True)
        quick_layout.addWidget(self.quick_hint_label)
        self.quick_buttons = [
            self._button("quick_improve", lambda: self.show_editing_tools("light"), "quickAction"),
            self._button("quick_crop", lambda: self.show_editing_tools("shape"), "quickAction"),
            self._button("quick_blur", lambda: self.show_ai_tools("blur"), "quickAiAction"),
            # Unlike the original one-click action, this starts a reversible preview.
            self._button("quick_cutout", lambda: self.show_ai_tools("cutout"), "quickAiAction"),
        ]
        for button in self.quick_buttons:
            button.setMinimumHeight(44)
            quick_layout.addWidget(button)
        panel_layout.addWidget(quick_card)

        self.more_tools_button = self._button("quick_more_show", self._toggle_more_tools, "moreTools")
        self.more_tools_button.setCheckable(True)
        panel_layout.addWidget(self.more_tools_button)

        self.more_tools_panel = QWidget()
        advanced_layout = QVBoxLayout(self.more_tools_panel)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(12)

        # Familiar feature entry points remain available and keyboard shortcuts
        # still work even when the advanced section is collapsed.
        tools_card, tools_layout = self._card("tools_title", "tools_hint")
        self.editing_buttons = []
        for section in ("light", "look", "shape", "background"):
            button = self._button(
                "tools_" + section,
                lambda checked=False, selected=section: self.show_editing_tools(selected),
            )
            tools_layout.addWidget(button)
            self.editing_buttons.append(button)
        advanced_layout.addWidget(tools_card)

        subject_card, subject_layout = self._card("subject_title", "subject_hint")
        self.subject_buttons = [
            self._button("subject_blur_open", lambda: self.show_ai_tools("blur")),
            self._button("subject_open", lambda: self.show_ai_tools("color_pop")),
        ]
        for button in self.subject_buttons:
            subject_layout.addWidget(button)
        advanced_layout.addWidget(subject_card)
        for card in (ai_card, mask_card, adjustments_card, shape_card):
            advanced_layout.addWidget(card)
        panel_layout.addWidget(self.more_tools_panel)
        panel_layout.addStretch()
        self.more_tools_panel.hide()

        # Saving a reusable .laip project is still in File/Ctrl+S; the prominent
        # toolbar action for occasional users is exporting a finished picture.
        self.save_project_button.hide()

        self.editing_action = self._action("tools_title", self.show_editing_tools)
        self.editing_action.setShortcut(QKeySequence("Ctrl+E"))
        self.subject_action = self._action("subject_title", self.show_ai_tools)
        self.subject_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self._edit_menu.addSeparator()
        self._edit_menu.addActions([self.editing_action, self.subject_action])

    def _toggle_more_tools(self, checked: bool = False) -> None:
        self.more_tools_panel.setVisible(checked)
        self._sync_more_tools_label()

    def _sync_more_tools_label(self) -> None:
        self.more_tools_button.setText(
            self._t("quick_more_hide" if self.more_tools_button.isChecked() else "quick_more_show")
        )
        self.more_tools_button.setToolTip(self._t("quick_more_hint"))
        self.more_tools_button.setAccessibleDescription(self._t("quick_more_hint"))

    def _update_quick_hint(self) -> None:
        if self.is_busy:
            key = "quick_busy"
        elif self.mask_button.isChecked():
            key = "quick_mask_active"
        elif self.crop_button.isChecked():
            key = "quick_crop_active"
        elif self.original_button.isChecked():
            key = "quick_original_active"
        elif self.has_pending_adjustments:
            key = "quick_preview_active"
        elif self.document is None:
            key = "quick_empty"
        else:
            key = "quick_ready"
        self.quick_hint_label.setText(self._t(key))

    def set_language(self, language: str) -> None:
        super().set_language(language)
        if hasattr(self, "more_tools_button"):
            self._sync_more_tools_label()
            self._update_quick_hint()

    def _update_state(self) -> None:
        super()._update_state()
        if not hasattr(self, "quick_buttons"):
            return
        enabled = self._editable() and not self.crop_button.isChecked()
        for control, hint in zip(
            self.quick_buttons,
            ("quick_improve_hint", "quick_crop_hint", "quick_blur_hint", "quick_cutout_hint"),
        ):
            control.setEnabled(enabled)
            control.setToolTip(self._t(
                hint if enabled else "quick_need_photo" if self.document is None
                else "tools_unavailable"
            ))
            control.setAccessibleDescription(self._t(hint))
        for control in (*self.editing_buttons, self.editing_action):
            control.setEnabled(enabled)
            control.setToolTip(self._t("tools_hint" if enabled else "tools_unavailable"))
        for control in (*self.subject_buttons, self.subject_action):
            control.setEnabled(enabled)
            control.setToolTip(self._t("subject_hint" if enabled else "tools_unavailable"))
        # Never hide Apply/Discard or a live crop/brush workflow behind
        # a collapsed panel; otherwise the quick actions remain blocked.
        requires_completion = (
            self.has_pending_adjustments
            or self.crop_button.isChecked()
            or self.mask_button.isChecked()
        )
        if requires_completion and not self.more_tools_button.isChecked():
            self.more_tools_button.setChecked(True)
            self.more_tools_panel.show()
            self._sync_more_tools_label()
        self.more_tools_button.setEnabled(not requires_completion)
        self._update_quick_hint()

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
