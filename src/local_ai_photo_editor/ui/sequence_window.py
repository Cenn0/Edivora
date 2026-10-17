"""Beginner-focused ordered clip editor built over the existing Qt media preview.

The visual timeline is a reorderable row of clips. The existing precision
trim timeline edits the selected clip only. Rendering composes every clip in
the displayed order with one cancellable local FFmpeg process.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import uuid

from PySide6.QtCore import QProcess, QSignalBlocker, QTimer, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget,
)

from ..ai.models import available as image_model_available
from ..ai.voice import model_available as voice_model_available
from ..core.media import MIN_SELECTION_MS, ffmpeg_executable, validate_source
from ..core.media_project import (
    MAX_CLIPS, MediaClip, MediaSequence, PROJECT_EXTENSIONS,
    load_media_project, save_media_project, unavailable_media,
)
from ..core.media_sequence import SequenceExport, commit_sequence_export
from ..core.media_recovery import candidate_recovery, clear_recovery, write_recovery
from ..core.media_history import MediaHistory, same_content
from ..core.process_tree import kill_media_ai_process_group
from .media_strings import text
from .icons import IconButton
from .responsive import ElideLabel
from .video_strings import text as video_text
from .media_shell import resize_media_shell
from .media_window import MediaWindow, clock


class SequenceWindow(MediaWindow):
    """A simple single-lane clip arrangement; not a multitrack NLE."""

    def __init__(self, kind: str, compiled_executable: str | None = None) -> None:
        self.clips: list[MediaClip] = []
        self.active_id: str | None = None
        self._project_file: Path | None = None
        self._dirty = False
        self._relink_unsaved = False
        self._recovery_pending = False
        self._history_restoring = False
        self._export_progress_buffer = bytearray()
        self._ui_ready = False
        self._loading = False
        self._pending_new: Path | None = None
        self._pending_existing: str | None = None
        self._sequence_plan: SequenceExport | None = None
        self._sequence_temp: Path | None = None
        self._export_cancelled = False
        self._ai_process: QProcess | None = None
        self._ai_job_folder: tempfile.TemporaryDirectory | None = None
        self._ai_action: str | None = None
        self._ai_target: Path | None = None
        self._ai_clip_id: str | None = None
        self._ai_cancel_requested = False
        super().__init__(kind, compiled_executable)
        self._install_sequence_controls()
        self.player.hasAudioChanged.connect(self._audio_presence_changed)
        self.player.errorOccurred.connect(self._sequence_preview_error)
        if self.normalize is not None:
            self.normalize.toggled.connect(lambda _: self._mark_changed())
            self.fade_in.valueChanged.connect(lambda _: self._mark_changed())
            self.fade_out.valueChanged.connect(lambda _: self._mark_changed())
        self._ui_ready = True
        self._saved_state = self._snapshot()
        self._history = MediaHistory(self._saved_state)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(15_000)
        self._autosave_timer.timeout.connect(self._autosave_recovery)
        self._autosave_timer.start()
        self._update_enabled()

    def _install_sequence_controls(self) -> None:
        stage = self.timeline.parentWidget()
        stage_layout = stage.layout()
        position = stage_layout.indexOf(self.timeline)
        lane = QFrame()
        lane.setObjectName("toolCard")
        lane_layout = QVBoxLayout(lane)
        lane_layout.setContentsMargins(8, 6, 8, 6)
        lane_layout.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(3)
        self.clip_heading = QLabel()
        self.clip_heading.setObjectName("sectionTitle")
        head.addWidget(self.clip_heading)
        head.addStretch()
        for attribute, key, callback in (
            ("add_button", "clip_add", self.open_file),
            ("remove_button", "clip_remove", self.remove_selected),
            ("up_button", "clip_up", lambda: self.move_selected(-1)),
            ("down_button", "clip_down", lambda: self.move_selected(1)),
            ("duplicate_button", "clip_duplicate", self.duplicate_selected),
            ("split_button", "clip_split", self.split_selected),
        ):
            button = IconButton(key=key)
            button.setObjectName("timelineAction")
            button.setCompact(True)
            button.clicked.connect(callback)
            setattr(self, attribute, button)
            head.addWidget(button)
        lane_layout.addLayout(head)
        self.clip_list = QListWidget()
        self.clip_list.setObjectName("clipTimeline")
        self.clip_list.setMinimumWidth(0)
        self.clip_list.setFixedHeight(80)
        self.clip_list.setFlow(QListWidget.Flow.LeftToRight)
        self.clip_list.setWrapping(False)
        self.clip_list.setDragEnabled(True)
        self.clip_list.setAcceptDrops(True)
        self.clip_list.setDropIndicatorShown(True)
        self.clip_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.clip_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.clip_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.clip_list.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.clip_list.currentRowChanged.connect(self._select_list_row)
        self.clip_list.model().rowsMoved.connect(self._reorder_from_widget)
        lane_layout.addWidget(self.clip_list)
        stage_layout.insertWidget(position, lane)

        self.project_heading = ElideLabel()
        self.project_heading.setObjectName("sectionTitle")
        project_layout = self.project_tools_layout
        project_layout.insertWidget(0, self.project_heading)
        self.open_project_button = IconButton(key="media_project_open")
        self.open_project_button.clicked.connect(self.open_media_project)
        self.save_project_button = IconButton(key="media_project_save")
        self.save_project_button.setCompact(True)
        self.save_project_button.clicked.connect(self.save_media_project)
        self.save_as_button = IconButton(key="media_project_save_as")
        self.save_as_button.clicked.connect(self.save_media_project_as)
        project_layout.insertWidget(1, self.open_project_button)
        project_layout.insertWidget(2, self.save_as_button)
        self.header_layout.insertWidget(self.header_layout.indexOf(self.export_button), self.save_project_button)
        self.ai_button = IconButton(key="ai_voice" if self.kind == "audio" else "ai_video_frame")
        self.ai_button.setObjectName("quickAiAction")
        self.ai_button.clicked.connect(self.start_local_ai)
        target = self.audio_tools_layout if self.kind == "audio" else self.picture_tools_layout
        target.insertWidget(target.count() - 1, self.ai_button)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, activated=self.open_media_project)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_media_project)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self.save_media_project_as)
        self.undo_button = IconButton(icon_name="undo")
        self.redo_button = IconButton(icon_name="redo")
        for button, callback in ((self.redo_button, self.redo_edit), (self.undo_button, self.undo_edit)):
            button.setCompact(True)
            button.setObjectName("timelineAction")
            button.clicked.connect(callback)
            self.playback_layout.insertWidget(0, button)
        QShortcut(QKeySequence.StandardKey.Undo, self, activated=self.undo_edit)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self.redo_edit)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.redo_edit)
        self.video_size = None
        self.enhance_button = None
        if self.kind == "video":
            self.enhance_button = IconButton(icon_name="adjust")
            self.enhance_button.setObjectName("quickAction")
            self.enhance_button.clicked.connect(self.enhance_video)
            self.picture_tools_layout.insertWidget(0, self.enhance_button)
            self.video_size = QComboBox()
            self.video_size.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            self.video_size.setMinimumContentsLength(10)
            self.video_size.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.video_size.addItem("", "hd")
            self.video_size.addItem("", "full_hd")
            project_layout.insertWidget(3, self.video_size)
            self.source_preview_hint = QLabel()
            self.source_preview_hint.setTextFormat(Qt.TextFormat.PlainText)
            self.source_preview_hint.setWordWrap(True)
            self.source_preview_hint.setObjectName("muted")
            self.picture_tools_layout.insertWidget(1, self.source_preview_hint)
        for button in (self.open_project_button, self.save_as_button, self.ai_button, self.enhance_button):
            if button is not None:
                button.setFitToWidth()
        self.language_combo.currentIndexChanged.connect(self._translate_sequence)
        self._translate_sequence()
        self._refresh_clips()
        resize_media_shell(self)

    def _translate_sequence(self) -> None:
        def key(k: str) -> str:
            return text(self.language, k)
        for button, name in (
            (self.add_button, "clip_add"), (self.remove_button, "clip_remove"),
            (self.up_button, "clip_up"), (self.down_button, "clip_down"),
            (self.split_button, "clip_split"), (self.duplicate_button, "clip_duplicate"),
            (self.open_project_button, "media_project_open"),
            (self.save_project_button, "media_project_save"),
            (self.save_as_button, "media_project_save_as"),
        ):
            button.setText(key(name))
        self.undo_button.setText(video_text(self.language, "undo") + " (Ctrl+Z)")
        self.redo_button.setText(video_text(self.language, "redo") + " (Ctrl+Shift+Z)")
        if self.enhance_button is not None:
            self.enhance_button.setText(video_text(self.language, "enhance"))
            self.source_preview_hint.setText(video_text(self.language, "source_preview"))
            self.video_size.setAccessibleName(video_text(self.language, "size"))
            self.video_size.setToolTip(video_text(self.language, "size_hint"))
            for index, profile in enumerate(("hd", "full_hd")):
                self.video_size.setItemText(index, video_text(self.language, profile))
        self.clip_heading.setText(key("clips_short"))
        self.clip_heading.setToolTip(key("clip_lane"))
        self.project_heading.setText(key("project_title"))
        self.ai_button.setText(key("ai_voice" if self.kind == "audio" else "ai_video_frame"))
        self.clip_list.setAccessibleName(key("clip_lane"))
        self.clip_list.setToolTip(key("clip_tip"))
        self._refresh_clips()

    def _is_busy(self) -> bool:
        return super()._is_busy() or self._ai_process is not None

    def _valid_selection(self) -> bool:
        # Master audio fades affect the *assembled sequence*, not just the
        # currently selected source clip. The sequence validator checks total.
        if self.source is None or self.duration_ms <= 0:
            return False
        start = round(self.start_spin.value() * 1000)
        end = round(self.end_spin.value() * 1000)
        return 0 <= start < end <= self.duration_ms and end - start >= MIN_SELECTION_MS

    def _sequence_preview_error(self, *_args: object) -> None:
        if self._pending_new is not None or self._pending_existing is not None:
            self._pending_new = None
            self._pending_existing = None
            self._loading = False
            self._update_enabled()

    def _update_enabled(self) -> None:
        super()._update_enabled()
        if not getattr(self, "_ui_ready", False):
            return
        busy = self._is_busy()
        has = self._selected_index() is not None and self.source is not None
        ready = has and self.duration_ms > 0 and not busy and not self._loading
        # The button in the original toolbar should render the full sequence.
        self.export_button.setEnabled(ready and self._can_render())
        self.export_second.setEnabled(ready and self._can_render())
        self.add_button.setEnabled(not busy and len(self.clips) < MAX_CLIPS)
        self.open_project_button.setEnabled(not busy)
        self.save_project_button.setEnabled(not busy and bool(self.clips))
        self.save_as_button.setEnabled(not busy and bool(self.clips))
        self.remove_button.setEnabled(ready)
        self.duplicate_button.setEnabled(ready and len(self.clips) < MAX_CLIPS)
        self.split_button.setEnabled(ready and len(self.clips) < MAX_CLIPS)
        idx = self._selected_index()
        self.up_button.setEnabled(ready and idx is not None and idx > 0)
        self.down_button.setEnabled(ready and idx is not None and idx < len(self.clips) - 1)
        self.clip_list.setEnabled(not busy)
        if self.enhance_button is not None:
            self.enhance_button.setEnabled(ready)
            self.video_size.setEnabled(not busy)
        history_ready = not busy and not self._loading
        self.undo_button.setEnabled(history_ready and self._history.can_undo)
        self.redo_button.setEnabled(history_ready and self._history.can_redo)
        self.ai_button.setEnabled(
            ready and (voice_model_available() if self.kind == "audio" else image_model_available())
        )
        self.ai_button.setToolTip(
            self._t("ai_ready" if self.ai_button.isEnabled() else "ai_unavailable")
        )

    def _can_render(self) -> bool:
        try:
            self._snapshot().validated()
            return self._valid_selection()
        except (OSError, ValueError):
            return False

    def _selected_index(self) -> int | None:
        for index, clip in enumerate(self.clips):
            if clip.id == self.active_id:
                return index
        return None

    def _snapshot(self) -> MediaSequence:
        return MediaSequence(
            self.kind, tuple(self.clips), self.active_id,
            self.normalize.isChecked() if self.normalize is not None else False,
            round(self.fade_in.value() * 1000) if self.fade_in is not None else 0,
            round(self.fade_out.value() * 1000) if self.fade_out is not None else 0,
        )

    def _mark_changed(self, key: str | None = None) -> None:
        if self._history_restoring:
            return
        self._dirty = True
        if hasattr(self, "_history"):
            self._history.record(self._snapshot(), key)
            self._dirty = self._relink_unsaved or self._recovery_pending or not same_content(self._snapshot(), self._saved_state)
            self.undo_button.setEnabled(not self._is_busy() and not self._loading and self._history.can_undo)
            self.redo_button.setEnabled(not self._is_busy() and not self._loading and self._history.can_redo)
        self._update_project_heading()

    def undo_edit(self) -> None:
        if self._is_busy() or self._loading or not self._history.can_undo:
            return
        if self._history_sources_available(-1):
            self._restore_history(self._history.undo())

    def redo_edit(self) -> None:
        if self._is_busy() or self._loading or not self._history.can_redo:
            return
        if self._history_sources_available(1):
            self._restore_history(self._history.redo())

    def _history_sources_available(self, direction: int) -> bool:
        try:
            for clip in self._history.candidate(direction).clips:
                clip.validated(self.kind)
            return True
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self._t("error"), str(exc))
            return False

    def _restore_history(self, state: MediaSequence) -> None:
        self._history_restoring = True
        self._cancel_waveform()
        self.player.pause()
        self._pending_new = self._pending_existing = None
        self.clips = list(state.clips)
        if self.normalize is not None:
            with QSignalBlocker(self.normalize), QSignalBlocker(self.fade_in), QSignalBlocker(self.fade_out):
                self.normalize.setChecked(state.normalize)
                self.fade_in.setValue(state.fade_in_ms / 1000)
                self.fade_out.setValue(state.fade_out_ms / 1000)
        if self.clips:
            selected = next((c for c in self.clips if c.id == state.selected_id), self.clips[0])
            self._preview_clip(selected)
        else:
            self._loading = True
            self.player.setSource(QUrl())
            self.source, self.active_id, self.duration_ms = None, None, 0
            self._loading = False
            self.timeline.set_duration(0)
            self.file_label.setText(self._t(f"empty_{self.kind}"))
            self._refresh_clips()
        self._history_restoring = False
        self._dirty = self._relink_unsaved or self._recovery_pending or not same_content(self._snapshot(), self._saved_state)
        self._update_project_heading()
        self._update_enabled()

    def enhance_video(self) -> None:
        index = self._selected_index()
        if self.kind != "video" or index is None or self._is_busy() or not self._capture_selected():
            return
        from .video_dialog import VideoEnhancementDialog
        self.player.pause()
        protected = tuple(c.source for c in self.clips)
        if self._project_file is not None:
            protected += (self._project_file,)
        dialog = VideoEnhancementDialog(self.clips[index], self.player.position(), self.language, protected, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_clip is not None:
            self.clips[index] = dialog.result_clip
            self._mark_changed()
            self._preview_clip(self.clips[index])
        dialog.deleteLater()

    def _update_project_heading(self) -> None:
        if not getattr(self, "_ui_ready", False):
            return
        label = text(self.language, "project_title")
        if self._project_file is not None:
            label += " · " + self._project_file.name
        if self._dirty:
            label += " *"
        self.project_heading.setText(label)

    def _capture_selected(self) -> bool:
        if self._loading or self.source is None:
            return True
        idx = self._selected_index()
        if idx is None:
            return True
        clip = self.clips[idx]
        # Reject invalid intermediate numeric edits instead of silently
        # losing them during a workspace/clip switch.
        start = round(self.start_spin.value() * 1000)
        end = round(self.end_spin.value() * 1000)
        if not (0 <= start < end <= self.duration_ms + 1 and end - start >= MIN_SELECTION_MS):
            return False
        changed = replace(clip, start_ms=start, end_ms=min(end, clip.duration_ms),
                          volume_percent=self.volume.value(),
                          mute=self.mute.isChecked() if self.mute is not None else False)
        if changed != clip:
            self.clips[idx] = changed
            self._mark_changed(key=clip.id)
            self._refresh_clips()
        return True

    def _refresh_clips(self) -> None:
        if not hasattr(self, "clip_list"):
            return
        with QSignalBlocker(self.clip_list):
            self.clip_list.clear()
            for index, clip in enumerate(self.clips):
                title = (
                    f"{index + 1:02d} · {clip.source.name[:24]}\n"
                    f"{clock(clip.start_ms)} – {clock(clip.end_ms)}"
                )
                item = QListWidgetItem(title)
                item.setData(Qt.ItemDataRole.UserRole, clip.id)
                item.setToolTip(f"{clip.source.name} · {clock(clip.length_ms)}")
                self.clip_list.addItem(item)
                if clip.id == self.active_id:
                    self.clip_list.setCurrentItem(item)
        self._update_project_heading()

    def _reorder_from_widget(self, *_args: object) -> None:
        if self._loading or self._is_busy():
            return
        ids = [self.clip_list.item(i).data(Qt.ItemDataRole.UserRole)
               for i in range(self.clip_list.count())]
        if len(ids) != len(self.clips) or len(set(ids)) != len(ids):
            self._refresh_clips()
            return
        by_id = {c.id: c for c in self.clips}
        if set(ids) != set(by_id):
            self._refresh_clips()
            return
        self.clips = [by_id[uid] for uid in ids]
        self._mark_changed()
        self._refresh_clips()

    def _select_list_row(self, row: int) -> None:
        if self._loading or not 0 <= row < len(self.clips):
            return
        new_id = self.clip_list.item(row).data(Qt.ItemDataRole.UserRole)
        if new_id == self.active_id or self._is_busy():
            return
        if not self._capture_selected():
            QMessageBox.warning(self, self._t("error"), self._t("invalid_selection"))
            self._refresh_clips()
            return
        clip = next((c for c in self.clips if c.id == new_id), None)
        if clip is not None:
            self._preview_clip(clip)

    def _preview_clip(self, clip: MediaClip) -> None:
        self.active_id = clip.id
        if hasattr(self, "_history"):
            self._history.select(clip.id)
        self._pending_existing = clip.id
        self._pending_new = None
        self._loading = True
        super().open_path(clip.source)
        self._refresh_clips()

    def _duration_changed(self, duration: int) -> None:
        if not hasattr(self, "clips"):
            super()._duration_changed(duration)
            return
        if duration <= 0:
            super()._duration_changed(duration)
            return
        self._loading = True
        super()._duration_changed(duration)
        if self._pending_new is not None:
            clip = MediaClip.create(
                self.kind, self._pending_new, int(duration),
                has_audio=True if self.kind == "audio" else bool(self.player.hasAudio()),
            )
            self.clips.append(clip)
            self.active_id = clip.id
            self._pending_new = None
            self._mark_changed()
        if self._pending_existing is not None:
            self.active_id = self._pending_existing
            self._pending_existing = None
        idx = self._selected_index()
        if idx is not None:
            clip = self.clips[idx]
            with QSignalBlocker(self.start_spin), QSignalBlocker(self.end_spin):
                self.start_spin.setValue(clip.start_ms / 1000)
                self.end_spin.setValue(min(clip.end_ms, duration) / 1000)
            with QSignalBlocker(self.volume):
                self.volume.setValue(clip.volume_percent)
            self._volume_changed(clip.volume_percent)
            if self.mute is not None:
                with QSignalBlocker(self.mute):
                    self.mute.setChecked(clip.mute)
                self._mute_changed(clip.mute)
            self.timeline.set_range(clip.start_ms, clip.end_ms)
        self._loading = False
        self._refresh_clips()
        self._update_enabled()

    def _audio_presence_changed(self, has_audio: bool) -> None:
        idx = self._selected_index()
        if self.kind != "video" or idx is None or self._loading:
            return
        clip = self.clips[idx]
        if clip.has_audio != bool(has_audio):
            self.clips[idx] = replace(clip, has_audio=bool(has_audio))
            self._mark_changed()
            self._refresh_clips()

    def _selection_changed(self, *_args: object) -> None:
        super()._selection_changed(*_args)
        if self._ui_ready and not self._loading:
            self._capture_selected()

    def _volume_changed(self, value: int) -> None:
        super()._volume_changed(value)
        if self._ui_ready and not self._loading:
            self._capture_selected()

    def _mute_changed(self, muted: bool) -> None:
        super()._mute_changed(muted)
        if self._ui_ready and not self._loading:
            self._capture_selected()

    def open_path(self, path: str | Path) -> None:
        if self._is_busy() or len(self.clips) >= MAX_CLIPS:
            return
        try:
            source = validate_source(path, self.kind)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self._t("error"), str(exc))
            return
        if not self._capture_selected():
            QMessageBox.warning(self, self._t("error"), self._t("invalid_selection"))
            return
        self._pending_new = source
        self._pending_existing = None
        self._loading = True
        super().open_path(source)

    def add_media(self) -> None:
        if not self._is_busy():
            super().open_file()

    def remove_selected(self) -> None:
        idx = self._selected_index()
        if idx is None or self._is_busy():
            return
        self.clips.pop(idx)
        self.active_id = None
        self._mark_changed()
        if self.clips:
            self._preview_clip(self.clips[min(idx, len(self.clips) - 1)])
        else:
            self.player.stop()
            self.player.setSource(QUrl())
            self.source = None
            self.duration_ms = 0
            self._loading = False
            self.timeline.set_duration(0)
            self.file_label.setText(self._t(f"empty_{self.kind}"))
            self._refresh_clips()
            self._update_enabled()

    def move_selected(self, delta: int) -> None:
        idx = self._selected_index()
        if idx is None or self._is_busy() or not 0 <= idx + delta < len(self.clips):
            return
        self._capture_selected()
        item = self.clips.pop(idx)
        self.clips.insert(idx + delta, item)
        self._mark_changed()
        self._refresh_clips()
        self._update_enabled()

    def duplicate_selected(self) -> None:
        idx = self._selected_index()
        if idx is None or self._is_busy() or len(self.clips) >= MAX_CLIPS:
            return
        if not self._capture_selected():
            return
        duplicated = replace(self.clips[idx], id=uuid.uuid4().hex)
        self.clips.insert(idx + 1, duplicated)
        self._mark_changed()
        self._preview_clip(duplicated)

    def split_selected(self) -> None:
        idx = self._selected_index()
        if idx is None or self._is_busy() or len(self.clips) >= MAX_CLIPS:
            return
        if not self._capture_selected():
            return
        clip = self.clips[idx]
        at = self.player.position()
        if not clip.start_ms + MIN_SELECTION_MS <= at <= clip.end_ms - MIN_SELECTION_MS:
            QMessageBox.information(self, self._t("clip_split"), self._t("split_hint"))
            return
        first = replace(clip, end_ms=at)
        second = replace(clip, id=uuid.uuid4().hex, start_ms=at)
        self.clips[idx:idx + 1] = [first, second]
        self._mark_changed()
        self._preview_clip(second)

    def _confirm_unsaved(self) -> bool:
        """Require an explicit Save / Discard / Cancel decision before data loss."""
        if not self._dirty:
            return True
        prompt = QMessageBox(self)
        prompt.setIcon(QMessageBox.Icon.Warning)
        prompt.setWindowTitle(self._t("project_title"))
        prompt.setText(self._t("media_project_unsaved"))
        prompt.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        can_save = bool(self.clips) and not self._is_busy()
        prompt.button(QMessageBox.StandardButton.Save).setText(self._t("media_project_save"))
        prompt.button(QMessageBox.StandardButton.Save).setEnabled(can_save)
        prompt.button(QMessageBox.StandardButton.Discard).setText(self._t("media_project_discard"))
        prompt.button(QMessageBox.StandardButton.Cancel).setText(self._t("cancel"))
        prompt.setDefaultButton(
            QMessageBox.StandardButton.Save if can_save else QMessageBox.StandardButton.Cancel
        )
        prompt.setEscapeButton(QMessageBox.StandardButton.Cancel)
        answer = QMessageBox.StandardButton(prompt.exec())
        if answer == QMessageBox.StandardButton.Save:
            # Never abandon the current project if Save As is cancelled or IO fails.
            return can_save and self.save_media_project()
        return answer == QMessageBox.StandardButton.Discard

    def _load_with_relinks(self, path: str | Path) -> tuple[MediaSequence, bool] | None:
        """Load a project only after *all* replacements pass exact source checks.

        Cancelled selection returns None without altering the active editor.
        Malformed project references never bypass the strict loader.
        """
        try:
            return load_media_project(path), False
        except (OSError, ValueError):
            unavailable = unavailable_media(path)
            if not unavailable:
                raise
        chosen: dict[tuple[str, str], Path] = {}
        replacements: dict[str, Path] = {}
        file_filter = ("Video (*.mp4 *.mov *.mkv *.webm *.avi *.m4v)"
                       if self.kind == "video" else
                       "Audio (*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus)")
        for missing in unavailable:
            key = (missing.reference, missing.sample_sha256)
            if key not in chosen:
                selected, _ = QFileDialog.getOpenFileName(
                    self, self._t("media_relink_choose", name=missing.name),
                    str(Path(path).parent), file_filter,
                )
                if not selected:
                    return None
                chosen[key] = Path(selected)
            replacements[missing.clip_id] = chosen[key]
        sequence = load_media_project(path, replacements=replacements)
        if sequence.kind != self.kind:
            raise ValueError("This project belongs to a different editor.")
        return sequence, True

    def _autosave_recovery(self) -> None:
        """Checkpoint only a changed, already saved and validated project."""
        if (self._project_file is None or not self._dirty or self._is_busy()
                or self._loading or not self.clips):
            return
        try:
            # Never write over the authoritative project. This operation is
            # small (manifest + sampled fingerprints) and atomically replaces
            # only its derived local sidecar.
            write_recovery(self._snapshot().validated(), self._project_file)
        except (OSError, ValueError):
            # The main project is unchanged; make failed crash protection
            # visible rather than claiming that autosave succeeded.
            self._set_status("media_recovery_failed")

    def open_media_project(self) -> None:
        if self._is_busy() or not self._confirm_unsaved():
            return
        kinds = PROJECT_EXTENSIONS[self.kind]
        path, _ = QFileDialog.getOpenFileName(
            self, self._t("media_project_open"), "", f"Edivora (*{kinds})"
        )
        if not path:
            return
        restored = False
        load_path = path
        try:
            try:
                recovery = candidate_recovery(path)
            except (OSError, ValueError):
                # A corrupt checkpoint may not prevent the last explicit
                # Save from loading. It is never applied without consent.
                recovery = None
                QMessageBox.warning(self, self._t("error"), self._t("media_recovery_invalid"))
            if recovery is not None and QMessageBox.question(
                self, self._t("media_recovery_title"),
                self._t("media_recovery_prompt"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes:
                load_path = str(recovery.checkpoint)
                restored = True
            outcome = self._load_with_relinks(load_path)
            if outcome is None:
                return
            sequence, relinked = outcome
            if sequence.kind != self.kind:
                raise ValueError("This project belongs to a different editor.")
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, self._t("error"), str(exc))
            return
        self._cancel_waveform()
        self.clips = list(sequence.clips)
        self.active_id = None
        self._project_file = Path(path)
        self._relink_unsaved = relinked
        self._recovery_pending = restored
        self._dirty = relinked or restored
        if self.normalize is not None:
            self.normalize.setChecked(sequence.normalize)
            self.fade_in.setValue(sequence.fade_in_ms / 1000)
            self.fade_out.setValue(sequence.fade_out_ms / 1000)
        selection = next(
            (c for c in self.clips if c.id == sequence.selected_id), self.clips[0]
        )
        self._preview_clip(selection)
        self._dirty = relinked or restored
        self._saved_state = self._snapshot()
        self._history.reset(self._saved_state)
        self._update_project_heading()
        self._update_enabled()

    def save_media_project(self) -> bool:
        if self._is_busy() or not self.clips:
            return False
        if self._project_file is None:
            return self.save_media_project_as()
        return self._save_to(self._project_file)

    def save_media_project_as(self) -> bool:
        if self._is_busy() or not self.clips:
            return False
        extension = PROJECT_EXTENSIONS[self.kind]
        suggested = str(self._project_file or
                        (self.clips[0].source.parent / f"edivora-project{extension}"))
        path, _ = QFileDialog.getSaveFileName(
            self, self._t("media_project_save_as"), suggested, f"Edivora (*{extension})"
        )
        if not path:
            return False
        dest = Path(path)
        if not dest.suffix:
            dest = dest.with_suffix(extension)
        return self._save_to(dest)

    def _save_to(self, path: Path) -> bool:
        if self._is_busy():
            return False
        if not self._capture_selected():
            QMessageBox.warning(self, self._t("error"), self._t("invalid_selection"))
            return False
        previous_project = self._project_file
        try:
            save_media_project(self._snapshot(), path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self._t("error"), str(exc))
            return False
        self._project_file = Path(path)
        self._relink_unsaved = False
        self._recovery_pending = False
        self._dirty = False
        self._saved_state = self._snapshot()
        self._history.checkpoint()
        self._set_status("media_project_saved", name=path.name)
        for cleared in (path, previous_project):
            if cleared is None:
                continue
            try:
                clear_recovery(cleared)
            except (OSError, ValueError):
                # Explicit Save did succeed. Keep working data, but surface a
                # cleanup warning so an old recovery is not mistaken as valid.
                self._set_status("media_recovery_failed")
        self._update_project_heading()
        return True

    def _sequence_export(self, destination: Path) -> SequenceExport:
        if not self._capture_selected():
            raise ValueError(self._t("invalid_selection"))
        return SequenceExport(self._snapshot(), destination,
            self.video_size.currentData() if self.video_size is not None else "hd").validated()

    def export_file(self) -> None:
        if self._is_busy() or not self.clips or not self._can_render():
            return
        extension = ".mp4" if self.kind == "video" else ".wav"
        filename = self._project_file.stem if self._project_file else self.clips[0].source.stem
        suggested = self.clips[0].source.parent / (filename + "-edivora" + extension)
        choices = "MP4 (*.mp4)" if self.kind == "video" else "WAV (*.wav);;MP3 (*.mp3)"
        selected, preferred = QFileDialog.getSaveFileName(
            self, self._t("export_title"), str(suggested), choices
        )
        if not selected:
            return
        dest = Path(selected)
        if not dest.suffix:
            dest = dest.with_suffix(".mp3" if "MP3" in preferred else extension)
        try:
            plan = self._sequence_export(dest)
            engine = ffmpeg_executable(self._compiled_executable)
            if dest.exists() and QMessageBox.question(
                self, self._t("export_title"), self._t("overwrite"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                return
            temporary = plan.temp_output()
            arguments = plan.ffmpeg_arguments(temporary)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self._t("error"), str(exc))
            return
        self.stop_playback()
        self._sequence_plan = plan
        self._sequence_temp = temporary
        self._export_cancelled = False
        self._export_error.clear()
        self._export_progress_buffer.clear()
        process = QProcess(self)
        self._export_process = process
        process.setProgram(engine)
        process.setArguments(arguments)
        process.readyReadStandardError.connect(self._collect_error)
        process.readyReadStandardOutput.connect(self._sequence_progress)
        process.finished.connect(lambda code, status, p=process: self._sequence_finished(p, code))
        process.errorOccurred.connect(
            lambda error, p=process: self._sequence_start_error(p, error)
        )
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.show()
        self.cancel_button.show()
        self._set_status("media_sequence_render")
        self._update_enabled()
        process.start()

    def _sequence_progress(self) -> None:
        if self._export_process is None or self._sequence_plan is None:
            return
        self._export_progress_buffer.extend(bytes(self._export_process.readAllStandardOutput()))
        del self._export_progress_buffer[:-8192]
        while b"\n" in self._export_progress_buffer:
            line, _, rest = self._export_progress_buffer.partition(b"\n")
            self._export_progress_buffer = bytearray(rest)
            if line.startswith(b"out_time_us="):
                try:
                    elapsed = max(0, int(line.split(b"=", 1)[1]))
                    value = min(99, round(elapsed / (self._sequence_plan.sequence.length_ms * 10)))
                    self.progress.setValue(value)
                except ValueError:
                    pass

    def _sequence_start_error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if process is self._export_process and error == QProcess.ProcessError.FailedToStart:
            self._sequence_finished(process, -1)

    def _sequence_finished(self, process: QProcess, code: int) -> None:
        if process is not self._export_process:
            return
        self._collect_error()
        plan, temporary = self._sequence_plan, self._sequence_temp
        self._export_process = None
        self._sequence_plan = None
        self._sequence_temp = None
        process.deleteLater()
        self.progress.hide()
        self.cancel_button.hide()
        try:
            if self._export_cancelled:
                self._set_status("cancelled")
            elif code != 0 or plan is None or temporary is None:
                detail = self._export_error.decode("utf-8", "replace").strip()[-300:]
                raise RuntimeError(detail or self._t("failed"))
            else:
                commit_sequence_export(plan, temporary)
                self._set_status("done", name=plan.destination.name)
        except (OSError, RuntimeError, ValueError) as exc:
            self._set_status("failed")
            QMessageBox.warning(self, self._t("error"), str(exc))
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            self._update_enabled()

    def _media_ai_command(self, operation: str, directory: Path) -> tuple[str, list[str]]:
        from ..__main__ import media_job_command

        return media_job_command(operation, directory)

    def start_local_ai(self) -> None:
        idx = self._selected_index()
        if idx is None or self._is_busy() or not self._capture_selected():
            return
        clip = self.clips[idx]
        operation = "voice" if self.kind == "audio" else "frame"
        target: Path | None = None
        if operation == "voice":
            if not voice_model_available():
                QMessageBox.warning(self, self._t("error"), self._t("ai_unavailable"))
                return
            if clip.length_ms > 15 * 60 * 1000:
                QMessageBox.information(self, self._t("ai_voice"), self._t("ai_voice_limit"))
                return
            payload = {"source": str(clip.source.resolve()),
                       "start_ms": clip.start_ms, "end_ms": clip.end_ms}
        else:
            if not image_model_available():
                QMessageBox.warning(self, self._t("error"), self._t("ai_unavailable"))
                return
            picked, _ = QFileDialog.getSaveFileName(
                self, self._t("ai_video_frame"), str(clip.source.with_suffix("").with_name(
                    clip.source.stem + "-ai-frame.png"
                )), "PNG (*.png)"
            )
            if not picked:
                return
            target = Path(picked)
            if not target.suffix:
                target = target.with_suffix(".png")
            if target.exists() and QMessageBox.question(
                self, self._t("ai_video_frame"), self._t("overwrite"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                return
            payload = {"source": str(clip.source.resolve()),
                       "at_ms": min(self.player.position(), clip.duration_ms),
                       "destination": str(target)}
        folder = tempfile.TemporaryDirectory(prefix="edivora-media-ai-")
        workdir = Path(folder.name)
        (workdir / "request.json").write_text(json.dumps(payload), encoding="utf-8")
        program, args = self._media_ai_command(operation, workdir)
        process = QProcess(self)
        self._ai_process = process
        self._ai_job_folder = folder
        self._ai_action = operation
        self._ai_target = target
        self._ai_clip_id = clip.id
        self._ai_cancel_requested = False
        process.setProgram(program)
        process.setArguments(args)
        if os.name != "nt":
            # Qt >= 6.7 creates the session *before exec*: no start/cancel race.
            # Nested FFmpeg inherits this group, unlike detached processes.
            process.setUnixProcessParameters(QProcess.UnixProcessFlag.CreateNewSession)
        process.finished.connect(lambda code, status, p=process: self._ai_finished(p, code))
        process.errorOccurred.connect(lambda err, p=process: self._ai_start_error(p, err))
        self.progress.setRange(0, 0)
        self.progress.show()
        self.cancel_button.show()
        self._set_status("ai_busy_media")
        self._update_enabled()
        process.start()

    def _ai_start_error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if process is self._ai_process and error == QProcess.ProcessError.FailedToStart:
            self._ai_finished(process, -1)

    def _ai_finished(self, process: QProcess, code: int) -> None:
        if process is not self._ai_process:
            return
        operation = self._ai_action
        clip_id = self._ai_clip_id
        folder = self._ai_job_folder
        self._ai_process = None
        self._ai_action = None
        self._ai_clip_id = None
        self._ai_job_folder = None
        process.deleteLater()
        self.progress.hide()
        self.cancel_button.hide()
        try:
            if self._ai_cancel_requested:
                self._set_status("cancelled")
                return
            if folder is None or code != 0:
                raise RuntimeError(self._t("ai_media_error"))
            file = Path(folder.name) / "result.json"
            if not file.is_file() or file.stat().st_size > 16384:
                raise ValueError("Invalid local AI result.")
            result = json.loads(file.read_text("utf-8"))
            if result.get("ok") is not True:
                raise RuntimeError(result.get("message", self._t("ai_media_error")))
            if operation == "voice":
                rows = result.get("segments", [])
                if result.get("too_many") or not isinstance(rows, list):
                    raise ValueError(self._t("ai_voice_too_many"))
                idx = next((i for i, c in enumerate(self.clips) if c.id == clip_id), None)
                if idx is None:
                    raise RuntimeError("The source clip changed during local inference.")
                clip = self.clips[idx]
                proposed = []
                for interval in rows:
                    if (not isinstance(interval, list) or len(interval) != 2
                            or any(type(v) is not int for v in interval)):
                        raise ValueError("Malformed voice detection interval.")
                    lo, hi = interval
                    if not clip.start_ms <= lo < hi <= clip.end_ms or hi - lo < MIN_SELECTION_MS:
                        raise ValueError("Voice detection returned an invalid region.")
                    proposed.append(replace(clip, id=uuid.uuid4().hex,
                                            start_ms=lo, end_ms=hi))
                if not proposed:
                    QMessageBox.information(self, self._t("ai_voice"), self._t("ai_voice_none"))
                elif len(self.clips) - 1 + len(proposed) > MAX_CLIPS:
                    QMessageBox.warning(self, self._t("error"), self._t("ai_voice_too_many"))
                elif QMessageBox.question(
                    self, self._t("ai_voice"),
                    self._t("ai_voice_confirm", count=len(proposed)),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                ) == QMessageBox.StandardButton.Yes:
                    self.clips[idx:idx + 1] = proposed
                    self._mark_changed()
                    self._preview_clip(proposed[0])
            else:
                self._set_status("ai_frame_done", name=str(result["name"]))
        except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
            if not self._ai_cancel_requested:
                QMessageBox.warning(self, self._t("error"), str(exc))
        finally:
            if folder is not None:
                folder.cleanup()
            self._update_enabled()

    def cancel_export(self) -> None:
        if self._ai_process is not None:
            process = self._ai_process
            self._ai_cancel_requested = True
            # On POSIX kill the verified new session, not just the Qt worker.
            # On Windows the worker's kill-on-close Job Object owns FFmpeg.
            try:
                killed_group = kill_media_ai_process_group(int(process.processId()))
            except OSError:
                killed_group = False
            if not killed_group:
                process.kill()
            process.waitForFinished(3000)
            if process.state() != QProcess.ProcessState.NotRunning:
                # Do not destroy the job directory while a worker still runs.
                return
            if self._ai_process is process:
                self._ai_finished(process, -9)
            self._set_status("cancelled")
            return
        if self._export_process is not None:
            process = self._export_process
            self._export_cancelled = True
            process.kill()
            process.waitForFinished(3000)
            if self._export_process is process:
                self._sequence_finished(process, -9)
            return

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._dirty and not self._confirm_unsaved():
            event.ignore()
            return
        if self._ai_process is not None:
            if QMessageBox.question(
                self, self._t("error"), self._t("close_processing"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.cancel_export()
            if self._ai_process is not None:
                event.ignore()
                return
        super().closeEvent(event)
        if event.isAccepted():
            # Qt Multimedia's Windows backend may otherwise retain an open
            # handle to the last clip during immediate project/test cleanup.
            self.player.setSource(QUrl())
            self.player.setAudioOutput(None)
            if self.kind == "video":
                self.player.setVideoOutput(None)
