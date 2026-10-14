# Edivora entwickeln und erweitern

Edivora wird als **Open-Source-Desktopanwendung** mit lokaler Foto-, Video- und Audiobearbeitung entwickelt. **Das Repository ist zurzeit privat**; die unten beschriebenen Beitragswege beziehen sich auf Personen mit Repository-Zugriff, bis eine öffentliche Freigabe erfolgt. Beiträge von Menschen und Coding-Assistenten sind willkommen, solange **Datenschutz, Dateischutz, Versionierung und nachgewiesene Funktionalität** erhalten bleiben.

**Verbindlich:** [AGENTS.md](../AGENTS.md). Der produktive Entwicklungsstand ist nicht mit dem alten veröffentlichten Foto-Testpaket `v0.1.0-alpha.1` gleichzusetzen. Vor einer Änderung [README](../README.md), [Architektur](ARCHITECTURE.md), [Medienprojekte](MEDIA_PROJECTS_AI.md) und [Roadmap](ROADMAP.md) lesen.

## Schnelle Entwicklungsumgebung

Unter Windows mit Python **3.12**:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python tools\prepare_model.py
.venv\Scripts\python tools\prepare_voice_model.py
.venv\Scripts\python -m local_ai_photo_editor
```

Die `prepare_*.py`-Schritte sind **nur** explizite Build-/Entwicklungsvorbereitung. Sie dürfen nicht in den Programmstart wandern. Modelle werden zur Laufzeit lokal und nur nach Prüfsummenabgleich geladen. Laufzeit benötigt weder Login noch Internetzugriff. Auf Linux/macOS kann man lokal entwickeln, eine Paket-/Hardware-Freigabe für diese Systeme wird dadurch **nicht** behauptet.

## Wo gehört eine Änderung hin?

| Bereich | Dateien / Grenze |
| --- | --- |
| Start/CLI | `src/local_ai_photo_editor/__main__.py`; `--tool photo\|video\|audio` und unabhängige Prozesse |
| UI | `src/local_ai_photo_editor/ui/`, Übersetzungsdictionaries, `theme.py` |
| Foto-Operationen / Projekt | `core/` inkl. `project.py`, `mask.py`, `editing.py` |
| Medien/Sequenzen/Projekte | `core/media.py`, `media_sequence.py`, `media_project.py` |
| KI und Isolation | `ai/` und begrenzte Unterprozess-Jobs; **keine Cloud-Adapter** |
| Marke/Assets | `branding.py`, `assets/*.svg`, `tools/brand_assets.py` |
| Builds | `tools/build_windows.py`, `.github/workflows/`, `THIRD_PARTY_NOTICES.md` |
| Tests | `tests/` (reine Coretests, GUI-Tests, Medien-/echte Modell-Smokes) |

**Abhängigkeitsregel:** `core/` kennt weder Qt noch ONNX Runtime, UI ruft geprüfte Kernoperationen auf; `ai/` kapselt Modellverifikation. Keine direkten Runtime-Downloads, Shell-Encoderaufrufe oder `pickle`-Deserialisierung.

## Testen

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
.venv\Scripts\python -m local_ai_photo_editor --media-smoke-test test-results/media
```

Bei GUI-Änderungen zusätzlich Qt im Offscreen-Modus (nur soweit die Testumgebung dies unterstützt) und **echte** deutsche/englische Screenshots prüfen. Für Modell- oder Windows-Änderungen die gepinnten echten Gewichte, Source- und **Standalone-EXE** sowie File-/Codec-Tests prüfen. Ein erfolgreiches Unit- oder Mock-Ergebnis belegt **weder** funktionierendes On-Device-KI-Modell **noch** ein auf Windows 11 funktionierendes Installationspaket.

## Ein gutes Feature implementieren

1. **Problem und Abgrenzung:** Für wen? Was ist die bisherige Funktion? Welche Medienformate, Projektversionen, Ressourcen- und Sicherheitsgrenzen gelten?
2. **Isolierte Umsetzung:** Nicht-destruktive Kernoperation, begrenzter Worker/Encoder, verständliche DE/EN-Steuerung, explizite Vorschau/Übernahme/Abbruch.
3. **Regressionen:** Erfolgs-, Fehler-, Abbruch-, Datei-Alias-, untrusted-input- und Versionsfälle. Bei Bildformaten Farb-/Alpha-/Metadatenkorrektheit prüfen; bei Sequenzen stille Clips und Streamwechsel.
4. **Dokumentation:** README-Funktionsmatrix, [Erste Schritte](GETTING_STARTED.md), Detaildokument, [Roadmap](ROADMAP.md), [Modellhinweise](MODELS.md) und Lizenztexte konsistent anpassen; veraltete Zusagen entfernen.
5. **PR mit Nachweisen:** Ausgeführte Befehle, exakter Stand, CI-Links, verbleibende manuelle Prüfungen, Lizenz-/Verteilungs-Gates. Kein automatisches „Release bereit“-Label auf Basis statischer Prüfung.

## KI-Coding-Assistenten: sicherer Einstieg

Gib dem Assistenten den Repository-Link **und** die Anweisung, **AGENTS.md zuerst zu lesen**. Er soll `main` und offene PRs vergleichen, veränderliche Aussagen am Code prüfen, keine Funktionen aus ungemergten PRs als aktuell ausgeben, nur in einem separaten Branch arbeiten und Tests/Limitierungen dokumentieren. Reproduzierbare kleine PRs sind besser als ein großflächiger Rewrite ohne Nachweise.

**Sicherheit / verantwortliche Veröffentlichung:** Keine Medienproben von Nutzern committen, keine geheimen Tokens oder internen Infrastrukturdaten veröffentlichen. Bei Sicherheitsschwachstellen zunächst den verantwortlichen Maintainer-Kanal verwenden, statt Ausnutzungsdetails in einem öffentlichen Issue zu posten.

## Release-Gates

Für ein neues verbreitetes Windows-Paket müssen Source- und Paket-Smoke, echter Offline-Modelltest, FFmpeg-Build-/Lizenzpflichten, Qt-/Modellumverteilung, realistische Codec-Tests und frische Windows-11-Abnahme separat belegt sein. Unsignierte Builds müssen als Teststände gekennzeichnet werden. [Historische Nachweise](VERIFICATION.md) dürfen nicht als Abnahme eines späteren Stands wiederverwendet werden.
