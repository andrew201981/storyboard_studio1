# Wrappers de ffmpeg — composición y concatenación

from __future__ import annotations

import subprocess
from pathlib import Path


def check_ffmpeg() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def concat_videos(
    inputs: list[Path],
    output: Path,
    fps: int = 24,
    resolution: str = "1920x1080",
) -> None:
    """Concatena videos con mismo formato usando concat demuxer."""
    output.parent.mkdir(parents=True, exist_ok=True)
    list_file = output.with_suffix(".txt")
    list_file.write_text(
        "\n".join(f"file '{p.absolute()}'" for p in inputs),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-vf",
            f"fps={fps},scale={resolution}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        check=True,
    )
    list_file.unlink()


def image_to_video(
    image: Path,
    output: Path,
    duration: float = 4.0,
    fps: int = 24,
    resolution: str = "1920x1080",
) -> None:
    """Convierte una imagen estática en video de N segundos."""
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image),
            "-vf",
            f"fps={fps},scale={resolution},format=yuv420p",
            "-c:v",
            "libx264",
            "-t",
            str(duration),
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        check=True,
    )


def add_audio_to_video(
    video: Path,
    audio: Path,
    output: Path,
) -> None:
    """Reemplaza / agrega audio al video."""
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        ],
        check=True,
    )


def mux_audio_video(
    video: Path,
    audio: Path | None,
    output: Path,
) -> None:
    """Mux final: si no hay audio, copia el video solo."""
    if audio is None or not audio.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", str(video), str(output)], check=True)
        return
    add_audio_to_video(video, audio, output)
