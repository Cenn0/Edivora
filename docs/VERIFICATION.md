# Verifikationsprotokoll – historische Foto-Testalpha

**Gültigkeitsbereich: ausschließlich `v0.1.0-alpha.1` (Foto-Release, Commit `2b1682b7…`).** Dieses Protokoll belegt **keine** Ausführung oder Freigabe des späteren Edivora-Launchers, der Video-/Audio-Mehrclip-Editoren, der neuen `.laip/.edvp/.edap`-Funktionen oder der eingebundenen Markenassets. Der neue Quellstand benötigt eigene Source-/Windows-/Offline-/Lizenznachweise.

**Für den genau unten identifizierten historischen Windows-Build wurden die Paketprüfungen erfolgreich abgeschlossen.** 69 von 69 Tests bestanden ohne Skips. Tatsächliche U2NETP-Ausführung und native Oberfläche auf Deutsch und Englisch funktionieren sowohl aus dem Quellcode als auch aus der kompilierten EXE. PNG-Import sowie PNG/JPEG/WebP-Export nach Qt-Initialisierung wurden ebenfalls bestätigt. **Ergebnis des separat heruntergeladenen Pakets unter Netzwerksperre:** Erfolgreich: echter KI-Worker und native Oberfläche mit Exit-Code 0 unter einem nachgewiesen wirksamen ausgehenden Firewallblock für die Anwendung.

## Geprüfter Stand und Paketidentität

| Feld | Nachweis |
| --- | --- |
| Anwendungscode | [`2b1682b74bd406238865e0b6f8ad1ed151890032`](https://github.com/Cenn0/LocalAiPhotoEditor/commit/2b1682b74bd406238865e0b6f8ad1ed151890032) |
| Windows-Build | [Windows alpha, Lauf 38311556834](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38311556834) |
| Umgebung | Windows Server 2022, Python 3.12, CPU-Ausführung |
| Paketwerkzeug | Nuitka **4.2.2**, PySide6 **6.12.0** |
| Actions-Artefakt | `LocalAiPhotoEditor-windows-x64-alpha`; ID **11775901053** |
| Größe des Actions-Artefakts | **70.652.403 Bytes** |
| SHA-256 des Actions-Artefakts | `0abda2fb998a43ce01ef989ed51fd4dfa128de006f3956ccd4c725c7b34e70b9` |
| SHA-256 der enthaltenen EXE | `cc8ab845f93310a63b16187a5143fef43d71e98dbf55b7aaf4f098457fc5cb8a` |
| Vorabversions-Tag | `v0.1.0-alpha.1` |
| Portable Vorabversion mit Paketnachweisen | [Paketinformationen](https://github.com/Cenn0/LocalAiPhotoEditor/releases/tag/v0.1.0-alpha.1) |
| Release-Asset | `LocalAiPhotoEditor-0.1.0-alpha.1-windows-x64.zip` |
| Prüfsumme des Release-ZIP | Separates Release-Asset `SHA256SUMS.txt` in der oben verlinkten Vorabveröffentlichung |
| Download des Release-ZIP | https://github.com/Cenn0/LocalAiPhotoEditor/releases/download/v0.1.0-alpha.1/LocalAiPhotoEditor-0.1.0-alpha.1-windows-x64.zip |
| Separater Offline-Lauf | [Offline-Paketprüfung 38313711747](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38313711747) |
| Veröffentlichungskanal | Unsignierte Entwicklungs-Alpha; keine stabile Endnutzer-Version |

Das Actions-Artefakt wurde heruntergeladen und sein SHA-256 gegen den oben angegebenen Wert geprüft. `build-info.json` im Paket dokumentiert dessen tatsächlichen Buildcommit, Python-Version, Plattform, Modell-SHA-256 und Veröffentlichungskanal. `build-resolved.txt` sowie die Lizenzinventare dokumentieren die aufgelösten Abhängigkeiten. Eine spätere Dokumentationskorrektur ändert die Identität des kompilierten Anwendungscodes nicht. Beim Zusammenstellen ergänzt `distribution-info.json` die Zuordnung zum endgültigen Dokumentationsstand; die Identität des kompilierten Anwendungscodes bleibt erhalten.

Das Release-ZIP enthält den obersten Ordner `LocalAiPhotoEditor/`. Nach dem vollständigen Entpacken wird `LocalAiPhotoEditor.exe` innerhalb dieses Ordners gestartet. Der oben eingetragene Actions-Artefakt-Hash und die separate Prüfsummendatei des Release-ZIP kennzeichnen jeweils das konkrete Archiv; sie werden nicht gleichgesetzt. Der Offline-Nachweis bezieht sich auf das darin ausdrücklich identifizierte Download-Artefakt.

## Bestätigte Ergebnisse

| Prüfung | Ergebnis | Was dadurch belegt wird |
| --- | --- | --- |
| Windows-Testsuite | **69 bestanden, keine übersprungenen Tests.** | Die geprüften Core-, KI-, Laufzeit- und Oberflächenverträge in der installierten Python-Umgebung des Runners. |
| Echter Quellcode-KI-Worker | **Erfolgreich.** | Tatsächliche Inferenz mit dem festgelegten lokalen U2NETP-Modell und ONNX Runtime CPU; keine Ersatzmaske. |
| Native Quelloberfläche | **Erfolgreich.** | Qt-Start, deutsche und englische Bildschirmaufnahmen sowie reguläres Beenden. Nach Qt-Initialisierung wurden Bildimport und alle drei Exportformate geprüft. |
| Nuitka-Standalone-Bau | **Mit Nuitka 4.2.2 erfolgreich abgeschlossen.** | Herstellung des vollständigen Anwendungspakets für den angegebenen Commit. |
| Echter KI-Worker der EXE | **Status `ok`, `CPUExecutionProvider`.** | Tatsächliche Inferenz aus der kompilierten Anwendung und dem mitgelieferten Modell. |
| Native Oberfläche der EXE | **Status `ok`, Qt-Plattform `windows`, DE/EN-Aufnahmen mit jeweils 1028 × 749 Pixeln; Ereignisschleife mit Exit-Code 0 beendet.** | Paketstart, Darstellung, Bildimport/-export nach Qt-Initialisierung und reguläres Beenden im dokumentierten Umfang. PNG und WebP bewahrten die exakten Pixel; bei JPEG wurden Dimensionen und RGB-Modus bestätigt. |
| Portables Actions-Artefakt | **Erfolgreich bereitgestellt und heruntergeladen; Archiv-SHA-256 bestätigt.** | Bereitstellung des oben eindeutig angegebenen Build-Artefakts. |
| Portable Vorabversion | **Geprüfter Paketinhalt für `v0.1.0-alpha.1`.** | Das Release-ZIP übernimmt die geprüften Binärdateien; Dokumentation und Archivstruktur werden beim Zusammenstellen ergänzt. |
| Erneut heruntergeladenes Paket unter ausgehendem EXE-Netzwerkblock | **Status `ok`; Worker und GUI mit Exit-Code 0, wirksame Sperre und Entfernen der temporären Regel bestätigt** | Ergebnis des separaten Workflows mit der unten beschriebenen Umgebung und Sperre. |

Die Laufnachweise enthalten die erfolgreichen Berichte unter `test-results/source-worker/`, `test-results/source-gui/`, `test-results/frozen-worker/` und `test-results/frozen-gui/`. Die KI-Berichte nennen Modell-SHA-256, Ausführungsanbieter und Workerabschluss. Die GUI-Berichte enthalten Sprachaufnahmen, Bild-I/O-Prüfungen und den Exit-Code der Ereignisschleife. Die Aufnahmen der kompilierten Anwendung sind auch auf [Deutsch](screenshots/ui-smoke-de.png) und [Englisch](screenshots/ui-smoke-en.png) verfügbar.

## Was die unterschiedlichen Prüfungen aussagen

**Unit- und Oberflächentests:** Die [Coretests](../tests/test_core.py) prüfen unter anderem EXIF-Ausrichtung, ICC-Konvertierung und Profilfehler, Transparenz, das Pixel-Limit, unveränderte Eingaben, begrenztes Undo/Redo, Exportmetadaten und Originalschutz einschließlich Datei-Aliasen. Simulierte Schreibfehler prüfen, dass ein bestehender Export erhalten bleibt. Die [Adaptertests](../tests/test_ai.py) verwenden für einzelne Verträge synthetische Bilder, berechnete Masken und Ersatzdaten. Sie ersetzen keinen Lauf des echten Modells. Lokale Tests ohne Qt weisen die übersprungenen Qt-Fälle ausdrücklich aus; diese lokalen Skips sind nicht Bestandteil der 69 erfolgreichen Windows-Tests.

**Tatsächliche Modellinferenz:** Der separate Worker-Smoke lädt das echte, auf Größe und SHA-256 geprüfte Modell und erzeugt ein Ergebnisbild. Sein begrenzter Umfang ist `worker_runtime_only`. Ein Erfolg bestätigt die ausgeführte Inferenz-/Exportstrecke, keine Freistellqualität an realen Fotos und keinen vollständigen Bedienablauf in der Oberfläche.

**Native Oberfläche und Bild-I/O:** Nach `QApplication` und `EditorWindow` wird eine synthetische Grafik als PNG exportiert, wieder importiert und als Dokument angezeigt. PNG und WebP werden beim Export auf übereinstimmende RGBA-Pixel geprüft; bei JPEG werden die Dimensionen und der RGB-Modus geprüft. JPEG ist verlustbehaftet, weshalb dafür keine pixelgenaue Übereinstimmung zugesagt wird. DE/EN-Aufnahmen und reguläres Beenden ergänzen diese Prüfung. Die automatisierten Aufrufe bedienen nicht jeden Dateidialog oder jeden Bearbeitungsschritt wie ein Mensch.

## Separater Offline-Prüfumfang

**Erfolgreich am 12. Oktober 2026 im [Offline-Lauf 38313711747](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38313711747).** Der Bericht meldet `status: ok`, `offline_enforcement_confirmed: true` und `rule_removal_verified: true`. Worker und Oberfläche endeten mit Code 0; `same_executable_worker_confirmed: true` bestätigt die Verwendung derselben gesperrten EXE für den KI-Auftrag. Die EXE-Prüfsumme entspricht dem oben angegebenen Windows-Build.

| Zusätzlicher Offline-Nachweis | Identität |
| --- | --- |
| Prüfharness-Commit | [`6d75397a8cf4ca6f573c650033b6f4018f650b1f`](https://github.com/Cenn0/LocalAiPhotoEditor/commit/6d75397a8cf4ca6f573c650033b6f4018f650b1f) |
| Nachweis-Artefakt | ID **11775129907**, **125.337 Bytes** |
| SHA-256 des Nachweis-Artefakts | `abaf7edaa502118f1d0c7de5d32df3bb66a4f0eef7376973c620c010888bfdc5` |

Auch dieses Nachweis-Artefakt wurde heruntergeladen und seine Prüfsumme bestätigt. Der Prüfharness-Commit bezeichnet die separate Prüfung, nicht einen anderen Anwendungscode.

Der abgeschlossene [Workflow für die Prüfung des heruntergeladenen Pakets](https://github.com/Cenn0/LocalAiPhotoEditor/blob/6d75397a8cf4ca6f573c650033b6f4018f650b1f/.github/workflows/offline-package-check.yml) ist vom Build getrennt. Folgende Schritte wurden erfolgreich ausgeführt:

- Das eindeutig ausgewählte Portable-Artefakt eines erfolgreichen Windows-Laufs herunterladen und seinen SHA-256 überprüfen.
- Das Paket auf einem weiteren Windows-Server-2022-Runner ohne Checkout, Python-Einrichtung oder Installation von Projektabhängigkeiten starten.
- Einen neuen Paketpfad und ein anfangs leeres Arbeitsverzeichnis verwenden; Python-Umgebungsvariablen entfernen und den `PATH` des gestarteten Prozesses auf Windows-Verzeichnisse beschränken.
- Einen ausgehenden Windows-Firewallblock für genau die heruntergeladene EXE einrichten und dessen aktive Durchsetzung vor und nach den Prüfungen kontrollieren. Der KI-Worker muss dieselbe blockierte EXE verwenden.
- Echten Paket-Worker und native Oberfläche einschließlich der im GUI-Smoke enthaltenen Bild-I/O-Prüfungen ausführen und die vorübergehende Firewallregel wieder entfernen.

Die Belege dazu sind `source-artifact.json`, `environment.json`, die Firewall-Snapshots, Worker-/GUI-Berichte und `offline-package-result.json` des angegebenen Offline-Laufs. Die aktive Public-Firewall war eingeschaltet; die wirksame Regel blockierte ausgehenden Verkehr der genauen EXE für alle Adressen, Ports und Protokolle. Die nach Qt-Initialisierung ausgeführten Bild-I/O-Prüfungen bestanden auch in diesem Lauf.

Dieser erfolgreiche Test erfolgte **nicht auf einer frischen Windows-11-Installation ohne vorhandene Entwicklungssoftware**. Der Runner kann vorinstallierte Systemkomponenten enthalten. Gesperrt wird der ausgehende Netzwerkzugriff der Anwendung; das Netzwerk des gesamten Rechners wird nicht abgeschaltet. Der Nachweis ist deshalb genau auf das heruntergeladene Paket und diese dokumentierte Testumgebung begrenzt.

## Kurze Fehlerhistorie

Der ursprüngliche Worker-Start über `sys.executable` verwies im betroffenen Paket auf eine nicht vorhandene `python.exe`; die Auswahl der tatsächlichen Paket-EXE korrigierte diesen Fehler. Anschließende native Abstürze wurden auf die Callback-Probe in **Nuitka 4.3** zurückgeführt ([Issue #4081](https://github.com/Nuitka/Nuitka/issues/4081)); die späteren Importabstürze bei Pillow und NumPy waren Symptome. Mit Nuitka **4.2.2** und unverändertem PySide6 **6.12.0** bestanden die Paketprüfungen.

Der erste Offline-Versuch scheiterte im PowerShell-Prüfharness vor dem Appstart. Nach Korrektur der Statuskonvertierung bestand die unveränderte Anwendung den oben angegebenen Offline-Lauf.

## Verbleibende Grenzen

- Eine frische Windows-11-x64-Installation ohne Entwicklungswerkzeuge und mit vor dem ersten Start abgeschaltetem Netzwerk wurde noch nicht vollständig abgenommen.
- Vollständige interaktive Bearbeitungsabläufe, Abbruch- und Neustartverhalten am ausgelieferten Paket, unterschiedliche Windows-Skalierungen und Barrierefreiheit bleiben gesondert zu beurteilen.
- Es gibt keine veröffentlichte Freistellqualitätsmessung, keine garantierten Inferenzzeiten und keine bestätigten Mindestanforderungen an RAM oder GPU.
- Das Paket ist unsigniert. Signierung und die dokumentierte Abnahme bleiben Voraussetzungen für die erste stabile Endnutzer-Version. Modellherkunft und Pflichten für Drittkomponenten werden durch erfolgreiche Laufzeittests nicht zusätzlich bestätigt; siehe [MODELS.md](MODELS.md) und [Dritthinweise](../THIRD_PARTY_NOTICES.md).

## Prüfungen reproduzieren

In einer vorbereiteten Entwicklungsumgebung unter Windows:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
.venv\Scripts\python -m local_ai_photo_editor --smoke-test source-worker-output
.venv\Scripts\python -m local_ai_photo_editor --ui-smoke-test source-gui-output
```

Die beiden Smoke-Prüfungen werden für das Paket separat über dessen EXE ausgeführt:

```powershell
.\LocalAiPhotoEditor.exe --smoke-test package-worker-output
.\LocalAiPhotoEditor.exe --ui-smoke-test package-gui-output
```

Ausgabeverzeichnisse dürfen noch nicht existieren. Die Workerprüfung benötigt das echte Modell und ONNX Runtime. Diese Befehle allein richten keine Netzwerksperre ein; dafür ist der separat protokollierte Offline-Workflow zuständig. Das Paket muss vollständig entpackt sein, einschließlich aller Bibliotheken, des Modells und der Unterordner.
