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

## Edivora: neue Oberfläche im Entwicklungsstand

Die neue, **noch nicht veröffentlichte Qt-Oberfläche** folgt dem [gemeinsamen Edivora-Designsystem](docs/DESIGN_SYSTEM.md). Ein Startbereich bietet den Fotoimport und das Öffnen vorhandener Bearbeitungsprojekte. In der gemeinsamen Navigationsleiste sind **Foto** (funktional) sowie **Video** und **Audio** (ausdrücklich *geplant*, nicht bedienbar) aufgeführt. Das Foto erhält eine große Arbeitsfläche und rechts vier einfache Einstiegsaktionen: Foto verbessern, Zuschneiden/Drehen, Hintergrund weichzeichnen (lokale KI) und Hintergrund entfernen (lokale KI). Weitere Werkzeuge sind einklappbar.

Die KI-Aufgaben öffnen weiterhin ihre bestehenden **Vorschau-Dialoge mit Übernehmen/Abbrechen**. Regler-, Zuschneide- und Maskenkorrekturen bleiben so lange erreichbar, wie eine Vorschau offen ist. Oben stehen Datei öffnen, Rückgängig, Wiederholen, Originalvergleich und **Exportieren**; „Projekt speichern“ bleibt im Datei-Menü und unter `Strg+S`. Ein abgeschlossener Bildexport erzeugt eine **neue Datei** und verändert das Original nicht. Die Oberfläche unterstützt Deutsch und Englisch; die Farben und Steuerelemente werden gemeinsam verwaltet.

**Abgrenzung:** Dies ist eine Aktualisierung der aktuellen *Quellcode-Oberfläche*, nicht der bereits veröffentlichten Windows-Testalpha `v0.1.0-alpha.1`. Video-/Audio-Verarbeitung, eine vollständig eingebettete Bearbeitung aller Fotoeffekte ohne Dialoge, reale Usability-/Screenreader-Tests und DPI-/Windows-Abnahme sind noch ausstehend. Details: [Implementierungsstand der Oberfläche](docs/UI_IMPLEMENTATION.md).

## Neu im Quellstand: KI-Motivwerkzeuge

Unter **KI-Motivwerkzeuge** oder mit **Strg+Umschalt+E** erkennt die lokale KI zunächst das Motiv. Danach kannst du den **vorhandenen Hintergrund unscharf machen**, das **Motiv aufhellen**, den **Hintergrund abdunkeln** oder **nur das Motiv farbig lassen**. Auch **auf das erkannte Motiv zuschneiden** und **mit Vorschau freistellen** stehen im selben Dialog bereit.

Du brauchst für die Hintergrund-Unschärfe kein zweites Hintergrundfoto. Die Erkennung läuft einmal pro geöffnetem KI-Bearbeitungsbereich; beim Wechseln der Effekte wird dieselbe Auswahl weiterverwendet. Über **KI-Auswahl anzeigen** lässt sich die Auswahl als violette Markierung kontrollieren. Stärke, weiche Kante und beim Zuschnitt der Rand sind einstellbar. Erst **Übernehmen** legt einen rückgängig machbaren Schritt an; **Abbrechen** verwirft die Vorschau.

**Was daran KI ist:** Das bereits mitgelieferte U2NETP-Modell erkennt die Motivbereiche. Die anschließenden Effekte sind lokale Bildoperationen. Es gibt kein neues Modell, keine zusätzliche Einrichtung und keine generative Rekonstruktion. Die Auswahl kann weiterhin Fehler machen, insbesondere an Haaren, Glas und ähnlichen Vorder-/Hintergrundfarben. Farb- und Hintergrundeffekte erhalten die ursprüngliche Transparenz; Freistellen und Zuschneiden verändern sie beziehungsweise die Bildgröße gezielt.

**Bereitstellung:** Diese Erweiterung gehört zum neueren Entwicklungsstand, **nicht zum oben verlinkten `v0.1.0-alpha.1`-ZIP**. Details, Prüfablauf und Grenzen: [Lokale KI-Motivwerkzeuge](docs/AI_SUBJECT_TOOLS.md).

## Neu im Quellstand: Mehr Werkzeuge, einfach bedienbar

Unter **Weitere Werkzeuge** oder mit **Strg+E** öffnet sich ein gemeinsamer Bearbeitungsbereich mit vier übersichtlichen Reitern:

| Bereich | Möglichkeiten |
| --- | --- |
| **Licht & Farbe** | Sanfter Verbesserungsvorschlag, heller/dunkler, dunkle Stellen aufhellen, helle Stellen abdunkeln, wärmere/kühlere Farben, Farbstärke, Kontrast und Details schärfen. |
| **Looks** | Natürlich, Kräftig, Sanft, Warm, Schwarz-Weiß und Sepia mit einstellbarer Stärke; Bildränder weich abdunkeln. |
| **Ausschnitt** | Feste Formate 1:1, 4:3, 3:2, 16:9, 4:5 und 9:16, Ausschnitt verschieben, horizontal/vertikal spiegeln und in 90°-Schritten drehen. |
| **Hintergrund** | Nach dem Freistellen eine Farbe oder ein eigenes lokales Foto einsetzen; nur das gewählte Hintergrundfoto weichzeichnen. |

Du siehst zuerst eine **Vorschau**, kannst den vorherigen Stand vergleichen und einzelne Regler, einen Bereich oder alles zurücksetzen. Erst **Übernehmen** legt einen neuen, rückgängig machbaren Bearbeitungsschritt an. **Abbrechen** lässt den bisherigen Stand unverändert. Die Berechnung in voller Bildgröße läuft in einem abbrechbaren Hintergrund-Thread.

Die Regler haben verständliche Beschriftungen, kurze Erklärungen und sichtbare Werte. Es werden keine zusätzlichen Modelle, Konten oder Server benötigt. „Sanft verbessern“ ist eine klassische Bildkorrektur, keine generative KI. Ein Hintergrund lässt sich nur ersetzen, wenn das Bild bereits transparente Stellen enthält.

**Wichtig:** Auch diese Werkzeuge sind **Quellcodefunktionen nach `v0.1.0-alpha.1`**, nicht Bestandteil des oben verlinkten alten ZIPs. Kleine Unterschiede zwischen verkleinerter Vorschau und voller Auflösung sind möglich. Projektdateien speichern die angenommenen Bildstände, nicht nachträglich editierbare Einstellungsebenen. Anleitung, Umsetzung und Grenzen: [Geführte Bildbearbeitung](docs/EDITING_TOOLS.md).

## Neu im Quellstand nach v0.1.0-alpha.1: Bearbeitungsprojekte

Der neue Quellstand kann Bearbeitungen als **lokale `.laip`-Projektdatei** speichern und später wieder öffnen. Gesichert werden das unveränderte Original, der angenommene Bearbeitungsstand und die noch im Verlauf verfügbaren Undo/Redo-Bilder. Über **Datei → Projekt speichern (Strg+S)** und **Datei → Projekt öffnen** kannst du die Bearbeitung fortsetzen. Ein Projekt kann auch in das Fenster gezogen werden.

Beim Speichern bleibt die ursprüngliche Fotodatei unverändert; das Projekt benötigt keinen Modellserver und legt keine ursprünglichen absoluten Bilddateipfade ab. Nach dem erneuten Öffnen wird zum Schutz des unbekannten Originalpfads nur der Export auf einen **neuen Dateinamen** erlaubt. Die genauen Formatgrenzen und Sicherheitsprüfungen stehen unter [Projektdateiformat](docs/PROJECT_FORMAT.md).

**Wichtig:** Diese Entwicklung ist **noch nicht Bestandteil** des bereits veröffentlichten portablen `v0.1.0-alpha.1`-ZIPs. Bis CI- und Paketprüfungen erfolgreich abgeschlossen sind, ist sie als Quellcodefunktion zu betrachten. Die weiter unten beschriebenen Alpha-Nachweise gelten nur für den veröffentlichten Paketstand.

## Neu im Quellstand: Manuelle Maskenkorrektur

Im neueren Quellstand kannst du nach der lokalen KI-Freistellung fehlende Motivteile **wieder sichtbar machen** oder verbliebene Hintergrundreste mit einem Pinsel **transparent entfernen**. Pinselgröße und weiche Kante sind einstellbar. Die Änderungen werden zuerst nur in einer Vorschau gezeigt. Pinselzüge lassen sich dort einzeln zurücknehmen; erst „Korrektur übernehmen“ legt einen neuen Undo/Redo-Schritt an.

Die Korrektur verändert **nur die Transparenz (Alpha)**, nicht die RGB-Farben. Sie generiert keine fehlenden Bilddetails und entfernt keine Hintergrundfarbsäume aus Haaren. Bei bereits vor der KI vorhandener Transparenz kann „Wiederherstellen“ Bereiche stärker sichtbar machen als ursprünglich. Details und technische Grenzen: [Manuelle Maskenkorrektur](docs/MASK_REFINEMENT.md).

**Bereitstellung:** Diese Funktion und die Projektdateien sind im neuesten Quellcode implementiert, **nicht** im veröffentlichten `v0.1.0-alpha.1`-ZIP. Aktuelle Testnachweise für diese Funktionen sind von denen der veröffentlichten Vorabversion zu unterscheiden.

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
| ONNX Runtime CPU + U2NETP | Lokale Hintergrundentfernung und Motivauswahl |
| Nuitka 4.2.2 | Vollständiges Windows-Paket mit eingebundener Laufzeit |

Die Bildlogik ist von Oberfläche und KI getrennt. Ein eigener KI-Prozess hält die Oberfläche bedienbar und ermöglicht den Abbruch eines Auftrags. Python und Qt halten diese erste Version in einer Anwendungssprache; der Vergleich mit Tauri/Rust und C# sowie die Gründe für diese Wahl stehen im [Projektkonzept](docs/CONCEPT.md). Die konkrete Aufteilung beschreibt die [Architektur](docs/ARCHITECTURE.md).

## Ehrliche Grenzen

- Unterstützt werden passende **8-Bit-Einzelbilder bis 40 Millionen Pixel**. RAW-, 16-Bit-, animierte und mehrseitige Dateien gehören nicht zur Alpha.
- Die EXIF-Ausrichtung wird berücksichtigt. Gültige eingebettete Farbprofile werden nach sRGB umgerechnet; ungültige oder nicht unterstützte Profile werden abgelehnt. RGB-, Graustufen- und Palettenbilder ohne Profil gelten als sRGB. CMYK und LAB benötigen ein gültiges eingebettetes Profil.
- Der Verlauf liegt im Arbeitsspeicher und ist begrenzt. Große Fotos behalten weniger rückgängig machbare Schritte; das Original bleibt während der Bearbeitung verfügbar.
- Die veröffentlichte Alpha bietet weder Projektdateien, manuelle Maskenkorrektur, die geführten Werkzeuge noch die neuen KI-Motiveffekte. Diese Funktionen sind im neueren Entwicklungsstand implementiert; Ebenen, Bearbeitung durch Textanweisungen und generatives Entfernen einzelner Objekte fehlen weiterhin.
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
- [Lokale KI-Motivwerkzeuge](docs/AI_SUBJECT_TOOLS.md)
- [Geführte Bildbearbeitung: Licht, Looks, Ausschnitt und Hintergrund](docs/EDITING_TOOLS.md)
- [Lokale Bearbeitungsprojekte (.laip)](docs/PROJECT_FORMAT.md)
- [Manuelle Maskenkorrektur](docs/MASK_REFINEMENT.md)
- [Prüfergebnisse und offene Nachweise](docs/VERIFICATION.md)
- [Roadmap](docs/ROADMAP.md)
- [Drittkomponenten und Lizenzhinweise](THIRD_PARTY_NOTICES.md)

Der Anwendungscode steht unter **Apache-2.0**. Bibliotheken und Modelle behalten ihre jeweiligen Lizenzen. Die Lizenz des U-2-Net-Quellprojekts und die Herkunft des separat bereitgestellten ONNX-Artefakts werden in den Modell- und Dritthinweisen ausdrücklich getrennt betrachtet.
