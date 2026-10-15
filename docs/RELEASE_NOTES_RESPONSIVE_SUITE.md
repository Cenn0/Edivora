# Edivora 0.4.0a1 — responsive editing and video picture improvements

Development alpha, not a stable or officially accepted Windows 11 release.
The 0.3 and historical 0.1 packages do not contain these changes.

- **Launcher:** direct Photo/Video/Audio opening; no selection checkboxes or bulk
  button. Stays open; independent editors; Alt+1/2/3.
- **Shared UI:** original vector icons, accessible DE/EN names, compact toolbars,
  flexible previews, media inspector tabs, scroll-safe settings, logical minimum
  640 × 480. Updated photo windows and editing dialogs as well as media editors.
- **Video:** seven non-destructive corrections, adjustable presets, actual
  before/after frame preview and explicit acceptance. Stored per clip and applied
  during export. HD/Full HD output selection; ordinary playback remains original.
- **Local video AI:** verified DnCNN color denoising for short selected clips,
  adjustable strength, real CPU worker, source audio retained, separate derived
  MP4, cancellation without replacing an existing destination.
- **Video/audio:** bounded Undo/Redo, correctly reloaded duplicate/history clips,
  mute changes recorded immediately and save checkpoints preserved.
- **Projects:** version 2 stores video recipes; version 1 remains readable. Older
  applications cannot read new version-2 projects. No media embedding/autosave.
- **Safety and evidence:** bounded jobs, owned native children, alias protection,
  real synthetic processing tests and source/standalone UI/DPI smoke checks.

## Important limits

DnCNN is not a generic filter remover. Embedded beauty effects, clipped colors
or lost detail cannot be reconstructed exactly. AI currently handles at most
30 seconds at up to 720p/30 fps, frame by frame on CPU; processing may be slow and
can smooth detail or flicker. Preview is a lower-resolution still. Conventional
corrections are not mislabeled as AI. Full HD export is not neural upscaling.

No multitrack mixing, transitions, whole-sequence live playback, GPU deployment,
generative video, transcription or new model-profile selector is introduced.
The suite is unsigned and intended for private evaluation; licensing,
real-world codec/hardware coverage and clean Windows 11 acceptance remain open.
See [detailed workflow, provenance and constraints](VIDEO_RESTORATION.md).
