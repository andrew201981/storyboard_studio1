# Bootstrap — configura backends y expone la app principal

from __future__ import annotations

import os
from pathlib import Path

import yaml

from schemas.project import StoryboardProject


def load_project(path: str | Path) -> StoryboardProject:
    from schemas.validator import load_project
    return load_project(path)


def save_project(project: StoryboardProject, path: str | Path) -> None:
    from schemas.validator import save_project
    save_project(project, path)


def load_config() -> dict:
    cfg_path = Path(__file__).resolve().parent / "config.yaml"
    if not cfg_path.exists():
        return {}
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def configure_backends(project: StoryboardProject) -> None:
    """Configura backends para texto, imagen, audio según disponibilidad."""
    cfg = load_config()

    # TTS backend: Edge/OpenAI via Hermes
    try:
        from text_to_speech import text_to_speech  # type: ignore

        def tts_fn(text: str, output_path: str | None) -> str | None:
            result = text_to_speech(text=text, output_path=output_path or "")
            if isinstance(result, dict):
                return result.get("output_path") or result.get("audio") or output_path
            if isinstance(result, str):
                return result
            return output_path

        from backends.tts_provider import configure_tts_backend
        configure_tts_backend(tts_fn)
    except Exception:
        pass

    # Image backend: FAL.ai / Pollinations via Hermes
    try:
        from image_generate import image_generate  # type: ignore

        def img_fn(prompt: str, aspect_ratio: str) -> str | None:
            result = image_generate(prompt=prompt, aspect_ratio=aspect_ratio)
            if isinstance(result, dict):
                return result.get("image")
            return None

        from backends.fal_image import configure_image_backend
        configure_image_backend(img_fn)
    except Exception:
        pass
