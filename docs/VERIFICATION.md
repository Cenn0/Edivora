# Verifikationsprotokoll

Stand: 12. Oktober 2026. Dieses Protokoll dokumentiert den beobachteten lokalen Lauf während der ersten Implementierung. Es behauptet keinen erfolgreichen GitHub-Actions-Lauf und keine Freigabe eines Windows-Pakets. Nach weiteren Änderungen muss der Nachweis mit dem geprüften Commit und den zugehörigen Ergebnissen aktualisiert werden.

## Tatsächlich beobachteter lokaler Stand

| Prüfung | Ergebnis | Aussagegrenze |
| --- | --- | --- |
| `PYTHONPATH=src python -m unittest discover -s tests -v` | **59 Tests: 51 bestanden, 8 übersprungen.** Bestandene Prüfungen: 33 Coretests, 17 Tests für KI-Adapter/Modellprüfung/Worker sowie ein Übersetzungstest. | Die 8 Qt-Tests wurden wegen der fehlenden lokalen Qt-Laufzeit ausdrücklich übersprungen. Echte Modellinferenz war nicht Bestandteil der erfolgreichen Prüfungen. |
| `python -m compileall -q src tests tools` | **Erfolgreich**, Exit-Code 0, beim vorausgegangenen lokalen Ausgangslauf. | Belegt die Übersetzbarkeit des zu diesem Zeitpunkt vorhandenen Python-Codes; keinen erfolgreichen Programmstart mit nativen Abhängigkeiten. Nach abschließenden Änderungen erneut ausführen. |
| Lokale Laufzeit | Python **3.12.14**, Pillow **12.3.0**, NumPy **2.3.5**. | NumPy weicht vom vorgesehenen Paket-Pin **2.5.4** ab. Der Lauf ist daher kein Nachweis für die vollständige gepinnte Paketumgebung. |

Der vorherige lokale Ausgangslauf hatte 45 bestandene Tests ohne Qt-Prüfungen. Die oben angegebene aktualisierte Zahl stammt aus dem anschließenden vollständigen Lauf der erweiterten Suite; sie darf nicht als 59 bestandene Tests wiedergegeben werden.

Die Coretests prüfen unter anderem EXIF-Ausrichtung, tatsächliche LAB-zu-sRGB-Konvertierung durch LittleCMS, transparente Palettenbilder, ungültige ICC-Profile, das Pixel-Limit vor dem Decodieren, Bearbeitung ohne Mutation des Eingabebildes sowie begrenztes Undo/Redo. Exporttests prüfen PNG-/WebP-Pixelrundläufe, JPEG mit weißem Transparenzhintergrund, entfernte Eingabemetadaten, Schutz des Originals einschließlich harter und symbolischer Links sowie den Erhalt eines vorhandenen Exports bei einem simulierten Schreibfehler. Quelle: [test_core.py](../tests/test_core.py).

Die Adaptertests arbeiten mit synthetischen Bildern, berechneten Masken und teilweise Ersatzdaten. Sie prüfen unter anderem Vorverarbeitung, Erhalt der RGB-Werte, Kombination vorhandener Transparenz, ungültige Ausgabeformen und Modellintegritätsfehler. Der Test gegen Netzwerkzugriff betrifft den Fehlerpfad „Modell fehlt“. Er ist kein systemweiter Nachweis, dass das vollständige Paket offline funktioniert. Quelle: [test_ai.py](../tests/test_ai.py).

## Was noch nicht nachgewiesen ist

| Bereich | Stand dieses Protokolls |
| --- | --- |
| PySide6/Qt-Oberfläche | Lokal nicht ausgeführt. Keine bestätigte Darstellung, Tastaturbedienung, Windows-Skalierung oder Interaktion mit echten Dialogen. |
| Tatsächliches U2NETP-Artefakt | Der erwartete SHA-256 ist dokumentiert; Download und eigener Hashabgleich des echten Binärartefakts sind noch ausstehend. Siehe [MODELS.md](MODELS.md). |
| Echte Inferenz mit ONNX Runtime | Nicht lokal ausgeführt. Eine korrekte Schnittstelle und synthetische Maskentests ersetzen diesen Nachweis nicht. |
| Gepinnte Abhängigkeiten | Die vollständige Umgebung aus [pyproject.toml](../pyproject.toml) ist durch diesen lokalen Lauf nicht geprüft. |
| Windows-Build und gebautes Programm | Kein hier dokumentierter erfolgreicher Actions-Lauf, kein bestätigter Start der gepackten Anwendung. |
| Offlinebetrieb ab erstem Start | Nicht auf einem frischen Windows-Rechner mit abgeschaltetem Netzwerk geprüft. |
| Bildqualität und Hardwarebedarf | Keine veröffentlichte Qualitätsmessung, kein bestätigter Mindest-RAM und keine garantierten Inferenzzeiten oder GPU-Konfigurationen. |

## Prüfungen reproduzieren

Für einen vorbereiteten Quellcode-Arbeitsstand unter einer Shell mit `PYTHONPATH`-Unterstützung:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests tools
```

Unter Windows mit einer installierten Entwicklungsumgebung aus dem README:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m compileall -q src tests tools
```

Ein separater Test der tatsächlichen Inferenz wird so gestartet:

```powershell
.venv\Scripts\python -m local_ai_photo_editor --smoke-test smoke-output
```

Voraussetzungen sind das echte, erfolgreich geprüfte Modell und ONNX Runtime. `smoke-output` darf noch nicht existieren. Der Befehl arbeitet mit synthetischen Bildinhalten, schreibt `smoke-result.json` und bei Erfolg `smoke-output.png`. Ein erfolgreicher Lauf bestätigt eine begrenzte Inferenz-/Exportstrecke; er bewertet noch keine Freistellqualität an realen Fotos. Für das gebaute Programm ist derselbe Einstieg über dessen ausführbare Datei separat erforderlich.

## Abnahme eines vollständigen Windows-Pakets

Vor einer als einsatzbereit beschriebenen Endnutzer-Version ist mindestens folgender Ablauf zu protokollieren:

1. Den geprüften Commit, den zugehörigen [Windows-alpha-Lauf](https://github.com/Cenn0/LocalAiPhotoEditor/actions) und das konkrete Paket festhalten; enthaltene Abhängigkeiten und Modellbytes prüfen.
2. Das gesamte Paket auf einem frischen Windows-11-x64-System ohne Entwicklungsinstallation bereitstellen und vor dem ersten Start das Netzwerk abschalten.
3. Die Oberfläche starten, Deutsch/Englisch und die wichtigsten Dialoge prüfen; ein normales sowie ein transparentes Testbild öffnen.
4. Anpassung, Zuschnitt, Drehung, Größenänderung, Originalvergleich und Undo/Redo durchführen; ein Ergebnis exportieren und prüfen, dass die Originaldatei unverändert geblieben ist.
5. Das echte Modell ausführen und Ergebnis sowie Abbruch eines laufenden Auftrags prüfen. Beendete oder abgebrochene Aufträge dürfen keine halbfertigen Ergebnisse übernehmen.
6. Einen erneuten Start sowie den vorgesehenen Umgang mit fehlendem/beschädigtem Modell prüfen. Diese Fälle dürfen keinen stillen Download auslösen.
7. Vor der ersten stabilen Veröffentlichung die Signierung des Windows-Pakets ergänzen und im Release-Nachweis festhalten.

Vorabartefakte dürfen ausdrücklich als unvollständig geprüfte Alpha bereitgestellt werden. Ein grüner CI-Lauf und eine solche Bereitstellung ersetzen die noch offenen Abnahmepunkte nicht. Ergebnisse werden erst nach tatsächlicher Ausführung mit Datum, Plattform, Commit, Paket und verbleibenden Einschränkungen ergänzt.
