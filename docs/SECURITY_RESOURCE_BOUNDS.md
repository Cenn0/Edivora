# Resource limits and native media-AI process ownership

This document describes code introduced in the security remediation for report(3)
(frozen `main` revision `8ddcba6726641fd00568eb206b6f05943f40f8d8`).

## Photo project imports

The `.laip` loader first validates **every** frame descriptor (including
original/current and all undo/redo images), computing decoded 8-bit RGB/RGBA
bytes from dimensions and mode. It rejects history exceeding the saved budget
(up to 256 MiB) **before** calling Pillow to decode even the first frame.
Each original/current frame has the existing 40 MP bound and both contribute
to retained-pixel accounting.

The 256 MiB budget is for retained undo/redo pixels, **not** an OS memory
quota. Pillow decoder allocations, temporary normalization copies, Python
objects and the base original/current images consume additional memory.
Opening a large but valid project still takes time in the Qt event loop;
isolating that operation in a bounded loading worker is separate work.

## FFmpeg I/O

- Voice PCM decoding writes a bounded-duration, fixed-format stream to a
  temporary file. Its size is validated before PCM bytes are loaded into RAM.
- Voice and video-frame decoding discard FFmpeg stderr rather than buffering
  untrusted diagnostic output. Malformed file errors are reported generically.
- Audio waveform preview redirects stderr to Qt's null device. Its existing
  standard-output and wall-clock bounds remain in place.
- Fixed FFmpeg argv/protocol restrictions and source non-overwrite policies
  are unchanged; these measures are **not** native decoder sandboxes.
- Voice PCM on-disk output is time-limited; temporary disk consumption remains
  possible up to the fixed-format duration, and extreme host failure can
  interrupt ordinary cleanup.

## Cancellation and worker ownership

The media-AI worker always establishes its OS process-tree boundary **before
launching FFmpeg**.

- On Windows, the worker owns a native Job Object using
  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Child FFmpeg inherits membership;
  when the worker is killed or exits, closing its only job handle terminates
  associated descendants. Windows 8+/Server 2012+ supports nested jobs; if
  assignment is unavailable, the worker fails closed before starting FFmpeg.
- On POSIX, Qt 6.12 creates the worker in a fresh session before exec;
  cancellation signals the verified process group (worker + FFmpeg), not a
  single PID or the editor's session.
- On normal completion, existing FFmpeg timeouts and temporary-file cleanup
  still apply. Forced termination may prevent Python finally blocks and
  leave empty/transient OS temp files after a crash; the OS tree control bounds
  running descendants, not guaranteed crash-consistent temporary cleanup.

The new regression uses a synthetic sleeping descendant on Windows and POSIX.
It does not exercise every hardware codec. Windows-native package testing and
actual Windows 11 acceptance are separate release criteria.

## Changes to keep out of scope

No new remote AI, runtime downloads, video denoiser, codec change, model
weights or public redistribution approval is introduced. A future new media
worker must use the same process ownership primitive; simply killing its
outer QProcess does **not** contain nested native processes.
