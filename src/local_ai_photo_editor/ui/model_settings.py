"""Single model-selection experience across Photo, Video and Audio editors.

Settings are stored locally via QSettings and passed as allowlisted model IDs
to detached worker processes. This dialog does not load neural networks.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QMessageBox, QVBoxLayout,
)

from ..ai.catalog import (
    SPECS, TASK_IMAGE, TASK_TRANSCRIBE, TASK_VOICE, TASKS,
    choose_model, detect_hardware, model_installed, recommended,
)
from .theme import stylesheet

LABELS = {
    "de": {
        TASK_IMAGE: "Foto und Video · Hintergrund/Freistellung",
        TASK_VOICE: "Audio · Sprachabschnitte erkennen",
        TASK_TRANSCRIBE: "Audio/Video · Sprache transkribieren",
        "title": "Lokale KI-Modelle",
        "hint": "Automatisch wählt das leistungsfähigste mitgelieferte Modell für die Aufgabe, das zu den verfügbaren Ressourcen passt. Größer bedeutet nicht immer besser.",
        "auto": "Automatisch (empfohlen)",
        "not_ready": "Nicht installiert / beschädigt",
        "installed": "Mitgeliefert",
        "capacity": "Ressourcenrichtwert",
        "hardware": "System: {memory:.1f} GiB RAM, {free:.1f} GiB frei, {cores} logische CPUs",
        "unknown": "RAM-Daten nicht verfügbar: konservative CPU-Auswahl.",
        "gpu": "Rechenweg: CPU (GPU-Beschleunigung ist in diesem Paket noch nicht freigegeben).",
        "automatic": "Automatische Wahl: {name}",
        "unavailable": "Kein geeignetes Modell im geprüften Paket verfügbar",
        "memory_note": "Manuelle Auswahl unterhalb der Empfehlung kann sehr langsam sein oder wegen Speichermangels fehlschlagen.",
        "override": "Diese Auswahl liegt unterhalb der Speicherempfehlung. Trotzdem speichern?",
        "confirm": "Speichern", "cancel": "Abbrechen",
    },
    "en": {
        TASK_IMAGE: "Photo and video · foreground/background",
        TASK_VOICE: "Audio · detect speech regions",
        TASK_TRANSCRIBE: "Audio/video · transcribe speech",
        "title": "Local AI models",
        "hint": "Automatic selects the highest-capability bundled model supported by your available resources for each task. Larger is not always better.",
        "auto": "Automatic (recommended)",
        "not_ready": "Missing / corrupted",
        "installed": "Bundled",
        "capacity": "Resource guideline",
        "hardware": "System: {memory:.1f} GiB RAM, {free:.1f} GiB free, {cores} logical CPUs",
        "unknown": "RAM detection unavailable: using conservative CPU choice.",
        "gpu": "Execution: CPU (GPU acceleration is not released in this package).",
        "automatic": "Automatic choice: {name}",
        "unavailable": "No suitable packaged model available",
        "memory_note": "A manual selection below the recommendation may be slow or fail due to insufficient RAM.",
        "override": "This model is below the recommended available memory. Save anyway?",
        "confirm": "Save", "cancel": "Cancel",
    },
}


def get_preference(task: str) -> str:
    if task not in TASKS:
        raise ValueError("Unknown AI task.")
    entry = QSettings("Edivora", "Edivora").value(f"ai/{task}", "auto")
    if not isinstance(entry, str) or entry not in ("auto", *SPECS):
        return "auto"
    if entry != "auto" and SPECS[entry].task != task:
        return "auto"
    return entry


class ModelSettingsDialog(QDialog):
    def __init__(self, language: str = "de", parent=None) -> None:
        super().__init__(parent)
        self.language = language if language in LABELS else "de"
        local = LABELS[self.language]
        self.hardware = detect_hardware()
        self.combos = {}
        self.setWindowTitle(local["title"])
        self.setMinimumWidth(590)
        self.setStyleSheet(stylesheet())
        root = QVBoxLayout(self)
        intro = QLabel(local["hint"])
        intro.setWordWrap(True)
        root.addWidget(intro)
        status = (local["hardware"].format(memory=self.hardware.total_gib,
                                          free=self.hardware.available_gib,
                                          cores=self.hardware.logical_cpu_count)
                  if self.hardware.measurement_available else local["unknown"])
        root.addWidget(QLabel(status))
        root.addWidget(QLabel(local["gpu"]))
        form = QFormLayout()
        for task in TASKS:
            combo = QComboBox()
            combo.setMinimumContentsLength(28)
            combo.addItem(local["auto"], "auto")
            for spec in sorted((s for s in SPECS.values() if s.task == task),
                               key=lambda s: s.quality_rank, reverse=True):
                display = f"{spec.display_name} · {spec.min_total_gib} GiB RAM"
                if not model_installed(spec.id):
                    display += " · " + local["not_ready"]
                combo.addItem(display, spec.id)
                idx = combo.count() - 1
                if not model_installed(spec.id):
                    combo.model().item(idx).setEnabled(False)
                combo.setItemData(idx, spec.note, Qt.ItemDataRole.ToolTipRole)
            selected = get_preference(task)
            index = combo.findData(selected)
            combo.setCurrentIndex(index if index >= 0 and combo.model().item(index).isEnabled() else 0)
            self.combos[task] = combo
            form.addRow(local[task], combo)
        root.addLayout(form)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        for combo in self.combos.values():
            combo.currentIndexChanged.connect(self._summarize)
        root.addWidget(QLabel(local["memory_note"]))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(local["confirm"])
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(local["cancel"])
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._summarize()

    def _summarize(self) -> None:
        local = LABELS[self.language]
        lines = []
        for task in TASKS:
            mode = str(self.combos[task].currentData())
            try:
                chosen = choose_model(task, mode, hardware=self.hardware)
            except (ValueError, FileNotFoundError):
                chosen = None
            lines.append(
                f"{local[task]}: " + (
                    local["automatic"].format(name=SPECS[chosen].display_name)
                    if chosen else local["unavailable"]
                )
            )
        self.summary.setText("\n".join(lines))

    def _save(self) -> None:
        local = LABELS[self.language]
        overrides = [
            model for combo in self.combos.values()
            if (model := str(combo.currentData())) != "auto"
            and not recommended(model, self.hardware)
        ]
        if overrides and QMessageBox.question(
            self, local["title"], local["override"],
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        config = QSettings("Edivora", "Edivora")
        for task, combo in self.combos.items():
            config.setValue(f"ai/{task}", str(combo.currentData()))
        config.sync()
        self.accept()
