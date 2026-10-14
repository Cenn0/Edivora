# Edivora – aktueller Qt-UI-Implementierungsstand

**Quellcode-Baseline:** `main` Version `0.3.0a1` vom 14.10.2026. Ein neuer Windows-11-Endnutzer-Release der Suite ist **nicht** belegt. Die unter [screenshots/](screenshots/) befindlichen DE/EN-Aufnahmen gehören zum **älteren veröffentlichten Foto-Alpha-Paket**; sie zeigen **nicht** den neuen Launcher, die Sequenz-UI oder das neue Edivora-SVG-Icon.

## Ist-Stand der drei Arbeitsbereiche

| Oberfläche | Implementierung | Grenze |
| --- | --- | --- |
| **Launcher** | `ui/launcher.py` mit drei Karten, Direktstart, Mehrfachauswahl 1/2/3, DE/EN und unabhängig gestarteten Prozessen über `__main__.py` | Keine gemeinsame Projekttimeline; das Schließen eines Fensters beeinflusst die anderen nicht |
| **Foto** | `ui/window.py`, `ui/canvas.py`, weitere Dialoge für Licht/Farbe, Looks, Ausschneiden, Maske und lokale U2NETP-Motivtools; Vorschau/Übernehmen/Verwerfen, Undo/Redo und `.laip` | Eine Bildfläche statt Ebenensystem; kein generatives Prompt-Editing |
| **Video** | `ui/sequence_window.py`, QtMultimedia-Einzelclipvorschau, geordnete Single-Lane-Timeline (bis 24 Clips), `ui/trim_timeline.py`, Clip-Split/Duplizieren/Sortieren, `.edvp`, FFmpeg-MP4-Export und aktueller KI-Standbild-PNG-Export | Kein kontinuierliches Komplett-Playback, keine Übergänge/Mehrspur und keine Video-Folgeframe-KI |
| **Audio** | Dieselbe Sequenz-UI mit Wellenform und Einzelclip-Playback, Clip-Schnitt, Lautstärke/Fades/Pegel, `.edap`, FFmpeg WAV/MP3 und bestätigungspflichtigen Silero-VAD-Sprachabschnittvorschlägen | Kein Mehrspurmix, keine Transkription, kein Medien-Undo-/Redo |

Für Video-/Audio-Projekte speichert die UI nur **Quellreferenzen und Bearbeitungsparameter**. Ein Export ist **immer separat**. [MEDIA_PROJECTS_AI.md](MEDIA_PROJECTS_AI.md) dokumentiert harte Größen-/Zeitgrenzen und das sichere Dateiformat.

## Navigation, Aussehen und Marke

- Gemeinsame dunkle Farbpalette: `ui/theme.py`; deutscher und englischer UI-Text in passenden `*_strings.py`-Modulen.
- Die Produktmarke **Edivora** wird als lokale SVG-Datei in Launcher-/Foto-Kopfzeile und als Anwendungsicon eingebunden (`branding.py`, `assets/edivora-mark.svg`). `tools/brand_assets.py` rendert das Windows-ICO **zur Buildzeit**. Keine externen Bilder/CDNs oder Fonts nötig.
- Der Launcher startet **dieselbe** ausführbare Datei mit `--tool photo|video|audio` mehrfach. Der Medien-MVP ist keine einzelne Multitrack-App.
- Die Fotoshell hält riskante Zustandsübergänge zurück: Unbestätigte Vorschauen dürfen nicht unbemerkt beim Wechseln der Navigation verloren gehen.
- Vorher-Nachher, klare Labels, Übersetzungen und Tastaturalternativen wurden im Quellcode berücksichtigt. **Vollständige Accessibility-, DPI- und Screenreader-Abnahme** auf realer Hardware steht aus.

## Tests und offene Abnahme

Relevant sind u. a. `tests/test_edivora_shell.py`, `tests/test_ui.py`, `tests/test_sequence_ui.py`, `tests/test_trim_timeline.py`, `tests/test_media_project.py`, `tests/test_media_ai.py` und `tests/test_branding.py`.

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
```

Die GUI-Source- und Windows-Standalone-Smokes müssen für **den jeweiligen aktuellen Commit** tatsächlich laufen. Neu erzeugte Launcher-/Media-Screenshots dürfen erst als echte Anwendungsscreenshots eingebunden werden, wenn ihre Herkunft/Umgebung feststeht. Interaktive Maus-, Tastatur-, DPI-, Medien- und Decoderprüfungen unter Windows 11 bleiben eigene Release-Gates.

[Designsystem](DESIGN_SYSTEM.md) · [Branding](BRAND.md) · [Media-MVP](MEDIA_MVP.md) · [Release-Gates](ROADMAP.md).
