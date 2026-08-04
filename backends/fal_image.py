# Backend imágenes — usa un backend configurable (Hermes / API / Pollinations)

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from schemas.project import BaseAsset

ImageFn = Callable[[str, str], str | None]  # (prompt, aspect_ratio) -> image_path


_backend: ImageFn | None = None


def configure_image_backend(fn: ImageFn | None) -> None:
    global _backend
    _backend = fn


def _get_backend() -> ImageFn:
    if _backend is not None:
        return _backend
    raise RuntimeError(
        "Backend de imágenes no configurado. "
        "Llamá configure_image_backend(...) antes de generar."
    )


def generate_character_image(asset: BaseAsset, style: str, output_dir: Path) -> str | None:
    fn = _get_backend()
    prompt = (
        f"Character portrait, full body shot. "
        f"{asset.physical}. {asset.clothing}. "
        f"Style: {style}. White background, high detail, consistent design."
    )
    result_path = fn(prompt, "square")
    if result_path:
        dest = output_dir / f"char_{asset.name.lower()}_{asset.id[:8]}.png"
        Path(result_path).rename(dest)
        asset.image_url = str(dest)
        return str(dest)
    return None


def generate_location_image(asset: BaseAsset, style: str, output_dir: Path) -> str | None:
    fn = _get_backend()
    prompt = (
        f"Location shot. {asset.prompt}. {asset.time_of_day}. "
        f"Style: {style}. Cinematic, wide shot."
    )
    result_path = fn(prompt, "landscape")
    if result_path:
        dest = output_dir / f"loc_{asset.name.lower()}_{asset.id[:8]}.png"
        Path(result_path).rename(dest)
        asset.image_url = str(dest)
        return str(dest)
    return None


def generate_shot_image(
    prompt: str,
    style: str,
    output_dir: Path,
    shot_id: str,
) -> str | None:
    fn = _get_backend()
    full_prompt = f"{prompt}. Style: {style}. Cinematic frame, high detail."
    result_path = fn(full_prompt, "landscape")
    if result_path:
        dest = output_dir / f"shot_{shot_id[:8]}.png"
        Path(result_path).rename(dest)
        return str(dest)
    return None
