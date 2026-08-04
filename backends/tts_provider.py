# Backend TTS — usa un backend configurable (Hermes / API)

from __future__ import annotations

from pathlib import Path
from typing import Callable

TtsFn = Callable[[str, str | None], str | None]  # (text, output_path) -> output_path


_tts_backend: TtsFn | None = None


def configure_tts_backend(fn: TtsFn | None) -> None:
    global _tts_backend
    _tts_backend = fn


def _get_tts_backend() -> TtsFn:
    if _tts_backend is not None:
        return _tts_backend
    raise RuntimeError(
        "Backend TTS no configurado. "
        "Llamá configure_tts_backend(...) antes de generar."
    )


def generate_dialogue_audio(
    dialogue,
    output_dir: Path,
    voice: str = "es-MX-JorgeNeural",
) -> Path | None:
    fn = _get_tts_backend()
    output = output_dir / f"dial_{dialogue.id[:8]}.mp3"
    result = fn(dialogue.text, str(output))
    if result and Path(result).exists():
        return Path(result)
    return None


def generate_scene_narration(
    scene_text: str,
    output_path: Path,
    voice: str = "es-MX-JorgeNeural",
) -> Path | None:
    fn = _get_tts_backend()
    result = fn(scene_text, str(output_path))
    if result and Path(result).exists():
        return Path(result)
    return None


def concatenate_audio_files(
    inputs: list[Path],
    output: Path,
) -> Path | None:
    try:
        import subprocess

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
                "-c",
                "copy",
                str(output),
            ],
            check=True,
        )
        list_file.unlink()
        return output
    except Exception:
        return None
