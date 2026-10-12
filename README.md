# localAiPhotoEditor

Ein einfacher Fotoeditor mit lokaler KI: Foto öffnen, bearbeiten, den Hintergrund entfernen und eine neue Bilddatei speichern. Deine Fotos bleiben dabei auf deinem Computer.

**Geprüfte portable Testalpha für Windows x64.** Das vollständige portable ZIP enthält die Anwendung, ihre Laufzeit und das Standardmodell. Eine separate Python-, CUDA- oder Modellserver-Einrichtung gehört nicht zum vorgesehenen Start. Die Alpha ist **unsigniert** und noch keine stabile Endnutzer-Version.

Bestätigt sind **69 erfolgreiche Windows-Tests** sowie echte KI-Ausführung und eine funktionierende deutsche und englische Oberfläche sowohl aus dem Quellcode als auch aus der kompilierten Anwendung. Der Pakettest umfasst außerdem Bildimport und PNG/JPEG/WebP-Export nach dem Start der Oberfläche. **Separate Offline-Prüfung:** KI-Worker und Oberfläche bestanden auch die Prüfung des heruntergeladenen Pakets mit gesperrtem ausgehendem Netzwerkzugriff der Anwendung auf Windows Server 2022. Nachweise und Grenzen stehen im [Verifikationsprotokoll](docs/VERIFICATION.md); Aufnahmen der geprüften Paketoberfläche gibt es auf [Deutsch](docs/screenshots/ui-smoke-de.png) und [Englisch](docs/screenshots/ui-smoke-en.png).

## Start in drei Schritten

1. **[Download](https://github.com/Cenn0/LocalAiPhotoEditor/releases/download/v0.1.0-alpha.1/LocalAiPhotoEditor-0.1.0-alpha.1-windows-x64.zip)**: Lade `LocalAiPhotoEditor-0.1.0-alpha.1-windows-x64.zip` herunter. [Informationen zur Vorabversion](https://github.com/Cenn0/LocalAiPhotoEditor/releases/tag/v0.1.0-alpha.1).
2. **Entpacke das gesamte ZIP** in einen lokalen Ordner. Das Archiv enthält den obersten Ordner `LocalAiPhotoEditor/` mit der Anwendung und allen benötigten Unterordnern.
3. Öffne den entpackten Ordner `LocalAiPhotoEditor` und starte darin `LocalAiPhotoEditor.exe`. Öffne ein Foto, wähle eine Bearbeitung und exportiere das Ergebnis unter einem neuen Dateinamen.

Die Prüfsumme des Downloads steht im separaten Release-Asset `SHA256SUMS.txt` derselben Vorabveröffentlichung.

Die erste Zielplattform ist **Windows 11 x64**. Der dokumentierte automatisierte Testrechner verwendet Windows Server 2022. Eine vollständige Abnahme auf einer frischen Windows-11-Installation ohne Entwicklungswerkzeuge steht noch aus.

## Funktionen der Alpha

- JPEG-, PNG- und WebP-Fotos öffnen.
- Helligkeit, Kontrast und Farbsättigung mit einer Vorschau einstellen und anschließend anwenden.
- Fotos drehen, zuschneiden und ihre Größe ändern.
- Den Hintergrund mit einem mitgelieferten lokalen KI-Modell entfernen.
- Original und Ergebnis vergleichen; Änderungen rückgängig machen oder wiederholen.
- PNG, JPEG oder WebP exportieren; die Oberfläche auf Deutsch oder Englisch verwenden.

**Die Originaldatei bleibt geschützt.** Der Export verlangt ein anderes Ziel. PNG und WebP können Transparenz erhalten; bei JPEG werden transparente Stellen weiß. Die Ausgabe übernimmt keine EXIF-, GPS- oder Kommentardaten des Eingabebildes und enthält ein sRGB-Farbprofil.

## Das lokale Standardmodell

**U2NETP** erkennt den Vordergrund und erstellt eine Freistellmaske. Das kompakte Modell läuft über **ONNX Runtime auf der CPU** und wird im vollständigen Paket mitgeliefert. Beim Laden werden seine festgelegte Dateigröße und sein SHA-256 geprüft. Die App lädt fehlende Modelle nicht selbst nach.

Die Maske verändert die Transparenz, während die ursprünglichen RGB-Pixel erhalten bleiben. Gesicht oder Kleidung werden nicht neu gezeichnet. Gerade bei Haaren, Fell, Glas und ähnlichen Vorder- und Hintergrundfarben können fehlerhafte Ränder oder fehlende Bildbereiche entstehen. Es gibt noch keine veröffentlichte Qualitätsmessung. Herkunft, Prüfsummen, Lizenzabgrenzung und spätere Modellkandidaten stehen in [MODELS.md](docs/MODELS.md).

Die Anwendung hat keine Konten, Cloud-Anbindung, Analyseberichte oder automatischen Laufzeit-Updates. KI-Aufträge laufen in einem eigenen lokalen Prozess. Das Herstellen und Herunterladen des vollständigen Pakets benötigt Internetzugriff; die Bildbearbeitung ist für den lokalen Betrieb ausgelegt.

Temporäre Auftragsdateien liegen lokal. Nach einem erzwungenen Prozess- oder Systemabbruch können Reste zurückbleiben. Wählst du einen synchronisierten Ordner als Exportziel, kann dessen Synchronisierungsdienst die Datei übertragen.

## Technologie und Architektur

| Baustein | Aufgabe |
| --- | --- |
| Python 3.12 | Anwendungslogik und Verbindung der Komponenten |
| PySide6 6.12 / Qt Widgets | Desktopoberfläche auf Deutsch und Englisch |
| Pillow und NumPy | Bildimport, Farbverarbeitung, Anpassungen und Export |
| ONNX Runtime CPU + U2NETP | Lokale Hintergrundentfernung |
| Nuitka 4.2.2 | Vollständiges Windows-Paket mit eingebundener Laufzeit |

Die Bildlogik ist von Oberfläche und KI getrennt. Ein eigener KI-Prozess hält die Oberfläche bedienbar und ermöglicht den Abbruch eines Auftrags. Python und Qt halten diese erste Version in einer Anwendungssprache; der Vergleich mit Tauri/Rust und C# sowie die Gründe für diese Wahl stehen im [Projektkonzept](docs/CONCEPT.md). Die konkrete Aufteilung beschreibt die [Architektur](docs/ARCHITECTURE.md).

## Ehrliche Grenzen

- Unterstützt werden passende **8-Bit-Einzelbilder bis 40 Millionen Pixel**. RAW-, 16-Bit-, animierte und mehrseitige Dateien gehören nicht zur Alpha.
- Die EXIF-Ausrichtung wird berücksichtigt. Gültige eingebettete Farbprofile werden nach sRGB umgerechnet; ungültige oder nicht unterstützte Profile werden abgelehnt. RGB-, Graustufen- und Palettenbilder ohne Profil gelten als sRGB. CMYK und LAB benötigen ein gültiges eingebettetes Profil.
- Der Verlauf liegt im Arbeitsspeicher und ist begrenzt. Große Fotos behalten weniger rückgängig machbare Schritte; das Original bleibt während der Bearbeitung verfügbar.
- Es gibt noch keine dauerhaft gespeicherten Projekte, Ebenen, Bearbeitung durch Textanweisungen oder generatives Entfernen einzelner Objekte.
- GPU-Betrieb, Mindest-RAM, garantierte Geschwindigkeit, macOS- und Linux-Pakete sind noch nicht freigegeben. Signierung, umfassende Bedienprüfungen und die frische Windows-11-Abnahme bleiben offen.

## Am Quellcode arbeiten

Für die Entwicklung mit Python 3.12 im Repository-Hauptverzeichnis unter Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python tools\prepare_model.py
.venv\Scripts\python -m local_ai_photo_editor
```

Unter Linux/macOS lautet der Interpreterpfad `.venv/bin/python`. `prepare_model.py` ist ein Werkzeug für Entwicklung und Paketvorbereitung; die Anwendung ruft es nicht auf. Direkte Abhängigkeiten sind in [pyproject.toml](pyproject.toml) festgelegt. Prüfkommandos und die unterschiedlichen Aussagen von Unit-, Modell- und Pakettests stehen in [VERIFICATION.md](docs/VERIFICATION.md).

## Dokumentation und Lizenz

- [Konzept, Zielgruppe und Technologievergleich](docs/CONCEPT.md)
- [Architektur und Modulgrenzen](docs/ARCHITECTURE.md)
- [KI-Modell, Herkunft und Grenzen](docs/MODELS.md)
- [Prüfergebnisse und offene Nachweise](docs/VERIFICATION.md)
- [Roadmap](docs/ROADMAP.md)
- [Drittkomponenten und Lizenzhinweise](THIRD_PARTY_NOTICES.md)

Der Anwendungscode steht unter **Apache-2.0**. Bibliotheken und Modelle behalten ihre jeweiligen Lizenzen. Die Lizenz des U-2-Net-Quellprojekts und die Herkunft des separat bereitgestellten ONNX-Artefakts werden in den Modell- und Dritthinweisen ausdrücklich getrennt betrachtet.
