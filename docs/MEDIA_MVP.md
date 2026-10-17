# Edivora Video & Audio – aktueller Medien-MVP

**Stand: geprüfter `main`-Quellcode 0.4.0a1 (17.10.2026).** Das ältere veröffentlichte `v0.1.0-alpha.1`-ZIP enthält ausschließlich den Fotoeditor. Die neuen Medienfunktionen sind **im Quellcode implementiert**, aber noch **nicht** als neue Windows-Suite mit abgeschlossenem Paket-/Lizenz-/Windows-11-Test veröffentlicht.

## Start und Fenster

Der Edivora-Launcher (`python -m local_ai_photo_editor` oder aktuelle Entwicklungs-EXE `LocalAiPhotoEditor.exe`) bietet **Foto**, **Video** und **Audio**. Die Werkzeuge lassen sich **einzeln, zu zweit oder alle drei** in unabhängigen Prozessen öffnen, ohne einander zu beenden. Direktstart: `--tool photo`, `--tool video`, `--tool audio`.

**Die aktuelle Windows-EXE ist nicht „onefile“:** Der ganze portable Ordner mit Qt, lokalen Modellen und `media-tools/ffmpeg.exe` gehört zusammen. Der Produktname Edivora und die neue Bildmarke ändern aktuell **nicht** den technischen Dateinamen `LocalAiPhotoEditor.exe`.

## Funktionen

| Funktion | Video | Audio |
| --- | --- | --- |
| Eingaben | u. a. MP4, MOV, MKV, WebM, AVI, M4V – **abhängig vom vorhandenen Decoder** | u. a. WAV, MP3, M4A, AAC, FLAC, OGG, Opus – **abhängig vom Decoder** |
| Vorschau | Qt-Multimedia-Player für **ausgewählten Einzelclip**, separate Vorher-/Nachher-Vorschau für sieben Bildkorrekturen | Qt-Multimedia-Player für Einzelclip + separate FFmpeg-Wellenformvorschau |
| Clip-Bearbeitung | Bis **24** Clips, per Drag & Drop sortieren, duplizieren, teilen, pro Clip Anfang/Ende sowie Lautstärke/Stumm | Bis **24** Clips, sortieren, duplizieren, teilen, trimmen, pro Clip Lautstärke, optionale Gesamt-Normalisierung/Fades |
| Projekt | **`.edvp`**, geordnete Clips und Parameter, lokale Quelldatei-Verweise | **`.edap`**, geordnete Clips und Parameter, lokale Quelldatei-Verweise |
| Ergebnisexport | **MP4** in HD (1280×720) oder Full HD (1920×1080) mit 30 fps, MPEG-4 Part 2 und AAC | **WAV** (PCM16, 48 kHz, Stereo) oder **MP3** (192 kbit/s) |
| Lokale KI | U2NETP: Hintergrund **eines ausgewählten Standbilds** als transparentes PNG entfernen | Silero VAD v6.2.1: **Sprachregionen** im gewählten Bereich vorschlagen, nach Bestätigung als Clips anwenden |

Die farbigen Schnittmarken auf der Zeitleiste sind mit den numerischen Ein-/Auswerten synchronisiert; damit wird **der jeweils gewählte Clip** getrimmt. Ein Klick außerhalb der Marken verändert den Abspielkopf, nicht den Schnitt. **Export** fügt die ganze sortierte Sequenz zusammen, nicht nur den gerade angezeigten Clip.

**Bewusste Grenzen:** Nur **eine** geordnete Spur, **keine Überlagerungen/Transitions oder Keyframes**, Medien-Undo/Redo bis 60 Zustände **nur in der Sitzung**, keine kontinuierliche Gesamtvorschau und keine automatische Projektwiederherstellung. Video-KI verarbeitet keine ganze Bewegung; Audio-KI erstellt **keine Transkription**. Das ursprüngliche Ein-Datei-MVP ist durch diese Stufe ersetzt worden. Weitere Details und Ressourcenlimits: [Mehrclip-Projekte & KI](MEDIA_PROJECTS_AI.md).

## Projekte sind nicht die exportierten Medien

`.edvp/.edap` sind streng validierte kleine **JSON-Manifeste**, die Clips und Quellreferenzen speichern. Sie enthalten **keine** Video- oder Audiodateien. Quellen unterhalb des Projektordners werden relativ, externe lokale Dateien ggf. **absolut** referenziert; beim Weitergeben können dadurch lokale Verzeichnisse sichtbar werden. Nach Verschieben/Ändern einer Quelldatei kann das Öffnen wegen fehlender Datei oder Fingerprint-Abweichung scheitern. Ein automatisches Relinking existiert nicht; eine gesicherte manuelle Zuordnung ist als separater Implementierungsschritt vorgesehen.

Foto-Projekte **`.laip`** verwenden hingegen ein ZIP-Archiv mit Bildständen und erlaubten Verlaufssnapshots. Diese Formate sind nicht austauschbar.

## Sicherheit und reale Unterstützung

- Lokale KI: **CPU ONNX Runtime**, geprüfte gepinnte U2NETP-/Silero-Modelldateien, Vorbereitung **nur zur Buildzeit**. Kein Runtime-Modell-Download, keine Konten oder Cloud.
- Ein gesamter Videoexport erzwingt konsistente Streams. Stille Videos erhalten lokal einen stummen Audiostream. Audioquellen werden zur Ausgabe resampelt/neu kodiert.
- FFmpeg wird ohne Shell mit validierten festen Befehlen gestartet. Originale, erkannte Aliase und Hardlinks dürfen nicht überschrieben werden; fertig gerenderte Dateien werden atomar installiert. Decoder-Eingaben bleiben sicherheitskritisch: **keine Sandbox**.
- Qt-Playback unterstützt nicht zwingend dieselben Formate wie der FFmpeg-Encoder. Daher ist ein unterstützter Container **keine garantierte Codec-Unterstützung**.
- Maximal **24 Clips**, höchstens **2 h** je Medienreferenz, insgesamt höchstens **4 h** gewählte Sequenz und **20 GiB** je Quelldatei. Spracherkennung analysiert höchstens **15 Minuten** pro Anfrage.
- Keine offiziell bestätigten GPU-Backends, Windows-11-Clean-Machine-Abnahme oder komplette Lizenzfreigabe des neuen Pakets.

## Technische Anknüpfungspunkte

`ui/launcher.py` (Start), `ui/sequence_window.py` (Timeline, UI), `ui/trim_timeline.py` (Marker), `core/media.py` (Exportvalidierung), `core/media_sequence.py` (Renderplan), `core/media_project.py` (Projektformat), `ai/voice.py` (VAD), `ai/video_frame.py` (ein Frame) und `media_smoke.py` (reale synthetische Medien-Smokes).

[Erste Schritte](GETTING_STARTED.md) · [Architektur](ARCHITECTURE.md) · [Tests/Release-Gates](VERIFICATION.md) · [Roadmap](ROADMAP.md).
