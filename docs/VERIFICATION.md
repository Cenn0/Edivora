# Verifikationsprotokoll

**Der dritte Windows-Lauf ist abgeschlossen: 62 Tests, echte KI im Quellcode und im gebauten Paket sowie die Quellcode-Oberfläche waren erfolgreich. Die native Paketoberfläche brach beim Start mit Exit-Code 3 ab. Es gibt deshalb noch kein freigegebenes portables Paket.**

## Aktuelles bestätigtes Windows-Ergebnis

Geprüfter Quellcode: Commit [`121d702f89885c9803a2dcc930ef02340607295f`](https://github.com/Cenn0/LocalAiPhotoEditor/commit/121d702f89885c9803a2dcc930ef02340607295f). Umgebung laut Buildbericht: **Windows Server 2022, Python 3.12.10**, CPU-Ausführung. Nachweis: [Windows-alpha-Lauf 38303734085](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38303734085).

| Prüfung | Bestätigtes Ergebnis | Aussagegrenze |
| --- | --- | --- |
| Vollständige Testsuite | **62 von 62 Tests bestanden, keine übersprungenen Tests.** | Die Tests laufen in der installierten Python-Umgebung des Runners. |
| Echtes U2NETP im Quellcode-Worker | **Erfolgreich**, einschließlich Integritätsprüfung des geladenen Modells; Worker-Exit-Code 0. | Begrenzte Inferenz-/Exportstrecke mit synthetischem Testbild; keine Messung der Freistellqualität. |
| Native Quellcode-Oberfläche | **Deutscher und englischer Qt-Start, Bildschirmaufnahmen und reguläres Beenden der Ereignisschleife erfolgreich.** | Kein vollständiger Test aller Dialoge, Windows-Skalierungen oder der Barrierefreiheit. |
| Bau der eigenständigen Windows-Anwendung | **Nuitka-Standalone-Bau erfolgreich abgeschlossen.** | Der Bau allein bestätigt noch keine funktionsfähige Paketoberfläche. |
| Echtes U2NETP im Worker der kompilierten EXE | **Erfolgreich**, einschließlich Integritätsprüfung; `LocalAiPhotoEditor.exe --worker` beendet sich mit Code 0. | Bestätigt die tatsächliche KI-Ausführung aus dem Paket auf diesem Runner. Der Bericht bezeichnet seinen Umfang ausdrücklich als `worker_runtime_only`. |
| Native Oberfläche der kompilierten EXE | **Start fehlgeschlagen: nativer Abbruch mit Exit-Code 3.** | Es entstand kein erfolgreicher `ui-smoke-result.json`-Bericht. Die Ursache ist für diesen Lauf nicht abschließend bestimmt. |
| Portables Paket | **Kein freigegebenes portables Artefakt.** | Der fehlgeschlagene Oberflächenstart verhindert die Bereitstellung als erfolgreich geprüftes Paket. |

Die archivierten Nachweise des Laufs enthalten `test-results/source-worker/smoke-result.json`, `test-results/frozen-worker/smoke-result.json`, die zugehörigen Workerberichte und Ergebnisbilder sowie `test-results/source-gui/ui-smoke-result.json` mit deutschen und englischen Bildschirmaufnahmen. Beide KI-Berichte bestätigen `CPUExecutionProvider`, denselben festgelegten Modell-SHA-256 und ein Ergebnis mit 384 × 256 Pixeln. `build-info.json` ordnet das Paket dem oben genannten Commit und dem Kanal `unsigned-development-alpha` zu.

Windows Server 2022 mit vorhandener Entwicklungsumgebung ist keine frische Windows-11-Installation. Ein erfolgreicher Paket-Worker auf diesem Runner belegt daher noch keinen ersten Offline-Start auf einem Rechner ohne Python.

## Kurze Diagnosehistorie

Im [zweiten Windows-Lauf 38301256500](https://github.com/Cenn0/LocalAiPhotoEditor/actions/runs/38301256500) für Commit [`13e69ad6`](https://github.com/Cenn0/LocalAiPhotoEditor/commit/13e69ad6339fde9d3f23aa960adae0a3c23dc7fd) bestanden 59 Tests, Quellcode-KI und Quellcode-Oberfläche. Der Standalone-Bau gelang; der Paket-Worker scheiterte mit `FileNotFoundError`, weil Nuitka 4.3 über `sys.executable` auf `dist/python.exe` statt auf die Anwendung verwies.

Der dritte Lauf bestätigt die Korrektur mit `__compiled__.process_exe`: Der Paketbericht führt die tatsächlich gestartete `LocalAiPhotoEditor.exe` auf und meldet erfolgreichen Workerabschluss. Der anschließende Abbruch der Paketoberfläche ist der verbleibende, separat zu untersuchende Fehler. Für nachfolgende Änderungen wird hier erst nach deren tatsächlicher Prüfung ein Ergebnis ergänzt.

## Lokale Quellcode-Prüfungen

Der zuletzt dokumentierte lokale Lauf für Anwendungscode `9e6dada` umfasst **65 Tests: 57 bestanden, 8 Qt-Tests wegen fehlender lokaler Qt-Laufzeit übersprungen**. Auch `python -m compileall -q src tests tools` wurde erfolgreich mit Exit-Code 0 abgeschlossen. Die lokale Umgebung verwendete Python **3.12.14**, Pillow **12.3.0** und NumPy **2.3.5**; NumPy weicht damit vom vorgesehenen Paket-Pin **2.5.4** ab. Dieser Lauf enthält keine echte lokale Modellinferenz und prüft keine native Windows-EXE. Die Windows-Ergebnisse oben sind eigenständige Nachweise für den ausdrücklich angegebenen Commit.

Die [Coretests](../tests/test_core.py) prüfen unter anderem EXIF-Ausrichtung, LAB-zu-sRGB-Konvertierung durch LittleCMS, transparente Palettenbilder, ungültige ICC-Profile, das Pixel-Limit vor dem Decodieren, Bearbeitung ohne Mutation der Eingabe und begrenztes Undo/Redo. Exporttests prüfen PNG-/WebP-Pixelrundläufe, JPEG mit weißem Transparenzhintergrund, entfernte Eingabemetadaten, Originalschutz einschließlich harter und symbolischer Links sowie den Erhalt eines vorhandenen Exports bei einem simulierten Schreibfehler.

Die [Adaptertests](../tests/test_ai.py) verwenden synthetische Bilder, berechnete Masken und teilweise Ersatzdaten. Sie prüfen unter anderem Vorverarbeitung, Erhalt der RGB-Werte, Kombination vorhandener Transparenz, ungültige Ausgabeformen und Modellintegritätsfehler. Der Netzwerktest betrifft den Fehlerpfad „Modell fehlt“. Er ist kein systemweiter Nachweis des Offlinebetriebs. Die separat ausgeführten Quellcode- und Paket-Workerprüfungen bestätigen dagegen die tatsächliche Modellinferenz auf dem Windows-Runner.

## Noch offene Nachweise

| Bereich | Stand |
| --- | --- |
| Paketoberfläche und vollständiger Bedienablauf | Der native EXE-Start ist im dritten Lauf fehlgeschlagen. Erfolgreicher Start, alle wesentlichen Dialoge, Export aus der Oberfläche, Abbruch, Skalierungen und Barrierefreiheit sind für das Paket noch zu prüfen. |
| Freigegebenes portables ZIP | Noch nicht vorhanden. Ein künftiges erfolgreiches Actions-Artefakt bleibt zunächst eine Entwicklungs-Alpha. |
| Offlinebetrieb ab erstem Start | Nicht auf einem frischen Windows-11-x64-Rechner ohne Python und mit abgeschaltetem Netzwerk geprüft. |
| Bildqualität und Hardwarebedarf | Keine veröffentlichte Qualitätsmessung, kein bestätigter Mindest-RAM und keine garantierten Inferenzzeiten oder GPU-Konfigurationen. |
| Signierung | Kein signiertes Windows-Paket bestätigt; Voraussetzung für die erste stabile Endnutzer-Version. |

## Prüfungen reproduzieren

Für eine vorbereitete Quellcode-Umgebung mit installierten Entwicklungsabhängigkeiten:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests tools
```

Unter Windows mit der Entwicklungsumgebung aus dem README:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
.venv\Scripts\python -m local_ai_photo_editor --smoke-test smoke-output
```

Der letzte Befehl benötigt das echte, erfolgreich geprüfte Modell und ONNX Runtime. Das Ausgabeverzeichnis darf noch nicht existieren. Er erzeugt ein synthetisches Testbild, `smoke-result.json` und bei Erfolg `smoke-output.png`; er bewertet keine Freistellqualität an realen Fotos. Für das gebaute Programm wird dieselbe Prüfung separat über `LocalAiPhotoEditor.exe --smoke-test smoke-output` gestartet. Sie ersetzt keinen Start der Oberfläche.

## Abnahme eines vollständigen Windows-Pakets

Der Workflow lädt nach erfolgreichen Paketprüfungen den Inhalt von `dist/LocalAiPhotoEditor` als `LocalAiPhotoEditor-windows-x64-alpha` hoch. Im Artefakt-ZIP liegt `LocalAiPhotoEditor.exe` direkt im Wurzelverzeichnis. Zum Start ist der gesamte Inhalt einschließlich aller Unterordner zu entpacken.

Vor einer als einsatzbereit beschriebenen Endnutzer-Version sind mindestens folgende Schritte zu protokollieren:

1. Geprüften Commit, [Windows-alpha-Lauf](https://github.com/Cenn0/LocalAiPhotoEditor/actions), konkretes Paket, Abhängigkeiten und Modellbytes festhalten.
2. Das vollständige Paket auf einem frischen Windows-11-x64-System ohne Entwicklungsinstallation bereitstellen und vor dem ersten Start das Netzwerk abschalten.
3. Oberfläche, Deutsch/Englisch und wesentliche Dialoge prüfen; normale und transparente Testbilder öffnen.
4. Anpassung, Zuschnitt, Drehung, Größenänderung, Originalvergleich, Undo/Redo und Export durchführen; den unveränderten Zustand der Originaldatei prüfen.
5. Das echte Modell ausführen, einen laufenden Auftrag abbrechen und erneut starten. Halbfertige Ergebnisse dürfen nicht übernommen werden.
6. Erneuten Programmstart und Verhalten bei fehlendem oder beschädigtem Modell prüfen; dabei darf kein stiller Download stattfinden.
7. Vor der ersten stabilen Veröffentlichung die Windows-Signierung ergänzen und im Release-Nachweis festhalten.

Ausdrücklich als unvollständig geprüfte Alpha bezeichnete Vorabartefakte ersetzen diese Abnahme nicht. Neue Ergebnisse werden erst nach tatsächlicher Ausführung mit Plattform, Commit, Paket und verbleibenden Einschränkungen ergänzt.
