# Public Windows release checklist

**Current status:** Edivora source is public under Apache-2.0. A Windows binary distribution has not been approved.

- Inventory every redistributed file, including transitive Python packages, Qt libraries/plugins, FFmpeg executable and AI model weights; generate an SBOM.
- Verify licensing of each exact binary/converted model asset, not merely the source repository or Python wrapper. Retain license notices and satisfy applicable corresponding-source obligations.
- Record exact FFmpeg `-version`, `-buildconf`, `-L` output, enabled codecs, source/build procedure and notices.
- Verify Qt/PySide6 library replacement rights and exact, version-matched Qt sources and third-party notices.
- Verify provenance and redistribution rights of ONNX weights, exported models and tokenizers (including any introduced by open pull requests).
- Test the downloaded Windows package offline, on a clean Windows 11 device, including media import/export, CPU inference and source-file protection.
- Publish binary SHA-256, build revision, reproducible package manifest, known limitations, support scope and all necessary legal notices.
- Check commit metadata, workflow logs, GitHub release assets and downloadable artifacts for private information before publishing.

Public GitHub repository settings such as branch rules, vulnerability reporting, secret scanning and dependency alerts require separate configuration. Adding documentation does not enable those settings.

See [third-party notices](../THIRD_PARTY_NOTICES.md), [model provenance](MODELS.md), and [Qt sources](QT_SOURCES.md).
