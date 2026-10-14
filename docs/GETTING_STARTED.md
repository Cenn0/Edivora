# Erste Schritte mit Edivora

Die Anwendungen sind für gelegentliche lokale Foto-, Video- und Audiobearbeitung gedacht. **Wähle zuerst den richtigen Softwarestand**, damit Anleitung und Funktionen zusammenpassen.

## Aktuellen Entwicklungsstand als private Windows-Testversion ausprobieren

**[Edivora 0.3.0 Alpha 1 herunterladen](https://github.com/Cenn0/Edivora/releases/download/v0.3.0-alpha.1/Edivora-0.3.0-alpha.1-windows-x64.zip)** · [SHA-256](https://github.com/Cenn0/Edivora/releases/download/v0.3.0-alpha.1/SHA256SUMS.txt) · [Release-Hinweise](https://github.com/Cenn0/Edivora/releases/tag/v0.3.0-alpha.1). Der Download ist nur für Personen mit Zugriff auf das **private Repository** bestimmt. Diese Version enthält Foto-, Video- und Audiobearbeitung, ist **unsigniert** und noch **nicht** auf einem frischen Windows 11 umfassend abgenommen. Drittanbieter-Lizenzprüfungen für öffentliche Weitergabe sind nicht abgeschlossen.

Nach Download den SHA-256 des ZIPs prüfen (`Get-FileHash .\Edivora-0.3.0-alpha.1-windows-x64.zip -Algorithm SHA256`), komplett entpacken, dann `LocalAiPhotoEditor/LocalAiPhotoEditor.exe` öffnen. Die alte technische EXE-Bezeichnung ist beabsichtigt. Die Anwendung wird unter dem Namen **Edivora** gestartet; der Launcher bietet alle drei Werkzeuge. Enthaltene DLLs, FFmpeg und Modell-Dateien dürfen nicht aus dem Ordner entfernt werden.

## 1. Nur ein Foto bearbeiten: historische Windows-Testalpha

Der [Download `v0.1.0-alpha.1`](https://github.com/Cenn0/Edivora/releases/tag/v0.1.0-alpha.1) enthält **ausschließlich den früheren Fotoeditor**. ZIP herunterladen, Hash aus `SHA256SUMS.txt` prüfen, vollständig entpacken und `LocalAiPhotoEditor/LocalAiPhotoEditor.exe` öffnen. Ein Foto importieren, Helligkeit oder Ausschnitt ändern, optional den Hintergrund lokal freistellen und **eine neue Datei exportieren**. Das Original ist geschützt.

**Nicht enthalten:** Edivora-Launcher, Video, Audio, `.laip/.edvp/.edap`, aktuelle geführte Motiveffekte oder manuelle Maskenkorrektur. Der ältere Screenshot unter [screenshots/ui-smoke-de.png](screenshots/ui-smoke-de.png) zeigt ausschließlich diese Testalpha.

## 2. Die ganze Edivora-Suite: aktueller Quellcode

Für den Entwicklungsstand brauchst du **Python 3.12**; die Modelldateien müssen **einmalig während der Vorbereitung** bezogen werden, nicht durch die laufende App. Im Repository-Hauptverzeichnis unter Windows:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python tools\prepare_model.py
.venv\Scripts\python tools\prepare_voice_model.py
.venv\Scripts\python -m local_ai_photo_editor
```

Andere Shells verwenden `.venv/bin/python` und passende Pfadseparatoren. Die erste Zielplattform ist Windows 11 x64; Linux/macOS-Quellstarts sind **keine** offiziell verifizierte Paketunterstützung.

Der Launcher zeigt drei Karten. Wähle **Foto**, **Video** oder **Audio** per `Öffnen` oder markiere **1–3 Werkzeuge** und klicke **Ausgewählte Werkzeuge öffnen**. Die Editoren arbeiten in getrennten Fenstern/Prozessen. Beim späteren Entwicklertest-Paket heißt die Startdatei zurzeit **`LocalAiPhotoEditor.exe`** trotz Edivora-Logo; DLLs, Modelle und `media-tools/ffmpeg.exe` müssen daneben liegen.

## 3. Foto: arbeiten, sichern, exportieren

**Bild öffnen** → Anpassung auswählen → Vorschau prüfen → **Übernehmen** (oder **Abbrechen**) → **Als neue Datei exportieren**. Bei ungewollten Änderungen **Rückgängig/Wiederholen** verwenden. Die KI-Freistellung und Motivwerkzeuge berechnen eine Maske lokal; Haare, Fell, Glas und geringe Kontraste können falsch erkannt werden. Der **Pinsel zur Maskenkorrektur** ändert Transparenz, erzeugt aber keine verlorenen RGB-Details.

**Projekt speichern** erzeugt im neueren Quellcode ein **`.laip`-Archiv** mit Original, Bearbeitungsstand und begrenzten Undo-/Redo-Snapshots. Es ist **nicht** die gleiche Datei wie ein exportiertes PNG/JPEG/WebP. Nach dem Öffnen eines Projekts ist zum Schutz unbekannter Originalpfade nur Export unter einem neuen Dateinamen zulässig. Details: [Foto-Projektformat](PROJECT_FORMAT.md).

## 4. Video: mehrere Clips in einer Reihenfolge

**Videoeditor öffnen** → Clip importieren → bei Bedarf bis zu **24 Clips** ergänzen → Clip auswählen, auf der Zeitleiste trimmen, teilen oder duplizieren → Clips per Drag & Drop oder Schaltflächen sortieren → **Projekt speichern** (`.edvp`) → **MP4 exportieren**.

Die Vorschau zeigt **jeweils einen Clip**, nicht das ganze zusammengesetzte Video. Der Export erzeugt eine einzige MP4-Datei mit vereinheitlichtem **1280×720, 30 fps, MPEG-4 Part 2 + AAC**. Das ist keine professionelle Mehrspur-Timeline und kein H.264-Garantieversprechen. Die lokale KI-Funktion **Standbild freistellen** exportiert nur das **gerade ausgewählte Videobild** als separates PNG; sie verändert nicht das ganze Video.

## 5. Audio: Clips schneiden und Sprache finden

**Audioeditor öffnen** → Audioquellen ergänzen → Clip auswählen, schneiden/teilen, Lautstärke einstellen und Reihenfolge festlegen → optional Normalisierung und Fades → **Projekt speichern** (`.edap`) → als **WAV oder MP3** exportieren.

Die lokale **Silero-VAD-Spracherkennung** erkennt Sprachaktivität im gewählten Bereich (bis zu 15 Minuten). Sie schlägt Schnittabschnitte vor und fragt vor der Übernahme. Sie **transkribiert keine Wörter** und kann leise Sprache verpassen oder Geräusche irrtümlich erkennen.

## 6. Unterschied zwischen Speichern und Exportieren

| Aktion | Inhalt | Für wen? |
| --- | --- | --- |
| Foto-Projekt `.laip` | Fotos und vorhandene Bildstände als Projektarchiv | Foto-Bearbeitung später fortsetzen |
| Video-/Audio-Projekt `.edvp/.edap` | Einstellungen, Clipreihenfolge, Verweise und Fingerprints, **keine Mediendateien** | Später mit denselben Quellmedien weiterarbeiten |
| Export `.png/.jpg/.webp/.mp4/.wav/.mp3` | Ergebnisdatei, neu erzeugt und ggf. neu kodiert | Fertige Medien ansehen und weitergeben |

**Achtung bei Medienprojekten:** Quellen außerhalb des Projektordners können als absolute Pfade referenziert werden. Beim Verschieben oder Weitergeben fehlen dann womöglich Medien, und die Projektdatei kann private Ordnernamen enthalten. Medien möglichst zusammen mit dem Projekt im selben Ordner organisieren. Automatisches Relinking und Autosave fehlen.

## 7. Typische Probleme

- **Das neue Video-/Audiotool fehlt:** Du hast wahrscheinlich das **alte veröffentlichte Foto-ZIP** geöffnet; nutze den aktuellen Entwicklungsquellstand oder ein separat geprüftes neues Entwicklungspaket.
- **Modell nicht verfügbar:** Im Quellcheckout die entsprechenden `tools/prepare_*.py`-Skripte bei erlaubtem Internetzugang ausführen. Die App lädt keine Gewichte zur Laufzeit.
- **Vorschau spielt nicht, obwohl Export möglich wäre:** Qt Multimedia und FFmpeg haben unterschiedliche Decoder. Eine Datei kann bei einem funktionieren und beim anderen nicht. Anderes lokales Quellformat testen; keine Codec-Garantie.
- **Projekt lässt sich nicht öffnen:** Prüfe, ob alle Medien am ursprünglichen Pfad liegen und unverändert sind. Das Projekt enthält keine Medienkopien; ein Datei-Fingerprint ist kein Vollhash.
- **EXE funktioniert alleine nicht:** Den **kompletten** vom Build erzeugten Ordner behalten.
- **Windows meldet eine unbekannte App:** Die bisherige Testalpha ist **unsigniert**. Nur Dateien aus der verifizierten Releasequelle mit abgeglichenem Hash verwenden; Schutzmechanismen nicht pauschal deaktivieren.

Für technische Grenzen und Tests siehe [MEDIA_PROJECTS_AI.md](MEDIA_PROJECTS_AI.md), [MODELS.md](MODELS.md) und [VERIFICATION.md](VERIFICATION.md).
