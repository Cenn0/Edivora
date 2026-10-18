# Edivora – Produkt- und Technikroadmap 2026/2027

**Aktualisiert: 18.10.2026.** Grundlage: öffentlicher Hauptzweig **main** (zuletzt geprüfter Merge-Commit: `91a1f0763e4b9e94b29dc9911abe7b2523d3ac98`), Paketversion **0.4.0a1**. Weitergehende Änderungen werden erst nach Merge und Commit-spezifischer CI als umgesetzt markiert. Die Versionsnummern unten sind **Planungsziele**, keine veröffentlichten Versionen oder Terminzusagen.

## 1. Produktziel und Leitplanken

Edivora ist eine quelloffene, einsteigerfreundliche Desktop-Suite mit unabhängig startbaren Foto-, Video- und Audioeditoren. Grundprinzip: **lokale Bearbeitung, kein Konto, keine Telemetrie, keine Cloud-KI, keine automatischen Modell-Downloads zur Laufzeit**. Neue Modelle werden separat bei Entwicklung/Paketvorbereitung beschafft, auf feste Dateiidentität geprüft und nur nach Klärung konkreter Lizenzrechte verteilt.

- Eine typische Aufgabe soll über **Importieren → Vorschau → Übernehmen/Verwerfen → Projekt speichern bzw. separat exportieren** verständlich funktionieren. Komplexere Werkzeuge werden progressiv eingeblendet.
- Änderungen sollen möglichst nicht destruktiv sein; Originalmedien werden auch bei Abbruch, Fehler, Symlink/Hardlink und Projektrecovery nicht überschrieben.
- Bestehende **Python-3.12-, PySide6/Qt-, Core-, AI-Worker- und FFmpeg-Grenzen** werden gezielt verbessert statt ohne Nachweis durch einen kompletten Framework-Wechsel ersetzt.
- Neue Medien- und Projektformate gelten als potenziell bösartig. Native Decoder und Unterprozesse sind **keine Sicherheits-Sandbox**.
- KI-Effekte brauchen reale Modelltests und transparente Qualitätsgrenzen. Eingebrannte Filter, verlorene Bilddetails oder Audioartefakte lassen sich nicht zuverlässig vollständig rückgängig machen.
- Eine Funktion kann technisch implementiert sein, ohne getestet, offiziell freigegeben oder sicherheitsseitig empfehlenswert zu sein.

## 2. Verifizierter Ausgangspunkt

| Bereich | Aktueller Quellcode, 0.4.0a1 | Wesentliche Lücke |
| --- | --- | --- |
| Launcher und UX | Foto/Video/Audio unabhängig starten, Launcher bleibt offen; Dark Theme, Icons, DE/EN, skalierbare Vorschauen und scrollbare Inspektoren | Interaktive Windows-11-/Accessibility-Abnahme und konsistente Vollsequenz-Workflows fehlen |
| Foto | JPEG/PNG/WebP, Korrekturen, Looks, Zuschnitt, Masken, Undo/Redo, U2NETP, **.laip** | Keine Ebenen, RAW/HDR, generative Bildbearbeitung |
| Video | Bis 24 geordnete Clips auf einer Spur, Trimmen/Teilen/Sortieren, Korrektur-Rezepte, **.edvp**, HD/Full-HD-MP4 | Keine kontinuierliche Sequenzvorschau, mehrere Spuren oder Übergänge |
| Video-KI | U2NETP für **ein Standbild** und CPU-DnCNN für maximal 30 s / 720p / 30 fps | Keine validierte temporale Restaurierung, generelle Filterentfernung oder geprüfte GPU |
| Audio | Bis 24 geordnete Clips auf einer Spur, Pegel/Fades, **.edap**, WAV/MP3, Silero VAD | Keine Mehrspurmischung, Transkription oder neuronale Rauschreduktion |
| Medienprojekte | Schema 2, ältere Schema-1-Dateien werden gelesen, 60 Undo/Redo-Zustände in der Sitzung, sicheres Speichern | Externe Medienreferenzen; Relinking und bestätigte Recovery-Checkpoints für bereits gespeicherte Audio-/Videoprojekte vorhanden, aber weder portable Projekte noch Recovery für nie gespeicherte Projekte |
| Distribution | Öffentliches Apache-2.0-**Quellcode**-Repo; historische Foto-Alpha | **Keine für öffentliche Weiterverteilung freigegebene Windows-Suite** |

**Distributionsstatus:** Es gibt weiterhin **keine genehmigte öffentliche Windows-ZIP**. Der öffentliche Quellcode und erfolgreiche automatisierte Tests allein erlauben keine Weiterverteilung ungeprüfter Qt-/FFmpeg-/Modell-Binärdateien.

**Statuskorrektur:** [PR #17](https://github.com/Cenn0/Edivora/pull/17) (vier Modelle/Hardwareprofile) wurde am 16.10.2026 **geschlossen, nicht gemergt**. Diese Funktionen gehören **nicht** zum Stand von main. Dagegen wurden unter anderem [PR #21](https://github.com/Cenn0/Edivora/pull/21) (0.4-Suite), [#22](https://github.com/Cenn0/Edivora/pull/22) (Public-Release-Schutz) und [#31](https://github.com/Cenn0/Edivora/pull/31) (CI-Kostenhygiene) gemergt. Die weiterhin offenen Release-Issues [#2](https://github.com/Cenn0/Edivora/issues/2) und [#3](https://github.com/Cenn0/Edivora/issues/3) bleiben verbindlich; ein alter Issue-Text, der PR #22 noch als ungemergt beschreibt, ist überholt.

### Freigabestufen – separat nachweisen

1. **Implementiert:** Funktion ist im aktuellen main vorhanden.
2. **Automatisiert geprüft:** Unit-/Integrations-/UI-/Modelltests sind am konkreten Commit erfolgreich und reproduzierbar.
3. **Paket geprüft:** exakt identifizierter, heruntergeladener Windows-Build startet und arbeitet ohne Entwicklungsumgebung und mit wirksamer Offline-Sperre.
4. **Endnutzer-Abnahme:** Clean-Windows-11-x64, reale Eingabemedien, Skalierung/Barrierefreiheit, Ressourcen- und Fehlerfälle bestanden.
5. **Öffentlich freigegeben:** Rechte aller mitgelieferten Qt-/FFmpeg-/Modell-/Runtime-Dateien nachgewiesen; SBOM, Hinweise, Quellenpflichten und Hashes vollständig.
6. **Stabil unterstützt:** definierte Plattform-/Hardware-/Codec-Matrix, Wartung, Update- und Supportprozess dokumentiert.

Ein grüner CI-Status beweist **nicht** automatisch die Stufen 3–6.

### Implementierungsschritte nach der Bestandsaufnahme

- **M3 (Teil):** Verifiziertes, manuelles Relinking verschobener oder geänderter Medienquellen; die Projektdatei wird nur nach ausdrücklichem Speichern aktualisiert. Mit [PR #38](https://github.com/Cenn0/Edivora/pull/38) sind alle fünf CI-Prüfungen für einen lokalen, bestätigungspflichtigen Recovery-Checkpoint bereits gespeicherter Audio-/Videoprojekte erfolgreich durchlaufen; der PR wurde als `91a1f07` gemergt. Für neue, nie gespeicherte Projekte, `.laip`-Foto-Recovery und portable Medienpakete gibt es weiterhin keine entsprechende vollständige Umsetzung.
- **M1 (Teil):** Ganzsequenz-Vorschau über einen lokalen **Vorab-Render** für maximal **2 Minuten** mit dem bestehenden Exportfiltergraphen sowie eine Qt-freie, millisekundengenaue Sequenz-Zeitbasis. Der Vorschauprozess besitzt Zeit-/Dateigrößenlimits, Abbruch und Temp-Cleanup. **Nicht** gleichbedeutend mit kontinuierlicher **Echtzeit**-Vorschau, Mehrspurunterstützung oder einer finalen Windows-Freigabe.

## 3. Priorisierung und Reihenfolge

| Meilenstein | Priorität | Zielversion (Plan) | Ergebnis | Voraussetzung |
| --- | --- | --- | --- | --- |
| M0 – Release- und Stabilitätsbasis | **P0** | 0.4.1 | Verlässliche Basis und rechtskonforme Release-Schranken | sofort |
| M1 – Nutzbare Gesamtvorschau | **P0** | 0.5 | Kontinuierliche Video-/Audio-Sequenzvorschau | M0-Kernstabilität |
| M2 – Echte Timeline | **P1** | 0.6 | Nichtlineare Spuren, Überblendungen, einfache Mischungen | M1-Zeitbasis und Renderkonsistenz |
| M3 – Robuste Projektarbeit | **P1** | 0.7 | Medien relinken, Wiederherstellung, portable Projekte | M1, teilweise parallel zu M2 |
| M4 – Erweiterte lokale KI | **P1/P2** | 0.8 | Prüfbare Modellprofile, Audio-/Video-/Foto-Assistenz | M0-Lizenzgrundlage, M1/M2 |
| M5 – Qualitäts- und UX-Beta | **P0 vor 1.0** | 0.9 | Stabilitäts-, Performance- und Bedienungsabnahme | M1–M4 je nach freigegebenem Umfang |
| M6 – Öffentliche stabile Ausgabe | **Release-Gate** | 1.0 | Verlässlich installierbare und dokumentierte Suite | alle relevanten Gates bestanden |

**Reihenfolge:** Vor neuen umfangreichen KI-Funktionen zuerst **gemeinsame Vorschau, Timeline-Zeitbasis und Projektzuverlässigkeit**. Sicherheits-/Lizenzarbeiten aus M0 laufen parallel weiter und blockieren die **öffentliche Binärfreigabe**, nicht jede Quellcodeentwicklung. Größenangaben: M0/M1/M3 = mittel–groß, M2/M4 = sehr groß, M5/M6 = abhängig von Prüf- und Fehleraufwand; keine belastbaren Kalenderdaten ohne Teamkapazität und Benchmark-Basis.

## 4. Meilensteine mit konkreten Arbeitspaketen

### M0 – 0.4.1: Stabilisierung und belastbare Release-Schranken (P0)

**Ziel:** Bekannte Fehler, unklare Freigaben und falsche Dokumentationsaussagen beseitigen.

- **M0.1 Recht und Herkunft:** Für jedes **tatsächlich mitgelieferte** Qt-/PySide6-/Shiboken-/Qt-Plugin, FFmpeg-Binary/Codec, Modellgewicht/ONNX-Export, Nuitka-/Python-/Native-Runtime eine SBOM, exakte Versionen, Lizenzpflichten, Quellen- und Ersetzungspflichten nachweisen; speziell U2NETP und DnCNN sowie spätere optionale Modelle. Issue **#3** erst bei echter Evidenz schließen.
- **M0.2 Verteilung:** Nicht genehmigte historische Assets/Actions-Pakete auf tatsächlich öffentliche Zugänglichkeit prüfen; Sperrmechanismen und Quarantäneprozess testen. Keine neue öffentliche ZIP, solange das Lizenz-Gate offen ist.
- **M0.3 Qualität:** Bestehende Foto-, Medien-, Abbruch-, Worker-/Prozessbaum-, Sicherheits-, Quellen- und Binär-Smoketests auf **identischem Commit** verifizieren. Defekte GUI-Speichern-/Exportieren- und Medien-Fehlerpfade gezielt nachtesten.
- **M0.4 Clean-Machine:** Windows 11 x64 ohne Python/Buildtools, mit Offline-Sperre, mehreren echten Codecs, 100/150/200 % Skalierung und Tastaturbedienung prüfen; die tatsächlich heruntergeladene Datei samt SHA-256 verwenden. Issue **#2** erst nach Dokumentation der Ergebnisse schließen.
- **M0.5 Dokumentationshygiene:** Geschlossene Vorschläge korrekt kennzeichnen (insbesondere PR #17); veraltete 0.3-Aussagen in Architektur-/MVP-/Design-Dokumenten bereinigen. Vorhandene erfolgreiche PRs nicht als noch ungemergt beschreiben.

**Abnahme:** Gleiche Commit-/Artefaktidentität in Tests und Nachweisen, alle kritischen Regressionen grün, keine offenen P0-Datenverlust-/Originalschutzfehler; öffentliche Binärdistribution **nur** bei erfülltem Lizenz-, Windows-11- und Paket-Gate.

### M1 – 0.5: Kontinuierliche, korrekte Sequenzvorschau (P0)

**Ziel:** Anwender sehen und hören vor dem Export **die gesamte Komposition**, nicht nur einen ausgewählten Quellclip.

- Gemeinsames, Qt-freies Sequenz-/Zeitmodell mit präzisen Clip-Grenzen, Zeitleisten-Zoom, Playhead, Scrubbing und Tastatursteuerung.
- Lückenlose Video-/Audio-Vorschau über Clipschnittstellen; Pausieren, Springen, Stumm-/Pegelzustände und A/V-Synchronisation konsistent.
- Bildkorrekturen als reale Vorschau (Live- oder lokal gecachte Proxy-Ausgabe); sichtbare Kennzeichnung, wenn ein aufwendiger AI-Effekt nicht in Echtzeit dargestellt werden kann.
- Asynchroner Proxy-/Thumbnail-/Waveform-Cache mit Größenbudget, invalidierbaren Schlüsseln und sicherer Bereinigung; kein Blockieren des Qt-Ereignisloops.
- Abgleich von Vorschau und Export auf definierten Testsequenzen einschließlich unterschiedlichen FPS/Audioformaten, fehlendem Ton, Framegrenzen und Abbruch.

**Abnahme:** Eine mehrteilige Referenzsequenz lässt sich ohne manuellen Clipwechsel abspielen und entspricht an geprüften Schnitt-/Effektpunkten dem tatsächlichen Export. Nach Abbruch oder Quellwechsel gibt es keine veralteten Vorschaubilder oder verlorenen Änderungen.

### M2 – 0.6: Mehrspur-Video und Mehrspur-Audio (P1)

**Ziel:** Vom einfachen Clip-Organizer zu einem benutzbaren, aber bewusst schlanken nichtlinearen Editor.

- Video-Spuren für Hauptbild und Überlagerungen; getrennte Audio-Spuren, Spur-Mute/Solo, Lautstärke, Ein-/Ausblenden und definierte Mischregeln.
- Drag-and-Drop auf Zeitachse, Verschieben, Trimmen, Ripple-Operationen, Snap und Undo/Redo mit eindeutiger Semantik.
- Basis-Übergänge (harter Schnitt, Crossfade), einfache Titel-/Textlayer und wenige nutzerfreundliche Keyframes; keine unübersichtliche Profi-Effektbibliothek zum Start.
- Versionsmigration der Medienprojekte statt stiller Formatbrüche; Renderplan bleibt vom Qt-UI getrennt.
- FFmpeg-Filtergraphen aus strikt validierten Parametern; klare Grenzen für Spuren, Dauer, Decoderprozesse, temporären Speicher und parallele Jobs.

**Abnahme:** Überlagerung und Audiomischung einer Testkomposition werden reproduzierbar gerendert, stimmen mit der Vorschau überein und lassen sich speichern, neu öffnen, rückgängig machen und abbrechen, ohne Ausgangsmedien zu verändern.

### M3 – 0.7: Projektportabilität und Ausfallsicherheit (P1)

**Ziel:** Ein begonnenes Projekt soll zuverlässig fortgesetzt und bei Bedarf verschoben werden können.

- **Medien neu zuordnen (Relink):** fehlende/verschobene Quellen erkennen, Dateisuche anbieten, Identität/Fingerprints überprüfen und Mehrdeutigkeiten bestätigen lassen.
- **Autosave und Crash-Recovery:** versionierte, begrenzte Wiederherstellungspunkte; nur erfolgreich bestätigte Projektzustände ersetzen die Hauptdatei. Konflikte und veraltete Recovery-Stände explizit behandeln.
- **Portables Projektpaket:** optionales, explizit angefordertes Einsammeln lokaler Medien unter Quoten-, Pfad-, Größen- und Datenschutzkontrollen; keine heimliche Duplikation oder Veröffentlichung.
- Schema-Migrationen und Sicherungskopien für **.laip/.edvp/.edap**; Tests mit älteren gültigen und gezielt manipulierten Projektdateien.
- Datenschutz bei relativen/absoluten Pfaden und Metadaten, atomare Schreibvorgänge auch bei Strom-/Platzmangel-Simulation.

**Abnahme:** Ein Projekt mit mehreren Dateien übersteht Verschieben, simulierten Absturz, fehlende Medien und Fehlversuche beim Speichern; ursprüngliche Dateien und letzter gültiger Projektstand bleiben intakt.

### M4 – 0.8: Lokale KI und sinnvolle Hardwareprofile (P1/P2)

**Ziel:** Nützliche KI-Funktionen mit **nachgewiesenem** Speicherbedarf, kompatiblen Modellen und transparenten Grenzen, nicht möglichst viele Modellnamen.

- **Modellverwaltung neu entwerfen:** PR #17 nicht als vorhandene Umsetzung voraussetzen. Aufgabenorientiertes Register mit geprüfter Modellidentität, Rechte-/Quellenbelegen, Pflichtdateien, Ressourcenprofil, lokalem Import und expliziter manueller Auswahl.
- **Autoauswahl:** CPU/RAM und tatsächlich validierte Ausführungsanbieter prüfen; kleinsten funktionsfähigen Fallback behalten. Mehr RAM/VRAM darf nur zu größeren Profilen führen, wenn diese **vollständig gemessen** wurden. Nicht verfügbare Modelle als solche anzeigen.
- **Foto:** hochwertige Freistellung und gezielte lokale Bildverbesserung anhand messbarer Vergleichssätze; mögliche Inpainting-/Upscaling-Optionen erst nach Rechte- und Qualitätsprüfung.
- **Audio:** lokale Sprache-zu-Text-Transkription mit editierbaren Untertiteln/Markern als erste Erweiterung; Rauschminderung und Verständlichkeitsverbesserung nur nach hörbasierten Vergleichstests.
- **Video:** optional bessere Entrauschung und zeitliche Konsistenz über aufeinanderfolgende Frames; Bewegungsfehler/Flackern und Ton-/Bild-Synchronisation messen. „Eingebrannte Filter entfernen“ nur als begrenzte Abschwächung/Restaurierung bezeichnen, nie als garantierte Rekonstruktion.
- **GPU-Evaluierung:** CPU bleibt Referenz. DirectML/CUDA/andere Anbieter einzeln nach OS/GPU/Treiber, Modell und Speicherverbrauch testen; keine pauschale „GPU-Unterstützung“ aufgrund einer erkannten Grafikkarte.
- **Verteilung:** Zusatzmodelle als getrennt geprüfte Offline-Pakete, nicht als heimlichen Runtime-Download. Quellcode, Gewichte und ONNX-Konvertate jeweils separat lizenzieren und dokumentieren.

**Abnahme:** Pro freigegebenem Modell ein reproduzierbarer Real-Inferenztest, Prüfsummen/Provenienz, Offline-Test, Ressourcen- und Qualitätsmessungen, manuelle Übersteuerung, verständliche Fehler/Fallbacks sowie saubere Deinstallation. Keine Modellfreigabe allein aufgrund von Mock-Tests.

### M5 – 0.9: UX, Foto-Vertiefung und Beta-Härtung (P0 vor 1.0)

**Ziel:** Die häufigsten Aufgaben sollen für Gelegenheitsnutzer zuverlässig und ohne Expertenwissen funktionieren.

- Workflows über alle drei Editoren vereinheitlichen: echte Vorschau, Vorher/Nachher, Anwenden/Abbrechen, Projektstatus, Export, Fortschritt, Warnungen und sichere Rückwege.
- Foto: nichtdestruktive Korrektur-Rezepte, feineres Masken-Handling, zielgerichtete Retusche und klar erklärte Qualitätsoptionen; **Ebenen, RAW/HDR und generative Editierung** nur nach gesonderter Architektur-/Leistungsentscheidung.
- Fenster und wichtige Dialoge bei 640 × 480 logischen Pixeln sowie 100/150/200 % Skalierung prüfen; **primäre Aktionen jederzeit sichtbar**, alle weiteren Werkzeuge ohne abgeschnittene/nicht erreichbare Bedienelemente. Vollständige gleichzeitige Sichtbarkeit jeder erweiterten Option ist bei kleinen Fenstern kein sinnvolles Versprechen.
- DE/EN vollständig und verständlich; Tastaturpfade, Fokusführung, High-Contrast und Screenreader mit manuellen und automatisierten Prüfungen testen.
- Eingabe-/Codec-Matrix mit echten Testmedien; Laufzeit-, Abbruch-, Arbeitsspeicher-, Disk-/Proxy-Budgets und Performance-Baselines auf benannten Testsystemen dokumentieren.
- SBOM/Dependency-Scanning, Absturz-/Ressourcentests, untrusted-media-Fuzzing wo sinnvoll, reproduzierbare Builds und Nachvollziehbarkeit der Commit-/Paketzuordnung.

**Abnahme:** Definierte End-to-End-Szenarien für alle drei Editoren ohne P0/P1-Defekte, getestete Accessibility- und Hardwarematrix; keine UX-Texte, die nicht vorhandene KI-, Codec- oder Distributionsfähigkeiten versprechen.

### M6 – 1.0: Stabile, öffentliche Windows-Version (Release-Gate)

- Alle tatsächlich auszuliefernden Drittkomponenten **rechtlich freigegeben**, inkl. Qt-LGPL-/Quellenpflichten, FFmpeg-Build-/Codec-Konfiguration und jedes Modells/Exports.
- Windows-11-Clean-Machine-Test mit heruntergeladenem **exakten Releasepaket**; wirksame Offline-Prüfung; SHA-256, Buildmanifest, SBOM, Versions- und Commitidentität.
- Definierte, bewährte Installations-/Portable-Variante und Deinstallation; Code-Signierung und sichere Update-Strategie vor produktiver Endnutzerempfehlung vorsehen.
- Release Notes, bekannte Einschränkungen, DE/EN-Hilfe, Support-/Security-Policy, Codec-/Hardware-Supportmatrix und Rollback-Plan bereitstellen.
- Vor der Veröffentlichung Prüfung auf private Metadaten, unzulässige Artefakte, Modellgewichte und personenbezogene Inhalte.

**Go/No-Go:** Nur das positiv geprüfte Paket darf als 1.0 ausgeliefert werden. Falls Lizenzrechte, Windows-Abnahme, kritische Sicherheit oder Datenintegrität offen sind, bleibt **main öffentlich, aber die Binärfreigabe gesperrt**. Technisch mögliche Features ohne belastbare QA werden aus 1.0 verschoben.

## 5. Querschnittstests pro Arbeitspaket

Jeder Feature-PR enthält mindestens: dokumentierten Nutzerfall, betroffene Schnittstellen/Dateiformate, DE/EN-Texte, Unit-/Integrationsregressionen (inkl. Fehler/Abbruch/Undo), unveränderte Quelldateien und relevante Versions-/Sicherheitstests. Bei Medienänderungen zusätzlich tatsächlichen FFmpeg-Export und reproduzierbare Zeit-/Codec-Szenarien; bei KI einen **echten** Modelllauf; bei UI Geometrie/Fokus- und Screenshot-Prüfungen; bei Windows-/Buildänderungen Source- und Standalone-Smokes. **Fehlende Tests benennen, nicht als grün ausgeben.**

Dokumentation, README-Funktionsmatrix, Lizenzhinweise und Releases müssen denselben nachgewiesenen Stand beschreiben. Features bleiben separat aktivierbar oder werden aus einem Release ausgenommen, wenn Test- bzw. Rechte-Gates fehlen. Branchschutz/Reviews bleiben wirksam. Keine vertraulichen Pfade, privaten Medien, persönlichen E-Mail-Adressen oder generierten Gewichte in öffentlichen Commits.

## 6. Unmittelbarer Arbeitsvorrat

| Reihenfolge | Paket | Nachweis/Definition of Done |
| --- | --- | --- |
| **1 / P0** | **M0.5** Roadmap und veraltete 0.3-/PR-17-Behauptungen bereinigen | Aktuelles main und PR-Zustände in allen Einstiegstexten korrekt |
| **2 / P0** | **M0.1–2** Lizenz-/SBOM-Inventar der exakt verteilten Assets und historische Download-Erreichbarkeit | Prüffähiger Report; Issue #3 nachweisbasiert |
| **3 / P0** | **M0.3–4** Binär-Smokes, Clean Windows 11 und Offline-Abnahme | CI-/Artefakt-SHA, Endanwender-Protokoll, Issue #2 |
| **4 / P0** | **M1** Sequenz-Zeitbasis, Ganzsequenzwiedergabe und Vorschau-/Export-Vergleich | Mehrclip-Video und -Audio mit geprüften Grenzen konsistent |
| **5 / P1** | **M3** Portable Medienpakete und restliche Recovery-Fälle | Relinking und Recovery-Checkpoints für bereits gespeicherte Audio-/Videoprojekte sind integriert; Portabilität, nie gespeicherte Projekte und vollständige Abnahme fehlen |
| **6 / P1** | **M2** Mehrspur-Rendermodell, Übergänge und Audiomischer | Reproduzierbarer Mehrspur-Export und Undo |
| **7 / P1** | **M4** Modellregister mit CPU-Baseline und genau einem neu validierten Modellpfad | Keine unerkannten Downloads, Lizenzen/HW-Budget geprüft |
| **8 / P0** | **M5/M6** Endanwender- und Distributionsfreigabe | Alle definierten Go/No-Go-Kriterien erfüllt |

### Was ausdrücklich nicht als bereits fertig gilt

Whisper/IS-Net-Modellprofile aus dem geschlossenen PR #17, automatische Modell-Hardwareauswahl, GPU-Beschleunigung, komplette Videorestaurierung, Sprachtranskription, Mehrspurmontage, kontinuierliche Gesamtvorschau, portables Medienprojekt, Windows-11-Endanwender-Abnahme und öffentliche Binärlizenzfreigabe. Diese Funktionen/Prüfungen sind **Ziele oder offene Gates**, keine bestehenden Produkteigenschaften.

**Verwandte Nachweise:** [Implementierungsgrenzen](MEDIA_PROJECTS_AI.md) · [0.4-Video-KI](VIDEO_RESTORATION.md) · [Modellprovenienz](MODELS.md) · [Release-Checkliste](PUBLIC_RELEASE_CHECKLIST.md) · [Verifikation](VERIFICATION.md) · [Issues #2 und #3](https://github.com/Cenn0/Edivora/issues).
