# Final mux — une video escenas + audio → final.mp4

from __future__ import annotations

from pathlib import Path

from utils.ffmpeg import concat_videos, mux_audio_video


def mux_final(
    scene_videos: list[Path],
    audio_path: Path | None,
    output: Path,
) -> Path:
    """Concatena videos de escena y agrega audio."""
    if not scene_videos:
        raise RuntimeError("No hay videos de escena para ensamblar.")

    output.parent.mkdir(parents=True, exist_ok=True)

    # 1. Concatenar todas las escenas
    video_only = output.with_name(output.stem + "_noaudio.mp4")
    concat_videos(inputs=scene_videos, output=video_only)

    # 2. Agregar audio si existe
    mux_audio_video(video=video_only, audio=audio_path, output=output)

    # Limpiar intermedio
    try:
        video_only.unlink()
    except OSError:
        pass

    return output
