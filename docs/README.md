# Edivora – Dokumentation

![Edivora Bildmarke](../src/local_ai_photo_editor/assets/edivora-mark.svg)

Diese Dokumentation beschreibt zwei **unterschiedliche** Softwarestände: das veröffentlichte, historische Foto-Alpha-Paket **\`v0.1.0-alpha.1\`** und die neuere **Edivora-Suite im Quellcode (0.3.0a1)**. Die aktuelle Quellcode-Suite verfügt über Foto-, Video- und Audiobearbeitung, aber es liegt **keine entsprechend freigegebene neue Windows-Version** vor. Der alte Paketprüfnachweis darf nicht auf aktuelle Features übertragen werden.

## Anwenden

- [Erste Schritte – Installation, Arbeitsabläufe, Projekte und Fehlerhilfe](GETTING_STARTED.md)
- [Video-/Audio-Launcher und aktuelle MVP-Funktionen](MEDIA_MVP.md)
- [Mehrclip-Projekte, lokale Medien-KI und technische Einschränkungen](MEDIA_PROJECTS_AI.md)
- [Foto bearbeiten: Licht, Farbe, Looks und Hintergrund](EDITING_TOOLS.md)
- [Foto-Motivwerkzeuge und KI-Auswahl](AI_SUBJECT_TOOLS.md)
- [Manuelle Maskenkorrektur](MASK_REFINEMENT.md)
- [Foto-Projektformat \`.laip\`](PROJECT_FORMAT.md)

## Verstehen und erweitern

- [Mitwirken – auch mit KI-Assistenten](CONTRIBUTING.md) und [verbindliche Regeln](../AGENTS.md)
- [Architektur, Komponenten, Datenschutzgrenzen](ARCHITECTURE.md)
- [Lokale Modelle, Herkunft, Lizenzen](MODELS.md)
- [Konzept und historische Anfangsentscheidungen](CONCEPT.md)
- [Designsystem](DESIGN_SYSTEM.md), [UI-Implementierungsstand](UI_IMPLEMENTATION.md) und [interaktiver **Prototyp**, keine App](prototypes/edivora-shell.html)
- [Markenführung, Logos und Assets](BRAND.md)
- [Roadmap und offene Release-Gates](ROADMAP.md)

## Verifikation, Builds und rechtliche Hinweise

- [Nachweise für das **historische** Foto-Alpha-Paket](VERIFICATION.md)
- [Release Notes der ursprünglichen Alpha](RELEASE_NOTES_ALPHA.md)
- [Drittanbieter und Lizenzhinweise](../THIRD_PARTY_NOTICES.md) sowie [Qt-Quellen/Lizenzen](QT_SOURCES.md)
- [Windows-Paketanleitung](../packaging/START_HERE.txt) – gilt für den Entwicklungsbuild und ist kein neues Releaseversprechen

**Statuskennzeichnung:** „Implementiert im Quellcode“ ist **nicht** „offiziell als Windows-Paket abgenommen“. „CPU-Modell integriert“ ist **nicht** „GPU offiziell unterstützt“ oder „KI-Qualität garantiert“. Für Änderungen im Repository sind eigene Prüfprotokolle mit Branch-/Commitbezug erforderlich.
