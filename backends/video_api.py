# Backend video — preparado para FAL video u otra API pago
# IMPORTANTE: requiere configurar la API key en config.yaml

from __future__ import annotations

import os
from pathlib import Path

import httpx

from schemas.project import StoryboardProject


def get_video_config(project: StoryboardProject) -> dict:
    """Extrae config de video desde config.yaml + project."""
    import yaml

    cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    video_cfg = cfg.get("video", {})
    provider = video_cfg.get("provider", "fal")
    api_key = video_cfg.get("api_key", "") or os.getenv("FAL_KEY", "")

    return {
        "provider": provider,
        "api_key": api_key,
        "base_url": "https://fal.run",
        "model": video_cfg.get("model", "fal-ai/wan-pro/v2.2"),
        "duration_per_clip": video_cfg.get("duration_per_clip", 4),
        "motion_strength": video_cfg.get("motion_strength", 5),
    }


def is_video_ready() -> bool:
    """True si hay key configurada."""
    cfg = get_video_config(StoryboardProject(projectTitle=""))
    return bool(cfg.get("api_key"))


def generate_transition_clip(
    image_a: Path,
    image_b: Path,
    transition_prompt: str,
    output: Path,
    cfg: dict | None = None,
) -> Path | None:
    """
    Genera un clip de transición entre dos imágenes.
    Por ahora solo funciona si hay API key de FAL configurada.
    """
    if cfg is None:
        cfg = get_video_config(StoryboardProject(projectTitle=""))

    api_key = cfg.get("api_key")
    if not api_key:
        raise RuntimeError(
            "FAL_KEY no configurada. Agregala en config.yaml o como variable de entorno."
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    # Subir imágenes a FAL temporalmente (requiere endpoint público)
    # En práctica real, usar URLs públicas o bucket.
    # Por ahora stub devuelve el path de salida para futura integración.
    raise NotImplementedError(
        "Video generation backend pendiente de integración real con FAL video API. "
        "Cuando tengas la key, completamos este módulo."
    )
