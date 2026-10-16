# Edivora – Markenauftritt und Assets

**Produktname:** Edivora · **DE:** „Einfach kreativ. Alles lokal.“ · **EN:** “Create simply. Stay local.”

Der Produktname umfasst **Edivora Photo**, **Edivora Video** und **Edivora Audio**. Alle drei sind im Quellcode als Arbeitsbereiche implementiert. „Edivora AI“ bezeichnet unterstützende lokale Fähigkeiten, **keine vierte App**. Der ältere veröffentlichte Foto-Alpha-Download trägt absichtlich noch die Bezeichnung **LocalAiPhotoEditor**.

## Logo und Wortmarke

Die SVGs liegen versioniert **im Repository**, nicht auf einem CDN. Sie enthalten keine externen Fonts, Bilder oder Skripte. Die frühere Bildmarke wurde durch eine eigene E-/Kamera-Blenden-/Audiowellen-Gestaltung ohne Play-Dreieck ersetzt. Das Banner beschreibt weiterhin den aktuellen Entwicklungsstand; Konzeptgrafiken sind von echten Screenshots getrennt.

| Asset | Vorschau | Einsatz |
| --- | --- | --- |
| `edivora-mark.svg` | ![Edivora Bildmarke](../src/local_ai_photo_editor/assets/edivora-mark.svg) | App-Fenster, Launcher, Taskleiste, Windows-Icon-Quelle |
| `edivora-mark-mono.svg` | ![Einfarbige Edivora Bildmarke](../src/local_ai_photo_editor/assets/edivora-mark-mono.svg) | Monochrome Darstellungen |
| `edivora-wordmark.svg` | ![Edivora Wortmarke mit Motto](../src/local_ai_photo_editor/assets/edivora-wordmark.svg) | README, Projektstart und Dokumentation |
| `edivora-banner.svg` | ![Edivora Foto-, Video- und Audiobereiche](../src/local_ai_photo_editor/assets/edivora-banner.svg) | Produktüberblick der aktuellen Quellcode-Suite |

Dateipfade: `src/local_ai_photo_editor/assets/`. In den Kopfzeilen des Launchers und aller drei Editoren werden die SVG-Daten durch QtSvg lokal gerendert; beim **Windows-Build** erzeugt `tools/brand_assets.py` ein ICO aus demselben Logo. `tools/build_windows.py` bindet SVG-Ressourcen sowie das ICO in den Entwicklungsbuild ein. **Dies ist eine Implementierung, kein Nachweis eines erfolgreich getesteten neuen Windows-Pakets.**

## Farben und Anwendung

| Rolle | Farbe |
| --- | --- |
| Midnight/Hintergrund | `#171B2D` |
| Türkis/Primär | `#4FF3D3`, `#18B9C6` |
| Blau/Video | `#7792FF`, `#4E56E9` |
| Violett/KI und Audioakzente | `#C98CFF`, `#8759E9` |
| Heller Kontrast | `#F5F4FF` |

Die eigentliche UI-Tokenquelle ist `src/local_ai_photo_editor/ui/theme.py`; Abstände, Interaktionen und Accessibility stehen in [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md). Die Bildmarke ist **nicht** Ersatz für eine lesbare Beschriftung. Texte müssen bei Verkleinerung und im Dark Mode lesbar bleiben; Status nie allein über Farbe vermitteln. Für technische Dokumentation Alt-Texte ergänzen. Für neue Screenshots reale Oberflächen verwenden, keine als Produktscreenshot ausgegebenen Prototypen.

## Benennung, Kompatibilität und Status

- Die öffentliche Marke heißt **Edivora**; der interne Python-Namespace bleibt **`local_ai_photo_editor`**. Der Einstieg `python -m local_ai_photo_editor` und das bestehende `edivora`-Script-Alias bleiben gültig.
- Das bestehende Foto-Projektschema **`.laip`** und seine interne Formatkennung werden **nicht** umbenannt. Medienprojekte verwenden **`.edvp`** und **`.edap`**.
- Der aktuelle Windows-Entwicklungsbuild schreibt weiterhin `dist/LocalAiPhotoEditor/LocalAiPhotoEditor.exe` und bekommt nun das Edivora-App-Icon. Das unveränderte veröffentlichte `v0.1.0-alpha.1`-ZIP bleibt beim alten Dateinamen und Inhalt.
- Dokumentation, Icons und Versionshinweise müssen immer unterscheiden zwischen *Quellcode implementiert*, *durch Tests nachgewiesen* und *als Endnutzer-Paket veröffentlicht*.
- Der Markenname wurde **nicht rechtlich freigeprüft**. Vor einer öffentlichen kommerziellen Verwendung sind Markenrecherche (etwa DPMA und EUIPO), Domain-/Namensrechte sowie Bildmarke separat zu prüfen; keine Verwendung des Zeichens `®` ohne Registrierung.

## Asset-Änderungen prüfen

Wenn du ein Logo bearbeitest, kontrolliere `viewBox`, Kontrast, kleinere Darstellungen, Lesbarkeit, fehlende externen URLs und die aus dem SVG abgeleitete Windows-ICO-Ausgabe. Führe `PYTHONPATH=src python -m unittest discover -s tests -p 'test_branding.py' -v` in geeigneter Umgebung aus und prüfe neue UI-/Windows-Screenshots, bevor du Branding in einem Release versprichst.

## Aktuelle Designvorlagen

[Light- und Dark-Designs samt Farbtokens](branding/README.md). Diese Grafiken sind Konzepte und keine implementierten UI-Nachweise.
