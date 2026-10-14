# Edivora – vier lokale KI-Modelle und Hardwareprofile

**Status: Entwicklungsstand 0.4.0 Alpha**, nicht der alte Foto-Release. Windows-Pakete gelten erst nach erfolgreicher CI-Verifikation als erstellt und getestet.

## Funktionale Auswahl

In allen Editoren befindet sich die Schaltfläche **KI-Modelle …**. Die Einstellungen werden lokal mit QSettings gespeichert, pro Aufgabe entweder automatisch oder manuell ausgewählt, und als streng begrenzte Modell-ID an den getrennten lokalen Worker übergeben. Keine Runtime-Downloads, Konten oder externen API-Dienste.

| Aufgabe | Modell | Tatsächliche Funktion |
| --- | --- | --- |
| Foto und Video-Standbild: Freistellung | U2NETP (schnell) oder IS-Net (aufwendiger) | Bild-/Standbild-Freistellung; kein zeitliches Video-Matting |
| Audio: Sprachbereiche | Silero VAD 6.2.1 | Markiert Spracherkennungsvorschläge, keine Transkription |
| Audio/Video: Transkription | Whisper Tiny multilingual INT8 | Lokal gespeicherte TXT-/SRT-Datei des gewählten Clip-Ausschnitts |

Whisper bearbeitet höchstens drei Minuten je Vorgang, spricht Deutsch/Englisch und legt SRT-Grenzen **grob pro 20-Sekunden-Block** fest. Die Ausgabe ist kein wortgenaues Untertitel-Alignment und muss geprüft werden.

## Die vier enthaltenen Modellfamilien

| ID | Gewichte | Quelle | Rolle |
| --- | --- | --- | --- |
| u2netp | 4,6 MB ONNX | bisheriges checksum-gepinntes rembg U²-Net P | Leichte, schnelle CPU-Segmentierung |
| isnet-general-use | ca. 170 MB ONNX | [rembg v0.0.0](https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx), [DIS](https://github.com/xuebinqin/DIS) | Detailorientierte 1024×1024-Segmentierung, nicht immer objektiv besser |
| silero-vad | 2,33 MB ONNX | [Silero VAD v6.2.1](https://github.com/snakers4/silero-vad/tree/v6.2.1) | Sprachaktivität ohne Spracherkennung |
| whisper-tiny | ca. 103 MB INT8-ONNX plus Text-Tokenizer | [sherpa-onnx Whisper Tiny](https://huggingface.co/csukuangfj/sherpa-onnx-whisper-tiny) und [Runtime](https://pypi.org/project/sherpa-onnx/1.13.0/) | Multilinguale CPU-Transkription |

**Nicht enthalten:** Whisper Base/Small/Large, FLUX, neurale Audio-Rauschfilter, eine Video-Diffusionspipeline oder eine GPU-Inferenzruntime.

## Automatische Auswahl – Hardwareheuristik

Die Anwendung misst Gesamtspeicher, aktuell freien RAM und logische CPU-Kerne. Aus den **für eine bestimmte Aufgabe** geeigneten installierten Modellen wählt sie die anspruchsvollste vernünftige Stufe, nicht schlicht die größte Datei.

| Modell | Empfohlener Startpunkt für Automatik |
| --- | --- |
| U2NETP | 1 GiB RAM gesamt, 1 GiB frei, 1 logischer Kern |
| IS-Net | 8 GiB RAM gesamt, 3 GiB frei, 4 logische Kerne |
| Silero VAD | 2 GiB RAM gesamt, 1 GiB frei, 1 logischer Kern |
| Whisper Tiny | 4 GiB RAM gesamt, 2 GiB frei, 2 logische Kerne |

Das sind **Startheuristiken**, keine hardwaregemessenen offiziellen Mindestanforderungen. Ist eine Speicherangabe nicht messbar, bleibt die Autoauswahl konservativ. Manuelle Wahl eines vorhandenen größeren Modells trotz Unterschreitung wird nach Warnung zugelassen; Speichermangel/Abbruch sind weiterhin möglich.

### Technische Einordnung

- **Funktioniert grundsätzlich:** Alle vier Modelle haben eine definierte lokale CPU-Verarbeitung. Die neue CPU-Inferenz muss für den jeweiligen Paket-Build im realen Smoke-Test bestanden sein.
- **Offiziell unterstützt in Edivora:** In diesem Stand ausschließlich CPU. GPU-Präsenz allein bedeutet weder CUDA noch DirectML-Support, auch nicht bei hoher GPU-VRAM-Kapazität.
- **Best Practice:** Automatik je Aufgabe, Vorschau prüfen, manuell abweichen für spezielle Motive. Modellgröße ist kein allgemeiner Qualitätsbeweis.
- **Sicherheit:** Keine frei wählbaren ONNX-/Skriptpfade und keine Runtime-Downloads. Modelle kommen aus Allowlist und werden per Digest kontrolliert. Getrennte Worker sind keine Malware-Sandbox gegen manipulierte Decoderdateien.

## Integrität und Vertrauensgrenzen

U2NETP, IS-Net und Silero sind durch feste SHA-256-Digests gepinnt. Für IS-Net gilt: 60920e99c45464f2ba57bee2ad08c919a52bbf852739e96947fbb4358c0d964a.

Whisper Tiny hat einen fixierten Quellenstand 65176e2. INT8-Encoder: d24fb083ae3b1041fc24e97971d60e280c9342201fbb67b0ab428a8b4a51a434; INT8-Decoder: d2fece8dd42771f1df975c6c0445770d0c292bf7547c2cae04a6c0cc57540925. Für die externe Klartext-Tokenizerdatei liegt **kein vorab unabhängig bestätigter SHA-256-Wert** vor. Das Buildwerkzeug lädt sie aus der gepinnten Revision, prüft die Dateigröße, ermittelt einen SHA-256 beim Paketbau und speichert ihn in einem lokalen Begleitmanifest, gegen das zur Laufzeit geprüft wird. Das ist schwächer als eine unabhängig verifizierte feste Digest-Vorgabe und bleibt eine Härtungsaufgabe.

Die drei expliziten Buildwerkzeuge bereiten die vier Modelle vor:

- tools/prepare_model.py – U2NETP
- tools/prepare_voice_model.py – Silero
- tools/prepare_extra_models.py – IS-Net und Whisper Tiny

Ein GUI-Aufruf löst niemals einen Download aus. Der Windows-Build muss fehlschlagen, wenn ein benötigtes Paketgewicht fehlt oder die Integritätsprüfung scheitert. Die Endnutzer-Redistribution des konkreten U2NETP-Assets, FFmpeg/Qt und des zusätzlichen ASR-Runtimes benötigt eine separate Lizenz-/Quellprüfung vor öffentlicher Freigabe.

## Softwaremodule und Zukunft

ai/catalog.py liefert Modellregister, Speicherprofil und Auswahlentscheidungen. ai/background.py integriert IS-Net neben U2NETP. ui/model_settings.py stellt eine einzige bilinguale Oberfläche bereit. ai/transcribe.py verwendet sherpa-onnx für lokale Transkription. worker.py und ai/video_frame.py akzeptieren nur zulässige Modell-IDs. tools/build_windows.py muss alle vier Modelle und das Begleitmanifest verifizieren.

Für die Zukunft sind größere Sprachmodelle, neurale Geräuschfilter, zeitliche Video-Segmentierung und optional DirectML/CUDA denkbar. **Sie sind nicht enthalten und werden nicht als unterstützt angegeben**, bevor passende Laufzeiten, Lizenzen und echte Benchmarks vorliegen.
