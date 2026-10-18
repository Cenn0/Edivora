# Portable Edivora audio/video project folders (source-only experimental tool)

The current media editor normally keeps source files in their original locations.
Its \`.edvp\` and \`.edap\` manifests may include absolute local paths and are not
portable by themselves. The **source checkout** now includes an explicit
bounded utility that creates a new portable *directory*, not a ZIP archive.

## Run

Install Edivora from source according to [Getting started](GETTING_STARTED.md).
First **save** the project in the video/audio editor, then run:

\`python tools/export_portable_media.py "/path/to/saved.edap" "/path/to/new-portable-folder"\`

The second path **must not exist**. The command creates a directory containing
\`project.edap\` or \`project.edvp\` and \`media/01.wav\`, \`media/02.wav\`, etc.,
with only relative references. Copy the complete directory to another machine
and open its \`project.edap\`/\`project.edvp\` through the corresponding editor.
The original saved project and original media files are not modified.

## Constraints and security

- **Source-only CLI:** no polished export button in the Windows UI and no
  end-user package acceptance; this is a partial M3 implementation.
- **Offline:** no network requests, archiving, extraction, symlinks in the
  package, telemetry, or model download.
- **Strict size limit:** 2 GiB of unique original media at most, 24 clips at
  most; the same source referenced by multiple clips is copied only once.
  Some legitimate large video projects will be rejected.
- **Integrity:** source data is re-read and hashed in full during preparation
  to detect a file changing while being copied; each packaged reference then
  passes the existing project/fingerprint validator. This does not make native
  multimedia decoders safe for untrusted files.
- **Failure behavior:** cancellation, failed validation, quota or I/O errors
  discard the private staging directory; no pre-existing destination is
  intentionally replaced.
- **Privacy:** filenames are replaced with numbered local names, and the new
  project does not expose the original absolute media paths. However, media
  payloads may contain EXIF/metadata, embedded names, voices, geolocation,
  faces or private content. Inspect all files before sharing.
- **Not included:** photo \`.laip\`, inline thumbnails, model weights, plugin
  assets, project recovery checkpoints or an exported Windows runtime.

This utility is experimental source functionality and does **not** establish
the legal clearance to publish Windows packages. See [Roadmap](ROADMAP.md)
and [Public release checklist](PUBLIC_RELEASE_CHECKLIST.md).
