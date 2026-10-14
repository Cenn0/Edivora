![Edivora – Create simply. Stay local.](src/local_ai_photo_editor/assets/edivora-wordmark.svg)

# Edivora

**Language:** Deutsch (dieses README) · [English README](README.en.md)

**Foto, Video und Audio einfach bearbeiten – mit ausgewählten lokalen KI-Funktionen.** Edivora wird als kostenloses Open-Source-Werkzeug für gelegentliche Bearbeitung entwickelt; **das GitHub-Repository ist derzeit privat**, eine öffentliche Veröffentlichung der aktuellen Suite steht noch aus. Für die Bearbeitung sind weder Konto noch Modellserver oder Cloud-Verarbeitung vorgesehen. Die Oberfläche ist auf **Deutsch und Englisch** verfügbar.

![Edivora Photo, Video und Audio](src/local_ai_photo_editor/assets/edivora-banner.svg)

> **Wichtig: Quellcode ist nicht gleich Download.** Das auf GitHub veröffentlichte **[v0.1.0-alpha.1-Paket](https://github.com/Cenn0/Edivora/releases/tag/v0.1.0-alpha.1)** ist eine ältere, unsignierte **Foto-Testalpha**. Foto-, Video- und Audio-Launcher, Mehrclip-Timelines sowie Projektdateien gehören zum **0.3-Entwicklungsstand; die Weiterentwicklung 0.4.0a1 ist unten gesondert beschrieben**. Die aktuelle Suite wird ausschließlich als private, unsignierte Testalpha angeboten; eine breite öffentliche Windows-Veröffentlichung ist nicht freigegeben. Die erste Windows-11-Clean-Machine-Abnahme und Redistribution-Prüfungen stehen aus.

## Neu im Entwicklungsstand 0.4.0a1

**Launcher ohne Auswahlkästchen:** Foto, Video und Audio direkt öffnen; der Launcher bleibt offen. Mehr lokale Vektor-Icons, kompakte Werkzeugleisten und anpassbare Vorschauflächen. Video-/Audio-Einstellungen sind in Reiter aufgeteilt; lange Bedienbereiche scrollen statt abgeschnitten zu werden. Mindestgröße: **640 × 480 logische Pixel**.

**Video verbessern:** Helligkeit, Kontrast, Farbstärke, Wärme, Grün/Magenta, klassische Rauschglättung und Schärfe; anpassbare Vorlagen und echter Vorher-/Nachher-Bildvergleich. Korrekturen werden je Clip im Projekt gespeichert und beim Export angewandt. Die normale Abspielvorschau zeigt weiterhin die Quelle. HD- und Full-HD-Export stehen zur Auswahl.

**Echte lokale KI-Entrauschung:** DnCNN verarbeitet einen gewählten Abschnitt bis **30 Sekunden**, maximal **720p / 30 fps**, auf der CPU. Stärke und Vorschau sind einstellbar; erst nach Bestätigung wird eine separate MP4 erstellt. Das kann langsam sein und Details glätten oder flimmern. **Kein universeller KI-Filterentferner:** Eingebrannte Filter können nur teilweise abgeschwächt werden; verlorene Originaldetails werden nicht zuverlässig wiederhergestellt.

**Video und Audio:** Rückgängig/Wiederholen mit bis zu 60 Zuständen. Neue `.edvp/.edap`-Dateien verwenden Schema 2; Schema 1 wird weiterhin gelesen. Alte Versionen können Schema 2 nicht öffnen.

[Bedienung, Grenzen und Modellnachweise](docs/VIDEO_RESTORATION.md) · [Änderungsübersicht 0.4](docs/RELEASE_NOTES_RESPONSIVE_SUITE.md)

## Windows-Testdownloads und Versionsgrenzen

**Bisheriger 0.3-Build – ohne die neuen 0.4-Funktionen:**

**[Windows-x64-Testbuild 0.3 (GitHub Actions)](https://github.com/Cenn0/Edivora/actions/runs/38636053924/artifacts/11928373456)** · [Erfolgreicher Pakettest](https://github.com/Cenn0/Edivora/actions/runs/38636053924)

Dieser bereits erfolgreich durchgelaufene Build aus PR #18 enthält **den Edivora-Anwendungscode des damaligen 0.3-Merges auf `main`** (Logo, Launcher, Foto/Video/Audio, lokale KI); nachträgliche Änderungen betreffen nur Dokumentation und den Release-Workflow. Er ist **14 Tage ab Erstellung** als Actions-Artefakt verfügbar und erfordert Zugriff auf das private Repository. Das Archiv enthält die Dateien der Anwendung; **den gesamten Inhalt gemeinsam in einen Ordner entpacken und `LocalAiPhotoEditor.exe` darin starten**. Die unten genannten dauerhaften Release-Links funktionieren erst nach erfolgreicher neuer Main-Paketprüfung.

**[Windows x64: Edivora 0.3.0 Alpha 1 als ZIP herunterladen](https://github.com/Cenn0/Edivora/releases/download/v0.3.0-alpha.1/Edivora-0.3.0-alpha.1-windows-x64.zip)** · [SHA-256-Prüfsumme](https://github.com/Cenn0/Edivora/releases/download/v0.3.0-alpha.1/SHA256SUMS.txt) · [Testbuild und Hinweise](https://github.com/Cenn0/Edivora/releases/tag/v0.3.0-alpha.1) · [Build-Nachweise](https://github.com/Cenn0/Edivora/releases/download/v0.3.0-alpha.1/BUILD_PROVENANCE.json)

Dies ist ein **privates, unsigniertes Prerelease** für Personen mit Zugriff auf dieses Repository, **kein offiziell freigegebener Windows-11-Release**. Der Build wird nur aus einem **erfolgreich geprüften Windows-CI-Artefakt** erstellt; fehlen die Paketprüfungen, wird die Release-Veröffentlichung nicht durchgeführt. Die ältere Foto-Version unten ist **nicht** dieselbe Anwendung. Der neue Testbuild enthält den Launcher und alle drei Werkzeuge.

**So startest du:** ZIP und `SHA256SUMS.txt` laden, den ZIP-Hash in PowerShell mit `Get-FileHash .\Edivora-0.3.0-alpha.1-windows-x64.zip -Algorithm SHA256` vergleichen, alles entpacken und **`LocalAiPhotoEditor/LocalAiPhotoEditor.exe`** öffnen. Der EXE-Dateiname ist noch historisch, die Anwendung heißt **Edivora**. DLLs, Modelle und `media-tools/ffmpeg.exe` müssen im Ordner bleiben. Das Paket erfordert weder separates Python noch Docker. **Nicht öffentlich weiterverteilen:** Die FFmpeg-/Qt-/Modell-Lizenzfreigaben sind noch offen, und eine vollständige Clean-Windows-11-Abnahme fehlt. [Release Notes](docs/RELEASE_NOTES_TEST_SUITE.md) · [Aktuelle Windows-Builds](https://github.com/Cenn0/Edivora/actions/workflows/windows-alpha.yml).

## Was kann Edivora?

| Bereich | Im aktuellen Quellcode umgesetzt | Wichtige Grenze |
| --- | --- | --- |
| **Foto** | JPEG/PNG/WebP öffnen und exportieren; Licht/Farbe, Looks, Zuschneiden, Spiegeln, Drehen, Bildgröße, Hintergrundgestaltung; Vorschau, Vorher/Nachher, Undo/Redo; lokale U2NETP-Motivauswahl und manuelle Alphamasken-Korrektur; **`.laip`**-Projekte | Kein RAW/HDR, keine Ebenen oder generative Textbearbeitung; Freistellmasken sind nicht immer perfekt |
| **Video** | Clips importieren, auf **einer** Timeline anordnen (bis 24), teilen, duplizieren, trimmen und Lautstärke einstellen; **`.edvp`** speichern/öffnen; lokale KI-Freistellung **eines Videostandbilds** als PNG; MP4-Export | Keine Mehrspurmontage, Übergänge oder Untertitel; Bildkorrekturen und kurze KI-Entrauschung siehe 0.4 oben. Export HD/Full HD, 30 fps, MPEG-4 Part 2 + AAC |
| **Audio** | Clips auf **einer** Timeline anordnen (bis 24), trimmen, teilen und mit Lautstärke/Fades/Pegelausgleich exportieren; **`.edap`** speichern/öffnen; lokale Silero-VAD-KI schlägt Sprachabschnitte vor; WAV/MP3-Export | Kein Mehrspurmix, keine Transkription, keine Rauschunterdrückungs-KI; Sprachabschnitte sind nur ein zu prüfender Vorschlag |

Der **Launcher** kann Foto, Video und Audio einzeln, zwei gemeinsam oder alle drei gleichzeitig in **unabhängigen Prozessen** starten. Vorschau und Bearbeitung der Medien-Timeline beziehen sich auf den gewählten Clip; erst der Export setzt die Reihenfolge zusammen. Das Original wird dabei nicht überschrieben.

**KI bedeutet nicht automatisch Generierung:** U2NETP erstellt Motivmasken für Foto/ein Videostandbild; Silero VAD erkennt Sprachaktivität in Audio; DnCNN entrauscht einzelne RGB-Frames eines kurzen Videos. Klassische Korrekturen, Fades und Filter sind keine generativen KI-Modelle. KI-Berechnung läuft lokal über **ONNX Runtime CPU**, soweit für die jeweilige Funktion dokumentiert. Für GPU-/CUDA-/DirectML-Betrieb existiert derzeit **keine projektseitig verifizierte Unterstützung**. Fehlende Modelle werden zur Laufzeit **nicht** heruntergeladen.

## Direkt ausprobieren: veröffentlichte Foto-Testalpha

1. **[Windows-x64-ZIP v0.1.0-alpha.1 laden](https://github.com/Cenn0/Edivora/releases/download/v0.1.0-alpha.1/LocalAiPhotoEditor-0.1.0-alpha.1-windows-x64.zip)** und den Hash anhand von [SHA256SUMS.txt](https://github.com/Cenn0/Edivora/releases/download/v0.1.0-alpha.1/SHA256SUMS.txt) prüfen.
2. **Vollständig entpacken**; die EXE benötigt die mitgelieferten Unterordner.
3. **`LocalAiPhotoEditor/LocalAiPhotoEditor.exe`** starten, ein Foto öffnen, bearbeiten und unter einem **anderen** Dateinamen exportieren.

Diese historische Alpha bietet **nur die Grundfunktionen des Fotoeditors und die KI-Hintergrundentfernung**. Sie enthält **keinen** Edivora-Launcher, keine Medieneditoren und keine neuen Projekt-/Motivwerkzeuge.

![Historische Foto-Testalpha (Deutsch)](docs/screenshots/ui-smoke-de.png)

*Screenshot des tatsächlich geprüften älteren Foto-Alphapakets – **kein** Screenshot der neuen Edivora-Mediensuite.*

Die Alpha wurde auf **Windows Server 2022** automatisiert getestet (damals 69 Tests, echte CPU-Inferenz sowie UI-/Bildexport- und Offline-Paketprüfungen). Daraus folgt **keine** nachgewiesene Freigabe für alle Windows-11-Geräte. Details: [Verifikation des historischen Releases](docs/VERIFICATION.md).

## Aktuellen Entwicklungsstand aus dem Quellcode starten

**Voraussetzung:** Python **3.12** und zum **Vorbereiten** der drei gepinnten KI-Modelle Internetzugriff. Das eigentliche Programm verwendet später keine Modell-Downloads.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python tools\prepare_model.py
.venv\Scripts\python tools\prepare_voice_model.py
.venv\Scripts\python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python -m pip install onnx==1.23.2
.venv\Scripts\python tools\prepare_restoration_model.py
.venv\Scripts\python -m local_ai_photo_editor
```

Der letzte Befehl öffnet den Launcher. Einzelne Werkzeuge starten mit:

```powershell
.venv\Scripts\python -m local_ai_photo_editor --tool photo
.venv\Scripts\python -m local_ai_photo_editor --tool video
.venv\Scripts\python -m local_ai_photo_editor --tool audio
```

**Im aktuellen Entwicklungsbuild** ist der Einstieg weiterhin `LocalAiPhotoEditor.exe`, trotz Edivora-Name und Logo. Das portable Windows-Buildsystem erstellt einen **kompletten Ordner**, keine einzeln verschiebbare Onefile-EXE. Der neue Name `Edivora.exe` wird nicht als schon ausgeliefert behauptet. [Ausführliche Einstiegsanleitung](docs/GETTING_STARTED.md).

## Lokal – mit bewusst dokumentierten Grenzen

- **Keine Konten, Laufzeit-Telemetrie oder Cloud-KI.** Die App lädt Medien und Modelle nicht zu externen Diensten hoch. Build-/Entwicklungswerkzeuge können gepinnte Abhängigkeiten und Modelle herunterladen. Ein Export in einen vom Nutzer gewählten Cloud-Sync-Ordner bleibt dessen Verantwortung.
- **Originalschutz:** Fotoexporte und FFmpeg-Medienexporte schreiben in eine neue Ausgabedatei und sperren erkannten Originalpfad-/Symlink-/Hardlink-Überschreibungen. Vor dem Ersetzen anderer Dateien wird nachgefragt; temporäre Reste können nach einem Absturz verbleiben.
- **Projektdateien unterscheiden sich:** `.laip` enthält Foto-Bildstände und Verlauf; `.edvp/.edap` sind kleine JSON-Projekte und enthalten **keine Medienkopien**. Außerhalb des Projektordners referenzierte Medien können mit **absoluten lokalen Pfaden** gespeichert werden; beim Teilen können dadurch Ordnernamen sichtbar werden. Defekte/verschobene Quellen können das Wiederöffnen verhindern.
- **Mediendateien sind nicht vertrauenswürdig:** Die eingebundenen nativen Decoder sind keine Sicherheits-Sandbox. Die Umverteilungsrechte für FFmpeg/Qt/Modelle müssen vor breiter Veröffentlichung gesondert geklärt werden.

## Für Mitwirkende und KI-gestützte Entwicklung

Der Hauptcode verwendet **Python 3.12**, **PySide6/Qt Widgets**, **Pillow/NumPy**, **ONNX Runtime CPU** und **FFmpeg** für Video-/Audioexport. Verantwortungen: `ui/` für Oberflächen und Übersetzungen, `core/` für fachliche Operationen und Dateivalidierung, `ai/` für geprüfte Modelladapter; der Inferenz- und Encoderbetrieb erfolgt in separaten Prozessen.

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
```

**Für KI-Coding-Assistenten:** Beginne mit [AGENTS.md](AGENTS.md) und dem [Entwicklungsleitfaden](docs/CONTRIBUTING.md). Lies Architektur, Projektschemata und Sicherheitsregeln, bevor du Funktionen veränderst. Neue Modelle, Laufzeit-Netzwerkzugriffe und Release-Behauptungen benötigen explizite Prüfung; ein grüner Unit-Test beweist weder ein lauffähiges Windows-Paket noch KI-Qualität.

## Dokumentation

**[Dokumentationsübersicht](docs/README.md)** · [Erste Schritte](docs/GETTING_STARTED.md) · [Architektur](docs/ARCHITECTURE.md) · [Foto-/Medienprojekte und lokale KI](docs/MEDIA_PROJECTS_AI.md) · [Modellgrenzen](docs/MODELS.md) · [UI-/UX-Designsystem](docs/DESIGN_SYSTEM.md) · [Edivora-Branding](docs/BRAND.md) · [Roadmap](docs/ROADMAP.md) · [Verifikationsstand](docs/VERIFICATION.md) · [Beitragen](docs/CONTRIBUTING.md)

**Lizenz:** Anwendungscode **Apache-2.0** ([LICENSE](LICENSE)). Externe Bibliotheken, Modelle und FFmpeg haben eigene Bedingungen und gegebenenfalls offene Redistributionspflichten; siehe [Drittanbieterhinweise](THIRD_PARTY_NOTICES.md). Der Projektname ist keine Zusicherung einer registrierten Marke.
