"""Responsive shared media shell; playback and file operations stay in MediaWindow."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QProgressBar, QScrollArea, QSizePolicy, QSlider, QSplitter,
    QTabWidget, QVBoxLayout, QWidget,
)
from PySide6.QtMultimediaWidgets import QVideoWidget

from ..branding import app_icon
from .responsive import ElideLabel, VerticalScrollArea
from .trim_timeline import TrimTimeline


def inspector_page(window, key: str):
    page = QWidget()
    page.setObjectName("toolsPanel")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)
    scroll = VerticalScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(page)
    index = window.inspector_tabs.addTab(scroll, window._t(key))
    window._inspector_tab_keys.append((index, key))
    return layout


def build_media_shell(w):
    central = QWidget(w)
    w.setCentralWidget(central)
    root = QVBoxLayout(central)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    header = QFrame()
    header.setObjectName("topBar")
    w.header_layout = top = QHBoxLayout(header)
    top.setContentsMargins(12, 6, 12, 6)
    top.setSpacing(6)
    mark = QLabel()
    mark.setPixmap(app_icon().pixmap(32, 32))
    mark.setAccessibleName("Edivora")
    mark.setObjectName("brandMark")
    top.addWidget(mark)
    w.brand_label = w._label("suite", "appName")
    top.addWidget(w.brand_label)
    top.addWidget(w._label(w.kind, "workspaceName"))
    top.addStretch()
    w.local_badge = w._label("local", "localBadge")
    top.addWidget(w.local_badge)
    w.open_button = w._button("open", w.open_file)
    top.addWidget(w.open_button)
    w.export_button = w._button("export", w.export_file, "primary")
    top.addWidget(w.export_button)
    w.language_combo = QComboBox()
    w.language_combo.addItem("Deutsch", "de")
    w.language_combo.addItem("English", "en")
    w.language_combo.currentIndexChanged.connect(w._switch_language)
    top.addWidget(w.language_combo)
    root.addWidget(header)

    w.content_splitter = content = QSplitter(Qt.Orientation.Horizontal)
    content.setChildrenCollapsible(False)
    content.setHandleWidth(5)
    root.addWidget(content, 1)
    w.stage = stage = QFrame()
    stage.setObjectName("previewFrame")
    stage.setMinimumWidth(220)
    w.stage_layout = stage_layout = QVBoxLayout(stage)
    stage_layout.setContentsMargins(12, 10, 12, 10)
    stage_layout.setSpacing(6)
    w.file_label = ElideLabel()
    w.file_label.setObjectName("fileName")
    w._labels.append((w.file_label, f"empty_{w.kind}"))
    stage_layout.addWidget(w.file_label)
    if w.kind == "video":
        w.video_surface = QVideoWidget(stage)
        w.video_surface.setMinimumSize(0, 60)
        w.video_surface.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        w.player.setVideoOutput(w.video_surface)
        stage_layout.addWidget(w.video_surface, 1)
        w.wave_label = None
    else:
        w.wave_label = w._label("preview", "sectionTitle")
        w.wave_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w.wave_label.setMinimumSize(0, 60)
        w.wave_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        stage_layout.addWidget(w.wave_label, 1)
    playback = QHBoxLayout()
    w.playback_layout = playback
    w.play_button = w._button("play", w.toggle_play)
    w.stop_button = w._button("stop", w.stop_playback)
    playback.addWidget(w.play_button)
    playback.addWidget(w.stop_button)
    w.time_label = ElideLabel()
    w.time_label.setText("00:00:00 / 00:00:00")
    w.time_label.setObjectName("muted")
    playback.addWidget(w.time_label, 1)
    stage_layout.addLayout(playback)
    w.timeline = TrimTimeline(stage)
    w.timeline.rangeChanged.connect(w._timeline_changed)
    w.timeline.seekRequested.connect(w._seek_from_timeline)
    stage_layout.addWidget(w.timeline)
    w.timeline_help = w._label("timeline_hint", "muted", wrap=True)
    stage_layout.addWidget(w.timeline_help)
    content.addWidget(stage)

    w.inspector_tabs = QTabWidget()
    w.inspector_tabs.setObjectName("inspectorTabs")
    w.inspector_tabs.setMinimumWidth(300)
    w.inspector_tabs.setMaximumWidth(450)
    w.inspector_tabs.setUsesScrollButtons(True)
    w._inspector_tab_keys = []
    content.addWidget(w.inspector_tabs)
    range_layout = inspector_page(w, "trim_tab")
    range_layout.addWidget(w._label("trim", "sectionTitle"))
    range_layout.addWidget(w._label("trim_hint", "muted", wrap=True))
    form = QFormLayout()
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
    w.start_spin, w.end_spin = QDoubleSpinBox(), QDoubleSpinBox()
    for spin, key in ((w.start_spin, "start_time"), (w.end_spin, "end_time")):
        spin.setDecimals(3)
        spin.setSingleStep(.25)
        spin.setSuffix(" s")
        spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        spin.valueChanged.connect(w._selection_changed)
        label = w._label(key, wrap=True)
        label.setBuddy(spin)
        form.addRow(label, spin)
    range_layout.addLayout(form)
    markers = QHBoxLayout()
    w.mark_start_button = w._button("mark_start", w._mark_start_at_playhead, "quiet")
    w.mark_end_button = w._button("mark_end", w._mark_end_at_playhead, "quiet")
    markers.addWidget(w.mark_start_button)
    markers.addWidget(w.mark_end_button)
    range_layout.addLayout(markers)
    w.reset_range_button = w._button("reset_range", w._reset_range, "quiet")
    range_layout.addWidget(w.reset_range_button)
    w.edit_tools_layout = range_layout  # SequenceWindow adds enhancement actions here.
    range_layout.addStretch()

    w.picture_tools_layout = None
    if w.kind == "video":
        w.picture_tools_layout = inspector_page(w, "picture_tab")
        w.picture_tools_layout.addStretch()
    audio_layout = inspector_page(w, "audio")
    audio_layout.addWidget(w._label("audio", "sectionTitle"))
    w.volume_title = w._label("volume")
    audio_layout.addWidget(w.volume_title)
    volume_row = QHBoxLayout()
    w.volume = QSlider(Qt.Orientation.Horizontal)
    w.volume.setRange(0, 200)
    w.volume.setValue(100)
    w.volume.valueChanged.connect(w._volume_changed)
    w.volume_title.setBuddy(w.volume)
    volume_row.addWidget(w.volume)
    w.volume_label = QLabel("100 %")
    w.volume_label.setObjectName("sliderValue")
    volume_row.addWidget(w.volume_label)
    audio_layout.addLayout(volume_row)
    if w.kind == "video":
        w.mute = w._check("mute", w._mute_changed)
        audio_layout.addWidget(w.mute)
        w.normalize = w.fade_in = w.fade_out = None
    else:
        w.mute = None
        w.normalize = w._check("normalize", lambda _: w._update_enabled())
        audio_layout.addWidget(w.normalize)
        fades = QFormLayout()
        fades.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        w.fade_in, w.fade_out = QDoubleSpinBox(), QDoubleSpinBox()
        for spin, key in ((w.fade_in, "fade_in"), (w.fade_out, "fade_out")):
            spin.setDecimals(1)
            spin.setRange(0, 60)
            spin.setSingleStep(.5)
            spin.setSuffix(" s")
            spin.valueChanged.connect(w._selection_changed)
            label = w._label(key, wrap=True)
            label.setBuddy(spin)
            fades.addRow(label, spin)
        audio_layout.addLayout(fades)
    w.audio_tools_layout = audio_layout
    audio_layout.addStretch()
    w.project_tools_layout = project_layout = inspector_page(w, "project_tab")
    project_layout.addWidget(w._label(f"export_hint_{w.kind}", "muted", wrap=True))
    w.export_second = w._button("export", w.export_file, "primary")
    project_layout.addWidget(w.export_second)
    for button in (w.export_second, w.reset_range_button, w.mark_start_button, w.mark_end_button):
        button.setFitToWidth()
    project_layout.addWidget(w._label("codec_hint", "muted", wrap=True))
    project_layout.addStretch()
    content.setStretchFactor(0, 1)
    content.setStretchFactor(1, 0)
    content.setSizes([890, 330])

    footer = QFrame()
    footer.setObjectName("bottomBar")
    bottom = QHBoxLayout(footer)
    bottom.setContentsMargins(12, 6, 12, 6)
    w.status = ElideLabel()
    w.status.setObjectName("status")
    bottom.addWidget(w.status, 1)
    w.progress = QProgressBar()
    w.progress.setRange(0, 0)
    w.progress.setMaximumWidth(150)
    w.progress.hide()
    bottom.addWidget(w.progress)
    w.cancel_button = w._button("cancel", w.cancel_export)
    w.cancel_button.hide()
    bottom.addWidget(w.cancel_button)
    root.addWidget(footer)
    w._set_status("ready")


def resize_media_shell(w):
    if not hasattr(w, "inspector_tabs"):
        return
    narrow = w.width() < 1050
    short = w.height() < 660
    w.local_badge.setVisible(not narrow)
    w.brand_label.setVisible(w.width() >= 780)
    for button in (w.open_button, w.export_button):
        button.setCompact(narrow)
    for button in (w.play_button, w.stop_button, w.mark_start_button, w.mark_end_button):
        button.setCompact(narrow)
    w.timeline_help.setVisible(not short)
    w.stage_layout.setSpacing(4 if short else 8)
    w.stage_layout.setContentsMargins(10, 6 if short else 12, 10, 6 if short else 12)
    if hasattr(w, "save_project_button"):
        w.save_project_button.setCompact(True)
    if hasattr(w, "clip_list"):
        w.clip_list.setFixedHeight(62 if short else 80)
        for button in (w.add_button, w.remove_button, w.up_button, w.down_button,
                       w.duplicate_button, w.split_button):
            button.setCompact(True)
    # No widget is removed from its layout; scroll areas retain keyboard access.
