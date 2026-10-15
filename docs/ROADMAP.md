# Edivora – Roadmap

**Aktualisiert am 14.10.2026.** Diese Roadmap trennt **bereits im Quellcode implementiert**, **als Release nachgewiesen** und **geplante** Funktionen. Eine Entwicklungsversionsnummer ist **keine** veröffentlichte Paketfreigabe.

## Historischer Foto-Testbuild: v0.1.0-alpha.1

Das frühere, **unsignierte** Windows-x64-Testpaket enthielt Import/Export von JPEG, PNG und WebP, Grundkorrekturen, Undo/Redo, DE/EN und lokale U2NETP-Hintergrundentfernung. Er wurde auf Windows Server 2022 inklusive Offline-KI-Ausführung und GUI getestet. **Kein Video-/Audioeditor, kein Launcher, keine `.laip/.edvp/.edap`-Projekte** in diesem Paket. [Verifikationsprotokoll](VERIFICATION.md).

## Aktueller `main`-Quellcode: 0.3.0a1

**Öffentlicher Quellcode:** Die aktuelle Suite liegt in `main`. Öffentliche Windows-Binärpakete sind **noch nicht lizenzrechtlich freigegeben**. Historische Pakete und Actions-Artefakte werden bis zum Abschluss der Prüfung zurückgezogen; der private Prerelease-Workflow bleibt für öffentliche Repositorys deaktiviert.

**Implementiert, noch nicht als gleichwertiger neuer Endnutzerdownload freigegeben:**

- Gemeinsamer Edivora-Launcher mit einzeln, zu zweit oder zu dritt parallel geöffneten, unabhängigen Foto-/Video-/Audio-Prozessen.
- Foto: geführte Korrekturen, Looks, Motivwahl-/Hintergrundeffekte, manuelle Alphamaskenkorrektur und `.laip`-Fotoarchive.
- Video: geordnete **Single-Lane-Timeline bis 24 Clips**, Drag & Drop, Schnitt-/Duplizierfunktionen, `.edvp`-Projekt und lokaler FFmpeg-MP4-Export.
- Audio: dieselbe Grund-Timeline bis 24 Clips, Pegel/Fades, `.edap`-Projekt und FFmpeg-WAV-/MP3-Export.
- Echte lokale **U2NETP-Standbild-Freistellung** im Videoeditor und **Silero-VAD-Sprachaktivitätsvorschläge** im Audioeditor; CPU-ONNX mit fest geprüften Modellen und ohne Runtime-Downloads.
- Zentrales Dark-Theme und zweisprachige Beschriftungen. Markendarstellung mit Edivora-Logo und dokumentierten Vektorassets ist im begleitenden Branding-Änderungssatz integriert, **nicht** im zuvor veröffentlichten ZIP.

[Umfang und Grenzen](MEDIA_MVP.md) · [Mediendateien, Render und KI](MEDIA_PROJECTS_AI.md) · [UI-Designsystem](DESIGN_SYSTEM.md).

## Nächste mögliche Entwicklungsstufe: Modellprofile

Ein **separater, noch offener PR #17** schlägt CPU-Modellprofile, ressourcenbewusste automatische oder manuelle Auswahl, ein größeres Bildsegmentierungsmodell und Offline-Transkription vor. **Diese Funktionen sind nicht Bestandteil von `main` 0.3.0a1 oder des alten Releases.** Nur nach Merge, Tests, Modell-/Lizenzprüfung und aktualisierten Produktgrenzen den Status ändern.

## Offene Produktfunktionen

- Eine **kontinuierliche Gesamtvorschau** der zusammengesetzten Video-/Audioreihenfolge.
- Mehrere **überlagerbare Spuren**, Übergänge, präzise Audio-/Videomischung, Medien-Undo-/Redo und Autosave.
- Media-Relinking, portable Paketprojekte, breitere Decoder-/Encoder-/Codec-Matrix und gemessene Qualitäts-/Performanceprofile.
- Optional: verbesserte KI-Maskenqualität, Video-KI über zusammenhängende Frames, lokale Transkription/Untertitel, Rauschminderung. Nur als implementiert kennzeichnen, wenn tatsächlich gemergt und überprüft.
- Langfristig: lokale generative Fotoänderungen **nur** nach vollständig gepinnter Modellkette, geprüfter Lizenz, RAM/GPU-Messungen, Masken-Isolation, Preview/Accept/Cancel und Crash-Recovery. Ein Modellkandidat allein ist keine unterstützte Funktion.

## Release-Gates vor einer neuen öffentlichen Windows-Suite

1. **Code + echte Modelle:** Testmatrix mit echten ONNX-Gewichten, Media-/Foto-Ein- und Ausgabe, DE/EN und für relevante Änderungen GPU nur mit tatsächlich geprüfter Laufzeit.
2. **Paket:** Exakter Standalone-Windows-Build einschließlich eingebetteter Vektorlogos, KI-Gewichte, Qt- und FFmpeg-Runtime; separater Test des **heruntergeladenen** Artefakts unter nachweisbarer Netzwerksperre.
3. **Lizenz-/Sicherheitsprüfung:** Qt-LGPL-Pflichten, tatsächliche FFmpeg-Binary-/Codec-GPL/LGPL-Bedingungen und entsprechende Quellen; Rechte an externen Modellgewichten; Schutz vor Dateiverlust, Symlink-/Hardlink-Aliassen und ungeprüften Medien/Projekten.
4. **Windows 11 Clean Machine:** reale Import-/Preview-/Export-Workflows, Codec-Stichproben, DPI/Accessibility, RAM/CPU und Fehlerfälle auf einer frischen Windows-11-x64-Umgebung.
5. **Veröffentlichung:** Build-Commit, Hash, Release Notes, bekannte Einschränkungen, Lizenzinventar und klare Kennzeichnung als **Testalpha** oder verifizierter Release. Für stabilen Release ist Windows-Signierung vorzusehen.

Bis diese Gates abgeschlossen sind, sind neue Quellcode-Features **nicht** als freigegebene Windows-Suite zu bezeichnen. [Beitragen](CONTRIBUTING.md) · [Nachweise](VERIFICATION.md).
