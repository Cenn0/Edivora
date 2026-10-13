# LocalAiPhotoEditor 0.1.0 Alpha 1

**Unsignierte, private Test-Alpha – keine stabile Endnutzer-Version.**

Diese Vorabversion bündelt die lokale Windows-x64-Desktopanwendung, Python-/Qt-Laufzeit
und das überprüfte U2NETP-ONNX-Modell. Für den vorgesehenen Start sind kein separates
Python, kein Docker, kein CUDA, kein Konto und kein Modellserver erforderlich.

## Bedienbare Funktionen

- JPEG, PNG und WebP öffnen und als neue Datei exportieren.
- Helligkeit, Kontrast, Sättigung, Zuschnitt, Drehen und Skalieren.
- Vorher/Nachher-Vergleich und begrenztes Undo/Redo.
- KI-gestützte Hintergrundentfernung mit lokaler CPU-Inferenz.
- Deutsche und englische Oberfläche; das Original wird nicht überschrieben.

## Geprüfter Umfang

- Windows-Tests: **69 bestanden, 0 übersprungen**.
- Native kompilierten EXE und KI-Worker mit echtem Modell geprüft.
- GUI-Start auf Deutsch/Englisch, PNG-Import und PNG/JPEG/WebP-Export geprüft.
- Dasselbe heruntergeladene Paket bestand den separaten Offline-Test unter einer
  nachgewiesen aktiven ausgehenden Windows-Firewallsperre für die EXE.
- [Windows-Build](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38311556834) ·
  [Offline-Prüfung](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38313711747) ·
  [Detailliertes Verifikationsprotokoll](https://github.com/Cenn0/LocalAiPhotoEditor/blob/main/docs/VERIFICATION.md).

Die Tests erfolgten auf **Windows Server 2022** und belegen nicht die vollständige
interaktive Erstinstallation und Nutzung auf einem frischen Windows-11-Rechner.
Das Paket ist **nicht signiert**. GPU-Unterstützung, Mindest-RAM, KI-Ergebnisqualität,
vollständige Barrierefreiheit und die Unterstützung weiterer Betriebssysteme
wurden nicht abgenommen. Das U2NETP-Modell kann fehlerhafte Freistellmasken erzeugen.

Die Rechte zur eigenständigen Weiterverteilung des separat bezogenen ONNX-Modellartefakts
und alle Qt/LGPL-Lieferpflichten sind für eine **öffentliche Verteilung** noch abschließend
zu prüfen. Diese Alpha bleibt deshalb vorerst im privaten Repository.

## Installation

1. `LocalAiPhotoEditor-0.1.0-alpha.1-windows-x64.zip` herunterladen und SHA-256
   mit `SHA256SUMS.txt` vergleichen.
2. Das gesamte Archiv in einen lokalen Ordner entpacken.
3. `LocalAiPhotoEditor/LocalAiPhotoEditor.exe` starten und eine **neue**
   Ausgabedatei wählen.

Die ZIP enthält `distribution-info.json`, Lizenz-/Buildinformationen sowie
den Dokumentationsstand des Release-Commits. Die kompilierten Anwendungsdateien
stammen unverändert aus dem oben verlinkten getesteten Build
`2b1682b74bd406238865e0b6f8ad1ed151890032`.

**Nicht enthalten:** Installation per Setup, generative Textanweisungen,
Ebenen und dauerhaft gespeicherte Projekte. Diese sind nicht als fertige
Funktionen dieser Alpha ausgewiesen.
