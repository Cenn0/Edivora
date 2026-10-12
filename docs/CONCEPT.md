# Projektkonzept

Entscheidungsstand: 12. Oktober 2026. Dieses Dokument beschreibt die Produktentscheidung und die beabsichtigte Bedienung. Welche Teile bereits tatsächlich geprüft wurden, steht separat in [VERIFICATION.md](VERIFICATION.md).

## 1. Das gewünschte Ergebnis

localAiPhotoEditor soll eine Person vom Öffnen eines Fotos bis zu einer brauchbaren exportierten Kopie führen, ohne dass sie Modelle auswählen, Treiber konfigurieren oder einen Server starten muss. Fotos, Bearbeitungsdaten und KI-Aufträge bleiben innerhalb der lokalen Anwendung und ihres Arbeitsverzeichnisses.

Die erste Zielplattform ist Windows 11 x64. Das ist eine Projektentscheidung zur Begrenzung des anfänglichen Testumfangs. Eine fertige Unterstützung aller Geräte dieser Plattform wird daraus erst nach Paket- und Gerätetests.

Für die erste Version zählen vier Eigenschaften besonders:

1. **Verständliche Bedienung:** Funktionen heißen „Hintergrund entfernen“, „Zuschneiden“ oder „Heller“, statt technische Modellparameter vorauszusetzen.
2. **Verlässlicher Umgang mit Fotos:** Das Original wird geschützt; Änderungen lassen sich vergleichen und innerhalb des verfügbaren Verlaufs zurücknehmen.
3. **Vollständige Auslieferung:** Programm, benötigte Laufzeit und Standardmodell gehören ins Paket. Eine separate Entwicklerinstallation darf keine Voraussetzung für Anwender werden.
4. **Nachvollziehbare Grenzen:** Fehlende Funktionen und ausstehende Prüfungen werden benannt. Eine vorhandene Modellanbindung ist noch kein Nachweis guter Bildqualität oder eines funktionierenden Windows-Pakets.

## 2. Umfang der ersten Alpha

Der erste durchgängige Arbeitsablauf umfasst Import, grundlegende Anpassungen, Freistellen, Vergleich und Export. Helligkeit, Kontrast, Sättigung, Drehung, Zuschnitt und Skalierung sind konventionelle Bildverarbeitung. Die erste KI-Funktion ist die automatische Vordergrunderkennung zum Entfernen des Hintergrunds.

| Aufgabe | Geplanter Nutzen | Grenze der Alpha |
| --- | --- | --- |
| Foto öffnen | Ausrichtung und Farben werden beim Import berücksichtigt. | Geeignete 8-Bit-Einzelbilder; maximal 40 MP. |
| Bild anpassen | Wenige verständliche Regler für häufige Korrekturen. | Keine RAW-Entwicklung, HDR-Pipeline oder professionellen Gradationskurven. |
| Zuschneiden und drehen | Bildausschnitt direkt prüfen und ändern. | Keine Ebenen oder dauerhaft gespeicherten Bearbeitungsprojekte. |
| Hintergrund entfernen | Ein lokales Modell erstellt eine Freistellmaske. | Keine Textanweisungen; keine neu generierten Bildinhalte; Masken können Fehler haben. |
| Ergebnis vergleichen | Original und aktuellen Bearbeitungsstand beurteilen. | Der Verlauf ist begrenzt und bleibt nur während der geöffneten Sitzung erhalten. |
| Kopie exportieren | Ein fertiges PNG, JPEG oder WebP erhalten. | Das Original darf nicht als Exportziel dienen. JPEG kann keine Transparenz behalten. |

Diese Begrenzung macht ein kleines, durchgängig prüfbares Programm möglich. Interaktives Nachbessern einer Freistellmaske folgt vor generativer Bearbeitung: Damit lässt sich ein konkretes Ergebnis korrigieren, ohne neue Bildinhalte erzeugen zu müssen.

## 3. Beabsichtigte Bedienung

Der Startbildschirm soll eine klare Einladung zum Öffnen eines Fotos zeigen. Nach dem Import steht das Bild im Mittelpunkt; Werkzeuge sind nach Aufgaben gruppiert. Deutsch und Englisch sind vorgesehen.

Der Ablauf ist bewusst kurz:

1. Foto öffnen und die Vorschau sehen.
2. Eine Aufgabe wählen; nur dafür relevante Einstellungen erscheinen.
3. Bei Anpassungen oder Zuschnitt das Ergebnis prüfen und übernehmen.
4. Bei der KI-Bearbeitung einen verständlichen Arbeitsstatus und eine Abbruchmöglichkeit sehen.
5. Mit dem Original vergleichen; bei Bedarf rückgängig machen.
6. Eine Kopie exportieren und dafür Format und Ziel wählen.

Bedienfehler sollen ohne Datenverlust korrigierbar sein. Ein fehlendes Modell verlangt die Wiederherstellung eines vollständigen Pakets; es löst keinen überraschenden Download aus. Ein abgebrochener KI-Auftrag darf kein halbfertiges Ergebnis übernehmen. Ein bereits vorhandener anderer Export darf erst nach Bestätigung ersetzt werden.

Für die Darstellung sind ausreichende Kontraste, lesbare Beschriftungen, sichtbarer Tastaturfokus und große Bedienziele vorgesehen. Ob dies auf unterschiedlichen Windows-Skalierungen tatsächlich funktioniert, muss an der Oberfläche geprüft werden. Ein bestandener Test der Bildverarbeitung belegt diese Eigenschaften nicht.

## 4. Technologieentscheidung

**Für die Alpha verwenden wir Python 3.12, PySide6 mit Qt Widgets, Pillow, NumPy und ONNX Runtime.** Python steuert die Anwendung; Bildoperationen und Inferenz verwenden die jeweiligen Bibliotheken. Der Einstieg bleibt in einer Anwendungssprache. Qt dokumentiert einen Deploymentweg über `pyside6-deploy` und Nuitka; ONNX Runtime dokumentiert seine Python-Anbindung. Quellen: [Qt Deployment](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html), [ONNX Runtime für Python](https://onnxruntime.ai/docs/get-started/with-python.html).

Die folgende Bewertung ist eine Architekturentscheidung für dieses Projekt, kein Benchmark der drei Ansätze:

| Ansatz | Vorteile für dieses Projekt | Nachteile und zusätzlicher Aufwand | Bewertung |
| --- | --- | --- | --- |
| **Python + PySide6/Qt** | UI, Bildlogik und Modelladapter können in einer Sprache bleiben. Die bestehende Pillow-/NumPy-/ONNX-Pipeline lässt sich direkt verwenden. | Runtime, Qt und native Bibliotheken müssen vollständig paketiert werden. Ein Quellcode-Start ersetzt den Test des fertigen Pakets nicht. Die Oberfläche braucht bewusstes Design. | Beste Ausgangsbasis für die erste Alpha und die absehbare Arbeit an weiteren Modelladaptern. |
| **TypeScript + Tauri/Rust** | Eine Weboberfläche bietet vertraute Gestaltungsmittel; Tauri verbindet sie mit einem nativen Kern. | Für diesen Entwurf kämen Weboberfläche, Rust-Anbindung und gegebenenfalls ein Python-Worker zusammen. Bildtransport, Prozessverträge und mehrere Buildketten würden zusätzliche Arbeit verursachen. | Sinnvoll bei einem starken bestehenden Web-Frontend oder einer Rust-zentrierten Bildpipeline. Für den aktuellen Umfang überwiegen aus unserer Sicht die zusätzlichen Grenzen zwischen Komponenten. |
| **C# + WPF + ONNX Runtime** | Gut passende Alternative für ein dauerhaftes Windows-Projekt. Die erste ONNX-Funktion braucht grundsätzlich keinen Python-Prozess; C#-erfahrene Mitwirkende können die Anwendung vollständig in .NET führen. | Die Bild-/Farbpipeline müsste in dieser Architektur separat gewählt und geprüft werden. WPF bindet die Oberfläche an Windows. Künftige Modelle müssen zur ausgewählten .NET-Pipeline passen oder einen weiteren Adapter erhalten. | Für einen dauerhaft festen ONNX-Modellumfang ebenfalls gut begründbar. Die Entscheidung für Python ist eine Gewichtung der weiteren Modellarbeit, keine Aussage gegen lokale KI in C#. |

Tauris dokumentierte Architektur kombiniert Rust und eine WebView mit Nachrichten zwischen Oberfläche und Kern. [Quelle](https://v2.tauri.app/concept/architecture/). Microsoft dokumentiert WPF als Windows-Oberfläche; ONNX Runtime stellt eine offizielle C#-Anbindung bereit. [WPF](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/overview/), [ONNX Runtime für C#](https://onnxruntime.ai/docs/get-started/with-csharp.html).

Für eine später geforderte plattformübergreifende .NET-Oberfläche wäre die UI-Entscheidung neu zu treffen. Umgekehrt garantiert auch die Wahl von Qt keine bereits funktionierenden macOS- oder Linux-Pakete. Paketgröße, Startzeit, Speicherbedarf und Inferenzdauer werden am vollständigen Programm gemessen; aus der Sprache allein werden keine Zahlen abgeleitet.

### Möglichkeit, Unterstützung und Empfehlung auseinanderhalten

| Kategorie | Aussage für das Projekt |
| --- | --- |
| **Funktioniert grundsätzlich** | Alle drei Ansätze können eine lokale Anwendung mit einer passenden Inferenzanbindung bilden. Der bisherige Core-Testlauf belegt einen konkreten Teil der Python-Implementierung. |
| **Offiziell unterstützt** | Die genannten Herstellerdokumentationen belegen die jeweiligen Framework-/Sprachanbindungen. Sie zertifizieren weder dieses Programm noch sein Modell auf einem beliebigen PC. |
| **Best Practice für diesen Umfang** | Unsere Empfehlung ist eine kleine Anwendung mit klar getrenntem Core, UI und Modelladapter, vollständig mitgelieferten Laufzeiten und überprüfbaren Exporten. Das ist eine begründete Projektentscheidung, keine universelle Vorgabe für Fotoeditoren. |
| **Sicherheitsseitig empfehlenswert** | Nur das vorgesehene, per Prüfsumme gebundene Modell laden, keine heruntergeladenen Python-Modelldateien ausführen und Fotos ohne Laufzeit-Netzwerkpfad verarbeiten. Der eigene Workerprozess dient der Abbrechbarkeit und ist keine Betriebssystem-Sandbox. |

## 5. Architektur mit klaren Verantwortlichkeiten

Die Anwendung wird als zusammenhängendes Desktopprogramm ausgeliefert. Die Modulgrenzen dienen Wartbarkeit und Tests; daraus entstehen keine entfernten Dienste.

| Teil | Verantwortung und Vertrag |
| --- | --- |
| `core/` | Import, Farbkonvertierung, Bearbeitungsfunktionen, unverändertes Original, begrenztes Undo/Redo und atomarer Export. Keine Abhängigkeit von Qt, ONNX Runtime oder Netzwerkcode. |
| `ui/` | Aufgaben, Übersetzungen, Bildvorschau, Dialoge und Koordination. Die Vorschau darf keine unbemerkte Änderung am Dokument auslösen. |
| `ai/` | Modellprüfung, Vorverarbeitung, Inferenz und Zusammensetzen von Bild und Maske. Ein fehlerhaftes Modell oder Ergebnis darf nicht stillschweigend übernommen werden. |
| `worker.py` | Ein definierter lokaler KI-Auftrag in einem separaten Prozess. Das Programm kann ihn abbrechen und danach seinen Arbeitsspeicher freigeben lassen. |
| `tools/` und Buildworkflow | Abhängigkeiten und Modell beschaffen, prüfen und in ein vollständiges Paket aufnehmen. Dieser Netzwerkteil wird nicht zum normalen Bearbeitungsablauf. |

Der Core liefert eigene Bilder zurück und hält das Original getrennt. Eine Änderung erzeugt einen benannten Verlaufsschritt. Die gespeicherten Pixelzustände für Undo und Redo haben zusammen standardmäßig ein Budget von 256 MiB; das gesamte Programm braucht zusätzlich Speicher für Original, aktuellen Stand, Vorschau und Verarbeitung.

Ein einzelner KI-Auftrag erhält eine normalisierte lokale PNG-Eingabe. Währenddessen wird verhindert, dass sein Ergebnis zu einem inzwischen anderen Bild gehört. Das Ergebnis wird erst nach erfolgreichem Abschluss und Größenprüfung übernommen. Einzelheiten und das Komponentendiagramm stehen in [ARCHITECTURE.md](ARCHITECTURE.md).

## 6. Modellentscheidung und weitere KI-Funktionen

Das erste Modell ist **U2NETP** für die Vordergrunderkennung. Ein schmaler Adapter und ONNX Runtime mit CPU-Ausführung halten die erste Konfiguration überschaubar. Das ist eine Ausgangsbasis für Messungen; konkrete Laufzeiten oder eine garantierte Freistellqualität werden noch nicht behauptet. Modellherkunft, Prüfsummen und die Unterscheidung zwischen Quellcode- und Gewichtsartefaktlizenz stehen in [MODELS.md](MODELS.md).

Die Maske verändert die vorhandene Transparenz. Die ursprünglichen RGB-Pixel bleiben erhalten. Gerade bei Haaren, feinen Konturen oder durchscheinenden Gegenständen muss die praktische Ergebnisqualität später mit geeigneten Testbildern beurteilt werden.

Die nächsten Schritte sind eine vom Anwender korrigierbare Maske und der Vergleich mit BiRefNet Lite. Für spätere Bearbeitung durch Textanweisungen wird FLUX.2 klein 4B als Kandidat untersucht. Dazu gehören alle benötigten Modellbestandteile und die gesamte Laufzeit. Weder eine einzelne Gewichtsdatei noch die VRAM-Zahl aus einer fremden Konfiguration beweisen ein einsatzbereites Paket. Ein bestimmter 12-GB-Grafikkartenbetrieb wird nicht zugesagt.

## 7. Auslieferung und Abnahme

Die erste Alpha wird als portables Windows-ZIP vorgesehen. Ein vollständiger Paketordner ist für diesen Stand ausreichend; ein Installer kann später darauf aufbauen. Der Workflow **Windows alpha** soll das Artefakt **LocalAiPhotoEditor-windows-x64-alpha** bereitstellen. Ein vorhandener Workflow ist noch kein erfolgreicher Lauf.

Eine veröffentlichte Test-Alpha kann ausdrücklich als unsigniertes Vorabpaket gekennzeichnet sein. **Vor der ersten stabilen Endnutzer-Version sind signierte Windows-Pakete und eine bestandene Abnahme auf einem frischen Windows-System vorgesehen.** Es wird kein vorhandenes Signierzertifikat vorausgesetzt. Diese Abgrenzung gilt ebenso in Architektur und Roadmap.

Die Abnahme beantwortet die ursprüngliche Produktfrage: Funktioniert die vollständige Anwendung ohne Entwicklerwerkzeuge und bei abgeschaltetem Netzwerk vom ersten Start bis zum Export? Dafür müssen auch Modellinitialisierung, Abbruch, Originalschutz, deutsche/englische Bedienung und Paketvollständigkeit geprüft werden. Ein Quellcode-Review oder ein Test mit künstlichen Masken genügt dafür nicht.

Die Empfehlung bleibt daher: **Zuerst den kleinen lokalen Editor mit einer funktionierenden, vollständig paketierten Freistellfunktion abschließen.** Anschließend Maskenkorrektur und gespeicherte Projekte ergänzen, bevor umfangreiche generative Modelle die Hardware- und Auslieferungsanforderungen verändern. Die ausführliche Reihenfolge steht in [ROADMAP.md](ROADMAP.md).
