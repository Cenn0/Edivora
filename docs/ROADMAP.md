# Edivora – Roadmap

**Stand: 15.10.2026 · aktueller `main`-Quellcode: 0.4.0a1.** Die Roadmap unterscheidet Quellcodefunktionen, erfolgreiche automatisierte Prüfungen, getestete Binärartefakte und eine **offiziell freigegebene Veröffentlichung**. Das sind unterschiedliche Zustände.

## Aktuell im Quellcode umgesetzt (0.4.0a1)

- **Launcher:** Foto, Video und Audio direkt und unabhängig starten; der Launcher bleibt für weitere Starts offen. Keine Auswahlkästchen und keine Sammelstart-Schaltfläche.
- **Oberflächen:** gemeinsames Dark-Theme und Edivora-Branding, lokale Vektoricons, DE/EN-Beschriftungen und Tastaturalternativen. Medienwerkzeuge besitzen kompakte Werkzeugleisten, größenanpassbare Einzelclipvorschauen und scrollbare Inspektor-Reiter. Unterstütztes Layout-Minimum: **640 × 480 logische Pixel**.
- **Foto:** Korrekturen und Looks, Zuschnitt/Rotation, Motiv-/Hintergrundeffekte, Masken-Pinsel, reversible Vorschauen, Undo/Redo und `.laip`-Projektarchive.
- **Video:** bis zu 24 Clips auf **einer** Reihenfolgespur, trimmen/teilen/duplizieren/sortieren, `.edvp`-Projektdateien, FFmpeg-MP4-Export in HD oder Full HD. Sieben konventionelle Bildkorrekturen mit Vorher-/Nachher-Standbildvorschau und pro Clip gespeicherten Parametern.
- **Video-KI:** lokale U2NETP-Freistellung **eines Standbilds** sowie CPU-DnCNN-Entrauschung eines ausgewählten Bereichs bis **30 s, 720p und 30 fps**. Die KI-Entrauschung erzeugt nach expliziter Bestätigung eine **separate** MP4. Kein universelles Entfernen eingebrannter Filter oder Wiederherstellen verlorener Bilddaten.
- **Audio:** bis zu 24 Clips auf einer Reihenfolgespur, Trimmen, Pegel/Fades, `.edap`-Projekte, WAV-/MP3-Export, lokale Silero-VAD-Vorschläge für Sprachsegmente.
- **Medienprojekte:** Undo/Redo (bis 60 Zustände), Schema 2 für neue Projekte, striktes Einlesen älterer Schema-1-Dateien. Projektdateien referenzieren externe Medien, statt sie einzubetten. Originalmedien werden nicht überschrieben.

[Umsetzung und Einschränkungen](VIDEO_RESTORATION.md) · [Release Notes 0.4](RELEASE_NOTES_RESPONSIVE_SUITE.md) · [UI-Stand](UI_IMPLEMENTATION.md).

## Historischer Foto-Testbuild

Das frühere unsignierte `v0.1.0-alpha.1` enthielt **nur** Fotofunktionen und U2NETP, nicht den heutigen Launcher, Video/Audio oder DnCNN. Automatisierte Windows-Server-2022-/Offline-Prüfungen beziehen sich auf genau dieses Paket und beweisen keine Windows-11-Abnahme der 0.4-Suite. Der frühere Binärdownload wird bis zur Redistributionsprüfung zurückgezogen. [Historische Nachweise](VERIFICATION.md).

## Abgrenzung von noch nicht integrierter Arbeit

- **PR #17:** Automatische/manuelle KI-Modellprofile, IS-Net und Whisper sind ein **separater offener Vorschlag**, nicht Teil von 0.4.0a1 in `main`. [PR ansehen](https://github.com/Cenn0/Edivora/pull/17).
- **Weiterhin offen:** Durchgehende Vorschau der kompletten Sequenz, Mehrspurmontage und -mischung, Übergänge, vollständiges Media-Relinking, portable eingebettete Medienpakete, Autosave/Crash-Recovery, breiter bestätigte Codec-/Hardwarematrix und echte GPU-Ausführung.
- **Längerfristig:** verifizierte Video-KI über zusammenhängende Frames, zusätzliche Spracherkennung und hochwertige generative Funktionen nur mit geprüften Modellgewichten, Rechten, Ressourcenbudgets, expliziter Übernahme und reproduzierbaren Qualitätsnachweisen.

## Freigabe-Gates für öffentliche Windows-Binärpakete

1. **Reale Funktion:** Foto-/Medien-/Modell-Smokes mit echten gepinnten Gewichten sowie korrekte Abbruch- und Exportpfade, DE/EN und relevante Anzeigegrößen.
2. **Paketidentität:** Windows-Standalone-Build aus exakt identifiziertem Commit, Prüfsummen, Abhängigkeits- und Modellmanifest, Test des tatsächlich heruntergeladenen Pakets unter wirksamer Offline-Sperre.
3. **Lizenzen/Sicherheit:** genaue Qt-/PySide6-/Shiboken-Binaries, LGPL-Verpflichtungen und Quellen; exakte FFmpeg-Buildkonfiguration und entsprechende Quellen; Modellgewichte-Rechte (u. a. U2NETP und DnCNN); SBOM, native Runtime-Bibliotheken und Schutz vor Quelldateiüberschreibung.
4. **Windows-11-Clean-Machine:** echte Ausführung unter Windows 11 x64 ohne Entwicklungsumgebung, Skalierung/Accessibility, Formate/Codecs, Abbrüche, Leistung und Ressourcenlimits.
5. **Veröffentlichung:** rechtliche Freigabe, dokumentierte Einschränkungen, Hashes, Herkunft und Versionskennung. Signierung für stabile Endnutzerdistribution vorsehen.

**Status:** Der Quellcode ist öffentlich. **Es gibt keine genehmigte öffentliche Windows-ZIP.** Erfolgreiche CI-Jobs allein ersetzen diese Freigaben nicht. Der private Prerelease-Workflow bleibt im öffentlichen Repository deaktiviert. [Checkliste](PUBLIC_RELEASE_CHECKLIST.md) · [Lizenzen](../THIRD_PARTY_NOTICES.md) · [Testnachweise](VERIFICATION.md).
