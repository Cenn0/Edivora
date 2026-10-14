# LocalAiPhotoEditor

**Fotos einfach bearbeiten – mit lokaler KI, ohne Benutzerkonto oder Cloud-Dienst.** Öffne ein Bild, passe es an, entferne den Hintergrund und speichere das Ergebnis als neue Datei. Die laufende Anwendung benötigt weder einen Modellserver noch einen API-Schlüssel; Bildverarbeitung und KI-Inferenz finden lokal statt.

[Deutsch](README.md) · [English](README.en.md) · [Für Mitwirkende](CONTRIBUTING.md) · [Mit KI entwickeln](docs/AI_WORKFLOW.md)

> **Status: frühe Entwicklung.** Das portable Windows-Paket `v0.1.0-alpha.1` ist eine **unsignierte Test-Alpha**, keine stabile Freigabe. Der aktuelle Quellcode auf `main` enthält zusätzliche Funktionen, die **nicht** im veröffentlichten ZIP stecken. Die dokumentierten Prüfungen der Alpha gelten nur für deren identifizierten Build. Details: [Verifikationsprotokoll](docs/VERIFICATION.md).

![Geprüfte deutsche Oberfläche der Windows-Test-Alpha](docs/screenshots/ui-smoke-de.png)

## Was möchtest du machen?

| Dein Ziel | Hier starten |
| --- | --- |
| **Das Programm ausprobieren**, ohne zu programmieren | [Windows-Alpha installieren](#1-programm-ausprobieren) |
| **Selbst eine kleine Änderung umsetzen**, auch mit wenig Programmiererfahrung | [Entwicklungsstart](#2-am-quellcode-arbeiten) und [CONTRIBUTING.md](CONTRIBUTING.md) |
| **Mit ChatGPT, Codex oder einem anderen Coding-Agenten mitentwickeln** | [KI-Schnellstart](#3-mit-ki-weiterentwickeln) |
| **Die Technik verstehen** | [Projektaufbau](#projektaufbau) und [Architektur](docs/ARCHITECTURE.md) |

## 1. Programm ausprobieren

Die erste Zielplattform ist **Windows 11 x64**. Die vorhandenen automatisierten Paketprüfungen liefen jedoch auf **Windows Server 2022**; eine vollständige Abnahme auf einem frischen Windows-11-Rechner steht aus.

1. [Portables ZIP der Alpha herunterladen](https://github.com/Cenn0/LocalAiPhotoEditor/releases/download/v0.1.0-alpha.1/LocalAiPhotoEditor-0.1.0-alpha.1-windows-x64.zip) ([Release-Informationen](https://github.com/Cenn0/LocalAiPhotoEditor/releases/tag/v0.1.0-alpha.1)).
2. Das **gesamte Archiv** in einen lokalen Ordner entpacken. Die Unterordner müssen bei der Anwendung bleiben.
3. `LocalAiPhotoEditor/LocalAiPhotoEditor.exe` öffnen, ein Foto auswählen und unter **einem neuen Dateinamen** exportieren.

Für dieses Paket sind **Python, CUDA, Docker und ein Modell-Download nicht nötig**. Das Modell ist im vollständigen Paket enthalten. Zur Integritätsprüfung steht beim Release eine separate `SHA256SUMS.txt` bereit. Das Repository ist derzeit privat; Zugriff auf Release und Quellcode erfordert eine entsprechende GitHub-Berechtigung.

**Funktionsumfang des veröffentlichten ZIPs:** JPEG/PNG/WebP-Import, grundlegende Licht- und Farbanpassungen, Drehen/Zuschneiden/Skalieren, lokale KI-Hintergrundentfernung, Vorher/Nachher, Undo/Redo und Export auf Deutsch oder Englisch.

**Schutz des Originals:** Die Anwendung verhindert den Export über die importierte Originaldatei. PNG/WebP können Transparenz erhalten; JPEG ersetzt transparente Stellen durch Weiß. Exporte übernehmen keine ursprünglichen EXIF-/GPS-/Kommentardaten.

## Welcher Funktionsstand ist gemeint?

| Funktion | Veröffentlichtes Alpha-ZIP | Aktueller `main`-Quellcode |
| --- | :---: | :---: |
| Grundlegende Fotobearbeitung und Export | Ja | Ja |
| Lokales U2NETP-Modell für Hintergrundentfernung | Ja | Ja |
| Geführte Werkzeuge für Licht, Looks, Ausschnitt und Hintergrund | Nein | Ja |
| KI-Motivwerkzeuge (z. B. Hintergrund unscharf, Motiv aufhellen) | Nein | Ja |
| Manuelle Korrektur der Transparenzmaske | Nein | Ja |
| Lokale Projekte als `.laip` speichern/öffnen | Nein | Ja |
| Generative Bearbeitung per Texteingabe, GPU-Support | Nein | Nein |

**Wichtig:** Funktionen in offenen Pull Requests oder anderen Branches sind **nicht automatisch Teil von `main`**. „Im Quellcode vorhanden“ bedeutet außerdem noch nicht „in einem neu getesteten Windows-Paket veröffentlicht“. Die [Roadmap](docs/ROADMAP.md) unterscheidet implementierte Arbeiten und geplante Funktionen.

Weitere Erklärungen: [Geführte Werkzeuge](docs/EDITING_TOOLS.md) · [KI-Motivwerkzeuge](docs/AI_SUBJECT_TOOLS.md) · [Maskenkorrektur](docs/MASK_REFINEMENT.md) · [Projektdateien](docs/PROJECT_FORMAT.md).

## 2. Am Quellcode arbeiten

**Du brauchst:** Git, Python **3.12** und eine Internetverbindung für das einmalige Installieren der Entwicklungsabhängigkeiten. Python 3.12 ist die getestete CI-Version; die in `pyproject.toml` erlaubte Versionsspanne ist keine Zusage, dass jede Plattform und Kombination bereits geprüft wurde.

Unter **Windows/PowerShell** im Repository:

```powershell
git clone https://github.com/Cenn0/LocalAiPhotoEditor.git
cd LocalAiPhotoEditor
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m local_ai_photo_editor
```

Damit startet die Desktopanwendung aus dem aktuellen Quellcode. Für KI-Funktionen musst du das festgelegte Modell bei der **Entwicklung** einmal ausdrücklich vorbereiten:

```powershell
.\.venv\Scripts\python.exe tools\prepare_model.py
```

**Nur dieses Vorbereitungsskript** lädt das Modell bei fehlender Datei herunter und prüft Größe und Prüfsumme; die gestartete Fotoanwendung lädt keine Modelle nach. Die Modellbinärdatei darf nicht eingecheckt werden.

Einen ersten Test kannst du ohne Foto und ohne Änderungen an produktiven Dateien ausführen:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src tests tools
Remove-Item Env:QT_QPA_PLATFORM
```

Die Testsuite enthält auch Qt-Fälle. **Achte auf „skipped“ und Fehlermeldungen**, nicht nur auf einen erfolgreichen Exitcode. Für Linux, einzelne Tests, eine echte lokale Modellprüfung und Fehlerbehebung: [Entwicklungsanleitung](docs/DEVELOPMENT.md).

## 3. Mit KI weiterentwickeln

Eine KI kann beim Verstehen, Planen, Implementieren, Testen und Erstellen eines Pull Requests helfen. **Nur ein Link allein verschafft ihr aber keinen Lese- oder Schreibzugriff auf private Repository-Inhalte.** Verwende einen Coding-Agenten mit freigegebenem GitHub-Zugriff oder gib ihm die relevanten Dateien. Änderungen im Repository erfordern zusätzlich entsprechende Schreibrechte.

**So beginnst du mit einer einzigen kleinen Aufgabe:**

1. Wähle ein bestehendes Issue oder beschreibe genau **ein** Problem. Beginne etwa mit einer verständlicheren Fehlermeldung, einer Übersetzung oder einem kleinen, testbaren UI-Fix.
2. Kopiere den folgenden Prompt in deinen Coding-Agenten und ergänze die konkrete Aufgabe.
3. Prüfe den vorgeschlagenen Diff, die tatsächlich ausgeführten Tests und den Pull Request, bevor du die Änderung übernimmst.

```text
Arbeite im GitHub-Repository Cenn0/LocalAiPhotoEditor auf Basis des aktuellen main.

Lies zuerst AGENTS.md, CONTRIBUTING.md und docs/DEVELOPMENT.md.
Prüfe danach nur die für die Aufgabe relevanten Quell- und Testdateien.
Beachte: Die veröffentlichte Alpha und der aktuelle Quellcode
haben unterschiedliche Funktionsstände.

Meine Aufgabe: [Beschreibe hier genau eine kleine Änderung oder verlinke ein Issue.]

Erkläre kurz den Ist-Zustand und deinen Umsetzungsplan.
Implementiere die Änderung in einem eigenen Branch, ergänze passende Tests
und aktualisiere bei Bedarf DE/EN-Texte und Dokumentation.
Erhalte lokale/offline Bildverarbeitung und den Originalschutz.
Führe die möglichen Prüfungen tatsächlich aus und nenne Fehlschläge,
Skips und nicht geprüfte Punkte ausdrücklich.
Zeige die geänderten Dateien und erstelle einen Pull Request.
Merge nicht ohne meine Freigabe.
Wenn dir der Repo-Zugriff fehlt, sage das und fordere nur die benötigten Dateien an.
```

Noch einfacher erklärt, mit Beispielen und einer Prüfliste: [Mit KI beitragen](docs/AI_WORKFLOW.md). Der normale Beitragsprozess steht in [CONTRIBUTING.md](CONTRIBUTING.md).

## Projektaufbau

| Pfad | Hier findest du … |
| --- | --- |
| `src/local_ai_photo_editor/core/` | Bildzustand, Bearbeitungen, Masken, Rezepte, Projektdateien – **ohne Qt und Modellinferenz** |
| `src/local_ai_photo_editor/ui/` | Desktop-Fenster, Dialoge, Vorschauen, deutsche/englische Texte |
| `src/local_ai_photo_editor/ai/` | Prüfung und Verwendung des lokalen ONNX-Modells |
| `src/local_ai_photo_editor/worker.py` | Abwicklung des separaten KI-Prozesses |
| `tests/` | Reproduzierbare Unit-, Integrations- und UI-Tests |
| `tools/` | Explizite Modellvorbereitung, Builds und Prüfwerkzeuge |
| `.github/workflows/` | Automatische Tests, Windows-Paket- und Offline-Prüfungen |
| `AGENTS.md` | Verbindliche Kurzregeln für Coding-Agenten |

Der KI-Worker läuft getrennt von der Oberfläche, damit diese bedienbar bleibt und Aufgaben abgebrochen werden können. Das ist **keine Sicherheits-Sandbox**. Ein Architekturdiagramm mit den Datenflüssen steht in [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Grenzen und Sicherheit

Unterstützt werden einzelne 8-Bit-Bilder mit höchstens **40 Millionen Pixeln**. RAW, 16-Bit, animierte oder mehrseitige Dateien gehören nicht zum aktuellen Umfang. Das kompakte **U2NETP**-Modell erkennt Vordergrundbereiche, **generiert aber keine neuen Bildinhalte**. Gerade Haare, Fell und Glas können fehlerhaft freigestellt werden. Eine objektive Freistellqualitätsmessung liegt nicht vor.

Der laufende Editor hat keine Cloud-, Telemetrie- oder Kontopflicht und soll keine Bilder übertragen. **Downloads während Installation/Build sind davon getrennt.** Auch können Dateien in vom Nutzer gewählten synchronisierten Ordnern durch dessen Synchronisierungssoftware hochgeladen werden. Temporäre lokale Dateien können nach einem erzwungenen Abbruch verbleiben. macOS-/Linux-Pakete, GPU-Ausführung und eine stabile Windows-Freigabe sind nicht zugesagt.

Vor **öffentlicher Verteilung** müssen insbesondere die Rechte am separat bezogenen ONNX-Modellartefakt und die Qt/LGPL-Paketpflichten abschließend geprüft werden. Näheres in [MODELS.md](docs/MODELS.md), [Dritthinweisen](THIRD_PARTY_NOTICES.md) und [Verifikationsprotokoll](docs/VERIFICATION.md).

## Dokumentation

Der [Dokumentations-Einstieg](docs/README.md) führt nach Ziel durch alle Unterlagen:

- **Mitmachen:** [CONTRIBUTING.md](CONTRIBUTING.md) · [Entwicklungsumgebung](docs/DEVELOPMENT.md) · [KI-Workflow](docs/AI_WORKFLOW.md) · [AGENTS.md](AGENTS.md)
- **Technik:** [Architektur](docs/ARCHITECTURE.md) · [Konzept](docs/CONCEPT.md) · [Modelle & Herkunft](docs/MODELS.md) · [Projektformat](docs/PROJECT_FORMAT.md)
- **Funktionen:** [Geführte Werkzeuge](docs/EDITING_TOOLS.md) · [KI-Motivwerkzeuge](docs/AI_SUBJECT_TOOLS.md) · [Maske](docs/MASK_REFINEMENT.md)
- **Stand & Qualität:** [Roadmap](docs/ROADMAP.md) · [Verifikation](docs/VERIFICATION.md) · [Alpha-Release-Notes](docs/RELEASE_NOTES_ALPHA.md)

**Lizenz:** Der Anwendungscode ist unter **Apache-2.0** lizenziert. Abhängigkeiten und Modellartefakte haben gesonderte Bedingungen; die Weiterverteilung ist nicht allein durch die Repository-Lizenz geklärt.
