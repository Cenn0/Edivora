# Edivora – Qt-Oberflächenstand

**Baseline: `main` 0.4.0a1, 15.10.2026.** Dies ist eine Beschreibung des **implementierten Quellcodes**, kein Nachweis eines allgemein freigegebenen Windows-Pakets. Unter [screenshots/](screenshots/) liegen historische Aufnahmen der **älteren Foto-Alpha**; sie dokumentieren ausdrücklich **nicht** das heutige 0.4-Layout.

## Arbeitsbereiche

| Oberfläche | Implementierung | Bewusste Grenze |
| --- | --- | --- |
| **Launcher** | `ui/launcher.py`: drei Karten mit direktem Start (Alt+1/2/3), bleibt geöffnet, beliebig viele unabhängige Foto-/Video-/Audiofenster über `__main__.py` | Kein gemeinsames Fensterprojekt oder Mehrspurarbeit |
| **Foto** | `ui/window.py`, `ui/canvas.py`, Motiv-, Masken- und Korrekturdialoge; geführte Werkzeuge, Bildbearbeitung mit Vorschau/Übernehmen/Verwerfen, Undo/Redo und `.laip` | Keine Ebenen, keine generative Textbearbeitung |
| **Video** | `ui/sequence_window.py`, `ui/media_shell.py`, `ui/video_dialog.py`: Einzelclip-Wiedergabe, bis 24 Clips in einer Spur, Schneiden/Sortieren, `.edvp`, Undo/Redo und HD/Full-HD-MP4-Export; sieben klassische Bildkorrekturen mit tatsächlicher Frame-Vorschau und lokale DnCNN-CPU-Entrauschung kurzer Sequenzen | Keine kontinuierliche Gesamtvorschau, Mehrspurmontage, Übergänge, GPU-Runtime oder zuverlässiges Entfernen eingebrannter Filter |
| **Audio** | Derselbe Sequenzeditor: Einzelclip-Wiedergabe und Wellenform, Trimmen/Splitten, Pegel/Fades, `.edap`, Undo/Redo, WAV/MP3 sowie bestätigungspflichtige Silero-VAD-Schnittvorschläge | Keine Mehrspurmischung oder Worttranskription; PR #17 ist separat |

## Layout, Bedienung und Projektzustand

- Gemeinsames Dark-Theme und lokale SVG-/Vektoricons aus `ui/theme.py`, `ui/icons.py` und `assets/`. Kein CDN, Laufzeit-Fontdownload oder externes UI-Skript.
- Launcher, Editoren und ausgewählte Dialoge verwenden kompakte Bedienelemente, skalierende Vorschauen, abkürzende Dateinamen mit vollständigem Tooltip und scrollbare Inspektor-Reiter. Unterstützte Mindestfenstergröße der 0.4-Suite: **640 × 480 logische Pixel**. Die scrollbaren Seiten machen Befehle erreichbar, nicht gleichzeitig sichtbar.
- Beschriftungen, Icons und Tooltips bleiben bei kompakten Schaltflächen über **AccessibleName**, Tastatur und Beschriftungshilfen erreichbar. Vollständige Screenreader-/DPI-Abnahme auf realen Geräten steht aus.
- Bei ungespeicherten Video-/Audioänderungen kann man vor Projektwechsel oder Fensterschluss **Speichern**, **Änderungen verwerfen** oder **Abbrechen** wählen. Ein abgebrochenes oder fehlgeschlagenes Speichern verhindert das Verwerfen des aktuellen Projekts. Speichern/Exportieren sind verschiedene Aktionen.
- Foto-/Medienprojekte und Quelldateien werden nicht stillschweigend durch Export überschrieben; Medienprojektdateien enthalten weiterhin externe Dateiverweise. Die vorhandenen Validierungs- und Speichergrenzen bleiben verbindlich.

## Verifikation und offene Prüfungen

Automatisierte Tests: `tests/test_responsive_suite.py`, `tests/test_suite_layout_surface.py`, `tests/test_sequence_ui.py`, `tests/test_unsaved_media_prompt.py`, `tests/test_video_ui.py` und andere Regressionstests. Ihre genaue Aussage hängt vom **geprüften Commit** ab. Offscreen-Qt-Geometrietests und DPI-Simulationen ersetzen keine interaktive Windows-11-Clean-Machine-Abnahme.

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
```

**Keine öffentlichen Binärdownloads freigeben**, bevor Lizenz-, Modell-, Paket- und Windows-11-Release-Gates erfüllt sind. [Designsystem](DESIGN_SYSTEM.md) · [Modellgrenzen](MODELS.md) · [Roadmap](ROADMAP.md) · [Release-Checkliste](PUBLIC_RELEASE_CHECKLIST.md).
