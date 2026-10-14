"""Safe one-process FFmpeg render plan for a bounded media clip sequence.

A single FFmpeg child process means cancel terminates the actual encoder; it
does not leave a detached chain of render workers behind. The filtergraph
contains only validated fixed operations and formatted numeric parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import uuid

from .media import AUDIO_OUTPUTS, protects_source
from .media_project import MediaSequence

VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS = 30


def _seconds(value: int) -> str:
    return f"{value / 1000:.3f}"


@dataclass(frozen=True)
class SequenceExport:
    sequence: MediaSequence
    destination: Path

    def validated(self) -> "SequenceExport":
        seq = self.sequence.validated()
        output = Path(self.destination).expanduser().absolute()
        allowed = {".mp4"} if seq.kind == "video" else AUDIO_OUTPUTS
        if output.suffix.lower() not in allowed or not output.parent.is_dir():
            raise ValueError("Choose an existing folder and supported output extension.")
        if output.is_symlink():
            raise ValueError("Symlink output destinations are not supported.")
        for clip in seq.clips:
            if not protects_source(clip.source, output):
                raise ValueError("The original media cannot be overwritten.")
        return self

    def temp_output(self) -> Path:
        self.validated()
        return self.destination.parent / (
            f".edivora-sequence-{uuid.uuid4().hex}{self.destination.suffix.lower()}"
        )

    def ffmpeg_arguments(self, temporary: Path) -> list[str]:
        self.validated()
        temporary = Path(temporary)
        if (temporary.parent.resolve() != self.destination.parent.resolve()
                or temporary.suffix.lower() != self.destination.suffix.lower()
                or temporary.is_symlink()):
            raise ValueError("Temporary export must be a new file in the destination folder.")
        if any(not protects_source(c.source, temporary) for c in self.sequence.clips):
            raise ValueError("Refusing to overwrite a source via a temporary destination.")

        clips = self.sequence.clips
        # Inputs always appear before filter_complex. The explicit protocol
        # allowlist blocks protocol fetches from nested media playlists too.
        args = ["-nostdin", "-hide_banner", "-loglevel", "error", "-nostats",
                "-filter_complex_threads", "2", "-threads", "2"]
        for clip in clips:
            args += [
                "-protocol_whitelist", "file,pipe,data",
                "-i", str(clip.source.resolve()),
            ]
        silent_indices: dict[int, int] = {}
        if self.sequence.kind == "video":
            for i, clip in enumerate(clips):
                if clip.mute or not clip.has_audio:
                    silent_indices[i] = len(clips) + len(silent_indices)
                    args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]

        filters: list[str] = []
        for i, clip in enumerate(clips):
            begin, end, length = map(_seconds, (clip.start_ms, clip.end_ms, clip.length_ms))
            if self.sequence.kind == "video":
                filters.append(
                    f"[{i}:v:0]trim=start={begin}:end={end},setpts=PTS-STARTPTS,"
                    f"fps={VIDEO_FPS},scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
                    "force_original_aspect_ratio=decrease,"
                    f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
                    f"setsar=1,format=yuv420p[v{i}]"
                )
            if i in silent_indices:
                stream, trim = f"[{silent_indices[i]}:a:0]", f"duration={length}"
                level = 1.0
            else:
                stream, trim = f"[{i}:a:0]", f"start={begin}:end={end}"
                level = clip.volume_percent / 100
            filters.append(
                f"{stream}atrim={trim},asetpts=PTS-STARTPTS,"
                "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"volume={level:.2f}[a{i}]"
            )

        n = len(clips)
        if self.sequence.kind == "video":
            pairs = "".join(f"[v{i}][a{i}]" for i in range(n))
            filters.append(f"{pairs}concat=n={n}:v=1:a=1[outv][outa]")
            args += ["-filter_complex", ";".join(filters), "-map", "[outv]", "-map", "[outa]"]
            args += [
                "-c:v", "mpeg4", "-q:v", "4", "-pix_fmt", "yuv420p",
                "-r", str(VIDEO_FPS), "-c:a", "aac", "-b:a", "160k",
                "-movflags", "+faststart",
            ]
        else:
            streams = "".join(f"[a{i}]" for i in range(n))
            filters.append(f"{streams}concat=n={n}:v=0:a=1[merged]")
            master: list[str] = []
            if self.sequence.normalize:
                master.append("loudnorm=I=-16:LRA=11:TP=-1.5")
            if self.sequence.fade_in_ms:
                master.append(f"afade=t=in:st=0:d={_seconds(self.sequence.fade_in_ms)}")
            if self.sequence.fade_out_ms:
                start = self.sequence.length_ms - self.sequence.fade_out_ms
                master.append(
                    f"afade=t=out:st={_seconds(start)}:"
                    f"d={_seconds(self.sequence.fade_out_ms)}"
                )
            if master:
                filters.append("[merged]" + ",".join(master) + "[outa]")
            args += [
                "-filter_complex", ";".join(filters),
                "-map", "[outa]" if master else "[merged]", "-vn",
            ]
            if self.destination.suffix.lower() == ".mp3":
                args += ["-c:a", "libmp3lame", "-b:a", "192k"]
            else:
                args += ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
        return [
            *args, "-map_metadata", "-1", "-map_chapters", "-1",
            "-y", str(temporary),
        ]


def commit_sequence_export(plan: SequenceExport, temporary: Path) -> None:
    plan.validated()
    temporary = Path(temporary)
    if temporary.is_symlink() or not temporary.is_file() or temporary.stat().st_size <= 0:
        raise ValueError("The media render did not produce a non-empty regular file.")
    if (temporary.parent.resolve() != plan.destination.parent.resolve()
            or temporary.suffix.lower() != plan.destination.suffix.lower()):
        raise ValueError("Invalid temporary media export path.")
    if any(not protects_source(c.source, temporary) for c in plan.sequence.clips):
        raise ValueError("Source aliased by temporary media export.")
    if plan.destination.is_symlink():
        raise ValueError("The destination changed into a symlink.")
    os.replace(temporary, plan.destination)
