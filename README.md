# localAiPhotoEditor

Ein Fotoeditor für Menschen, die Bilder einfach bearbeiten möchten und ihre Fotos auf dem eigenen Computer behalten wollen.

**Status: frühe Entwicklungs-Alpha. Es gibt noch keine geprüfte Endnutzer-Version und kein freigegebenes portables Paket.** Im abgeschlossenen [dritten Windows-Lauf](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38303734085) bestanden alle **62 Tests**. Die lokale KI funktioniert sowohl aus dem Quellcode als auch aus der gebauten Anwendung. Die deutsche und englische Oberfläche startet aus dem Quellcode; die Oberfläche des Pakets bricht beim Start jedoch mit Exit-Code 3 ab. Deshalb ist das Paket noch nicht zum Ausprobieren freigegeben. Nachweise und Grenzen stehen im [Verifikationsprotokoll](docs/VERIFICATION.md).

## Was du damit machen kannst

Der vorgesehene Ablauf ist: Foto öffnen, eine verständlich benannte Funktion wählen, das Ergebnis mit dem Original vergleichen und eine Kopie exportieren.

Die Alpha umfasst:

- JPEG-, PNG- und WebP-Fotos öffnen.
- Helligkeit, Kontrast und Farbsättigung ändern.
- Fotos drehen, zuschneiden und ihre Größe ändern.
- Den Hintergrund mit einem mitgelieferten lokalen KI-Modell entfernen.
- Änderungen rückgängig machen, wiederholen und zum Original zurückkehren.
- PNG, JPEG oder WebP exportieren; die Bedienoberfläche ist für Deutsch und Englisch vorgesehen.

**Die Originaldatei bleibt geschützt.** Der Export verlangt einen anderen Dateinamen. PNG und WebP können einen transparenten Hintergrund behalten; JPEG bekommt an transparenten Stellen einen weißen Hintergrund. Übernommene EXIF-, GPS- und Kommentardaten werden beim Export entfernt. Die Ausgabe enthält ein sRGB-Farbprofil.

Die KI-Funktion erkennt einen Vordergrund und erzeugt eine Freistellmaske. Sie zeichnet Gesicht, Kleidung oder andere Bildinhalte nicht neu. Fehlerhafte Ränder oder versehentlich entfernte Bereiche sind trotzdem möglich. Die Alpha unterstützt noch keine Bearbeitung durch Textanweisungen, generatives Entfernen einzelner Objekte, RAW-Entwicklung oder dauerhaft gespeicherte Projekte mit Ebenen. Modellwahl und Grenzen sind in [MODELS.md](docs/MODELS.md) beschrieben.

## Ausprobieren unter Windows

Erstes Ziel ist **Windows 11 x64**. Die Auslieferung der Alpha ist als **portables ZIP mit Programm, Laufzeit und KI-Modell** vorgesehen. Ein Installer wird für diesen ersten Build nicht versprochen. Im vollständigen Paket soll keine separate Installation von Python, CUDA oder einem Modellserver nötig sein; der entsprechende Test auf einem frischen Windows-System steht noch aus.

Der zuletzt abgeschlossene [Windows-Lauf](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38303734085) stellt wegen des fehlgeschlagenen Oberflächenstarts kein freigegebenes portables Paket bereit. Sobald ein späterer Lauf Paketbau und Paketprüfungen erfolgreich abschließt:

1. Öffne [GitHub Actions](https://github.com/Cenn0/LocalAiPhotoEditor/actions) und wähle den Workflow **Windows alpha**.
2. Öffne einen erfolgreich abgeschlossenen Lauf und lade unter **Artifacts** das Paket **LocalAiPhotoEditor-windows-x64-alpha** herunter.
3. Entpacke das heruntergeladene ZIP vollständig in einen Ordner. `LocalAiPhotoEditor.exe` liegt direkt im Wurzelverzeichnis des ZIP.
4. Starte `LocalAiPhotoEditor.exe` aus dem entpackten Ordner. Belasse sämtliche mitgelieferten Dateien und Unterordner bei der Anwendung.

**Ein Actions-Artefakt ist ein Vorabpaket für Tests.** Ein grüner Build allein belegt weder die Qualität der Freistellung noch den erfolgreichen Offlinebetrieb auf einem frischen Windows-Rechner. Fehlt ein erfolgreiches Artefakt, ist über diesen Weg noch kein Paket verfügbar. Freigegebene Versionen gehören später auf die [Releases-Seite](https://github.com/Cenn0/LocalAiPhotoEditor/releases).

## Was „lokal“ bedeutet

Die Anwendung hat keine Konten, Cloud-Anbindung, Analyseberichte, automatische Modell-Downloads oder Laufzeit-Updates. Der KI-Auftrag wird in einem eigenen Prozess auf dem Computer ausgeführt. Internetzugriff ist für das Herstellen eines vollständigen Pakets vorgesehen, nicht für die spätere Bildbearbeitung.

Temporäre Eingaben und Ergebnisse liegen lokal und sollen nach Abschluss oder Abbruch des Auftrags entfernt werden. Ein erzwungener Prozess- oder Systemabbruch kann Dateien zurücklassen; diese Arbeitsdateien sind nicht verschlüsselt. Wenn du selbst einen synchronisierten Ordner als Speicherziel wählst, kann dessen Synchronisierungsdienst die exportierte Datei übertragen.

Die Umsetzung und die noch ausstehende Prüfung des vollständigen Pakets sind im [Architekturdokument](docs/ARCHITECTURE.md) und [Verifikationsprotokoll](docs/VERIFICATION.md) getrennt beschrieben.

## Aktuelle Grenzen

- Unterstützt werden passende **8-Bit-Einzelbilder bis 40 Millionen Pixel**. Animierte und mehrseitige Dateien sowie RAW-/16-Bit-Bearbeitung sind ausgeschlossen.
- Die Ausrichtung aus EXIF wird berücksichtigt. Gültige eingebettete Farbprofile werden nach sRGB umgerechnet; ungültige oder nicht unterstützte Profile lösen einen Fehler aus. RGB-, Graustufen- und Palettenbilder ohne Profil werden als sRGB behandelt. CMYK und LAB benötigen ein gültiges eingebettetes Profil.
- Der Verlauf bleibt im Arbeitsspeicher. Große Fotos behalten weniger rückgängig machbare Schritte. Das ursprüngliche Bild bleibt während der Bearbeitung unabhängig davon verfügbar.
- Die erste KI-Ausführung ist auf die CPU ausgelegt. GPU-Unterstützung, Mindestgeschwindigkeit und konkrete RAM-Anforderungen sind noch nicht für dieses Programm freigegeben.
- macOS- und Linux-Pakete sind spätere Ziele. Lokale Quellcode-Tests sind kein Nachweis für fertige Pakete dieser Plattformen.

## Für Entwicklerinnen und Entwickler

Die folgenden Befehle sind für die Arbeit am Quellcode gedacht. Der vorgesehene Einstieg für Anwender ist das vollständige Paket oben.

Mit Python 3.12 im Repository-Hauptverzeichnis, unter Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python tools\prepare_model.py
.venv\Scripts\python -m local_ai_photo_editor
```

Unter Linux/macOS lautet der Interpreterpfad `.venv/bin/python`. Direkte Abhängigkeiten sind in [pyproject.toml](pyproject.toml) festgelegt. Ein vollständig mit Hashes gesperrter Satz aller transitiven Abhängigkeiten ist noch kein vorhandenes Versprechen.

`prepare_model.py` ist ausschließlich ein Werkzeug zum Vorbereiten des Pakets. Beim Download prüft es Dateigröße, den festgelegten SHA-256 und den upstream angegebenen MD5-Kompatibilitätswert. Die Anwendung selbst ruft es nicht auf. Die Herkunft der Prüfsummen steht in [MODELS.md](docs/MODELS.md). Das tatsächliche Modell wurde im Windows-Quellcode-Worker und im Worker der kompilierten EXE mit Integritätsprüfung erfolgreich ausgeführt. Der noch fehlgeschlagene Start der Paketoberfläche ist im [Verifikationsprotokoll](docs/VERIFICATION.md) dokumentiert.

### Prüfungen ausführen

Nach Installation der Entwicklungsabhängigkeiten:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
.venv\Scripts\python -m local_ai_photo_editor --smoke-test smoke-output
```

Im zuletzt abgeschlossenen Windows-Lauf bestanden **62 von 62 Tests ohne übersprungene Tests** für Commit `121d702f89885c9803a2dcc930ef02340607295f`. Die lokale Vergleichsbasis und die genaue Aussage der Paketprüfungen stehen im [Verifikationsprotokoll](docs/VERIFICATION.md). Ohne installierte Qt-Laufzeit werden die entsprechenden lokalen Tests ausdrücklich übersprungen.

Der letzte Befehl benötigt das echte Modell und ONNX Runtime sowie ein noch nicht vorhandenes Ausgabeverzeichnis. Er erzeugt ein synthetisches Testbild und einen Ergebnisbericht. Tests mit künstlichen Masken oder Ersatzdaten bestätigen keine erfolgreiche Modellinferenz. Das gebaute Windows-Programm muss zusätzlich separat geprüft werden.

## Projektentscheidungen

- [Konzept, Zielgruppe und Technologievergleich](docs/CONCEPT.md)
- [Architektur und Modulgrenzen](docs/ARCHITECTURE.md)
- [KI-Modelle, Herkunft und Lizenzabgrenzung](docs/MODELS.md)
- [Roadmap und Abnahmekriterien](docs/ROADMAP.md)
- [Tatsächlich durchgeführte Prüfungen](docs/VERIFICATION.md)
- [Verwendete Drittkomponenten](THIRD_PARTY_NOTICES.md)

## Lizenz

Der Anwendungscode steht unter **Apache-2.0**. Bibliotheken und Modelle behalten ihre jeweiligen Lizenzen. Die Lizenz des U-2-Net-Quellprojekts und die Herkunft des über rembg bereitgestellten ONNX-Artefakts werden ausdrücklich getrennt betrachtet; Details stehen in [MODELS.md](docs/MODELS.md) und den [Dritthinweisen](THIRD_PARTY_NOTICES.md).
