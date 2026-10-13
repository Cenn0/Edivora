# Local project files (.laip) — format version 1

Status: implemented on a development branch following the private v0.1.0-alpha.1 release. The published alpha ZIP **does not yet contain this feature**; it must pass CI and a new packaged acceptance run before inclusion in a future release.

## User workflow

1. Open a JPEG, PNG or WebP photo and edit it normally.
2. Choose **File → Save project** (Ctrl+S) to create a .laip file.
3. Choose **File → Open project** or drag a .laip file into the editor to resume later.
4. **Save project as** creates another independent project. **Export a copy** creates a flattened PNG, JPEG or WebP and does **not** update the editable project.

Projects contain a lossless copy of the imported, orientation-adjusted sRGB original, the accepted current pixels, retained in-memory undo and redo images, and their labels. The same 256 MiB default pixel-history budget applies. History snapshots already discarded from memory cannot be recovered by saving a project. Active slider previews and crop selections must be applied or discarded before saving; a running AI job must finish or be cancelled.

Saving a project after an edit marks the editable project clean; exporting a picture does not. The editor warns when a project has unsaved edits on close or replacement. Project archives can be large, and encoding them currently blocks the UI briefly on large photos. No automatic recovery, background autosave, or recovery from crashes is promised in this version.

## Privacy and source protection

- All project data is written locally; no server, model host or telemetry is involved.
- Original EXIF, GPS, XMP and comments are **not** stored; input pixels have already been normalized to 8-bit sRGB.
- The absolute original file path and username are deliberately **not** stored. The **photograph itself**, and visible details within it, *are* stored inside the project archive. Do not share private project files inadvertently.
- An open photo still cannot be exported over its original location or its aliases.
- After reopening a project, the original source path is unknown. To preserve the stronger original-protection guarantee, the editor refuses to replace **any pre-existing image export** unless that path was created by the current editor session. Choose a new export filename. The original photo is never read from disk again when opening the project.
- The project file and any saved export can be synchronized by third-party software if the user chooses a cloud-synchronized folder.

## Archive schema

ZIP container, stored entries (not deflated), UTF-8 JSON manifest at manifest.json, lossless PNG frames. The format identifier is local-ai-photo-editor-project and version is currently 1.

- frames/original.png — imported pixels, including their transparency
- frames/current.png — last accepted edit result
- frames/undo-N.png — each *retained* undo snapshot, oldest first
- frames/redo-N.png — each *retained* redo snapshot, oldest to newest
- manifest.json — frame descriptors (exact names, width, height, RGB/RGBA mode, SHA-256 of encoded PNG), operation labels, pixel-history budget and version

The JSON manifest is an allowlist, not an executable script. Opening a project **never extracts archive paths** into the filesystem. It rejects duplicate, missing and unknown members; encrypted or unsupported compression; version mismatches; bad SHA-256 checksums; mismatched image metadata; excessive sizes; and inconsistent undo labels. Individual frames cannot exceed the 40-megapixel product limit; encoded frame entries have an approximately 162 MiB ceiling, total uncompressed archive data a 768 MiB ceiling, and the manifest a 1 MiB ceiling. These limits are defensive and do not constitute a total RAM-use guarantee.

## Failure and versioning

Saves use a temporary file in the target directory, flush/fsync and atomically replace the target only after successful encoding. Save errors leave existing project files unchanged. A failed open leaves the currently edited photo unchanged. Loading accepts version 1 only. Any future format change must preserve an explicit migration path rather than silently treating incompatible layouts as version 1.

**Testing:** The project suite covers round-tripping current, original and undo/redo pixels and labels; bounded-history behavior; source alias protection; atomic replacement and failure cleanup; malformed archives, duplicates, checksum tampering, unexpected ZIP members, version errors and oversized dimensions. Actual packaged Windows GUI acceptance remains a separate test gate.
