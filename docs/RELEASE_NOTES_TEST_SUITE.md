# Edivora 0.3.0 Alpha 1 – geplanter Windows-x64-Testbuild

**Nicht für öffentliche Weiterverteilung.** Dieses Dokument beschreibt einen ursprünglich für ein privates Repository geplanten Testbuild. Das Repository ist inzwischen öffentlich, die Veröffentlichung des Binärpakets wegen offener Lizenzauflagen aber gesperrt. Er ist weder ein stabiler Windows-11-Release noch eine durchgehend lizenzrechtlich freigegebene Veröffentlichung.

## Enthalten

- Gemeinsamer Edivora-Launcher: **Foto, Video und Audio** einzeln, zu zweit oder alle drei parallel starten, jeweils in einem separaten Prozess.
- **Foto:** klassische Korrekturen, Looks, Zuschneiden, Undo/Redo, lokale U2NETP-Motivauswahl und Freistellung, manuelle Alpha-Maskenkorrektur, bearbeitbare `.laip`-Foto-Projekte.
- **Video:** geordnete Einspur-Sequenz aus bis zu 24 Clips, Clip-Zuschnitt/Teilen/Duplizieren/Umordnen, `.edvp`-Projekt, lokaler MP4-Export. Mit dem CPU-Modell kann **ein einzelnes Videostandbild** freigestellt und als PNG exportiert werden.
- **Audio:** geordnete Einspur-Sequenz aus bis zu 24 Clips, Lautstärke, Fades, Normalisierung, `.edap`-Projekt, WAV-/MP3-Export. Die lokale **Silero VAD** erkennt Sprachaktivität als Vorschlag, **keine Transkription**.
- Deutsches und englisches Qt-UI, neues Edivora-SVG-Branding und lokal abgeleitetes Windows-Icon.
- Komplettes Standalone-Verzeichnis inklusive Laufzeit, geprüften lokalen ONNX-Modellen und FFmpeg. **Kein Python, Modellserver, Konto oder Runtime-Download** beim Start erforderlich.

## Installation

1. `Edivora-0.3.0-alpha.1-windows-x64.zip` und `SHA256SUMS.txt` erst nach ausdrücklicher Freigabe eines späteren Releases herunterladen.
2. Auf Windows in PowerShell im Downloadordner die Prüfsumme mit `Get-FileHash .\Edivora-0.3.0-alpha.1-windows-x64.zip -Algorithm SHA256` berechnen und mit `SHA256SUMS.txt` vergleichen.
3. Gesamtes ZIP entpacken und **`LocalAiPhotoEditor/LocalAiPhotoEditor.exe`** öffnen. Die technische EXE-Dateibezeichnung ist noch historisch, das Produkt in der Oberfläche heißt **Edivora**.
4. Ein, zwei oder alle drei Werkzeuge wählen. Eingabemedien bleiben unverändert; **Projekt speichern** und **Ergebnis exportieren** sind unterschiedliche Funktionen.

**Wichtig:** Die EXE darf nicht einzeln aus dem Ordner verschoben werden; Qt, Modelldateien und `media-tools/ffmpeg.exe` werden benötigt. Windows kann beim Start wegen fehlender Signatur warnen; Sicherheitsschutz nicht pauschal deaktivieren. Dateien nur aus einem künftig ausdrücklich freigegebenen Release mit geprüftem SHA-256 beziehen.

## Technische Grenzen und Sicherheitsstatus

- Videoexport: 1280×720, 30 fps, MPEG-4 Part 2 + AAC; Audioexport: 48-kHz-WAV oder 192-kbit/s-MP3. **Keine** Mehrspurmontage, Übergänge oder kontinuierliche Gesamtvorschau.
- Video-KI freistellt **nur ein Standbild**, Audio-VAD transkribiert **nicht**. Eine automatische Auswahl mehrerer KI-Modellprofile und Offline-Transkription aus dem separaten **PR #17** sind in dieser `0.3.0a1`-Version **nicht** enthalten.
- Verifizierter Inferenzprovider ist **CPU**. **CUDA, DirectML, AMD/ROCm oder GPU-Unterstützung** werden nicht zugesichert. Mindest-RAM/Leistung sind nicht abgenommen.
- FFmpeg, Qt und ONNX-Modelle verarbeiten nicht vertrauenswürdige Dateien; Decoder und abgetrennte Child-Prozesse sind **keine Sicherheitssandbox**.
- Datei-/Projektprüfung und nicht-destruktiver Export sind implementiert, aber nicht als vollständige Sicherheitsgarantie zu verstehen.
- **Keine allgemeine öffentliche Weitergabe:** Exakte FFmpeg-GPL/LGPL-Bedingungen inkl. korrespondierender Quellen, Qt-LGPL-Pflichten und U2NETP-Gewichtsrechte müssen vor einer breiteren Veröffentlichung noch abschließend geprüft werden (siehe `THIRD_PARTY_NOTICES.md`).
- GitHub Actions prüft vor dem Erstellen dieses privaten Prereleases erfolgreiche **Quellcode-, Modell-, GUI-, Medien- und kompilierte Windows-Tests**. Eine separate **Clean-Windows-11-Abnahme**, echte breite Codec-/Hardware-Matrix und vollständige Offline-Firewallprüfung **für genau diesen neuen Build** stehen noch aus.
- Zum Projekt gehört die Open-Source-Lizenz **Apache-2.0** für den eigenen Code; externe Komponenten besitzen eigene Lizenzen.

## Prüfnachweise

Die automatische Veröffentlichung ergänzt unten den **genauen Quellcommit**, die **Windows-CI-Run-ID** und den **Digest des geprüften Actions-Artefakts**. `BUILD_PROVENANCE.json` im Release enthält zusätzlich EXE- und ZIP-SHA-256; `SHA256SUMS.txt` bestätigt den herunterladbaren Archivinhalt. Eine Testperson kann damit die Paketidentität prüfen, ohne ein neues Release mit dem historischen Foto-only-`v0.1.0-alpha.1` zu verwechseln.

[Projekt-README](https://github.com/Cenn0/Edivora/blob/main/README.md) · [Technische Grenzen](https://github.com/Cenn0/Edivora/blob/main/docs/MEDIA_MVP.md) · [Drittanbieter-Lizenzen](https://github.com/Cenn0/Edivora/blob/main/THIRD_PARTY_NOTICES.md).
