# Transiciones — img_i → img_i+1 video clips

from __future__ import annotations

import click
import os
from pathlib import Path

from schemas.project import StoryboardProject, ShotStatus
from backends.video_api import generate_transition_clip, is_video_ready, get_video_config


def generate_all_transitions(
    project: StoryboardProject,
    frames_dir: Path,
    clips_dir: Path,
) -> None:
    if not is_video_ready():
        raise RuntimeError(
            "Video API no configurada. "
            "Agrega FAL_KEY en config.yaml o como variable de entorno."
        )

    clips_dir.mkdir(parents=True, exist_ok=True)
    cfg = get_video_config(project)

    for sb_scene in project.storyboard.get("scenes", []):
        shots = sb_scene.get("shots", [])
        for idx in range(len(shots) - 1):
            shot_a = shots[idx]
            shot_b = shots[idx + 1]

            img_a = shot_a.get("image_url")
            img_b = shot_b.get("image_url")

            if not img_a or not img_b:
                continue
            if not os.path.exists(img_a) or not os.path.exists(img_b):
                continue

            transition_prompt = shot_b.get(
                "transition_prompt"
            ) or f"Smooth transition from shot {shot_a['shotNumber']} to {shot_b['shotNumber']}"

            output = clips_dir / f"trans_{shot_a['id'][:8]}_{shot_b['id'][:8]}.mp4"

            if output.exists():
                shot_a["clip_url"] = str(output)
                continue

            try:
                path = generate_transition_clip(
                    image_a=Path(img_a),
                    image_b=Path(img_b),
                    transition_prompt=transition_prompt,
                    output=output,
                    cfg=cfg,
                )
                if path:
                    shot_a["clip_url"] = str(path)
                    shot_a["status"] = ShotStatus.clip_generated
            except NotImplementedError:
                click.echo(
                    f"⚠️  Transición pendiente de API key: {shot_a['title']} → {shot_b['title']}"
                )
                break
            except Exception as exc:
                click.echo(f"❌ Error en transición: {exc}")


def mark_scene_clips_from_dir(
    project: StoryboardProject,
    clips_dir: Path,
) -> None:
    """Marca clips como generados si existen en disco."""
    for clip_path in clips_dir.glob("trans_*.mp4"):
        hint = clip_path.stem.replace("trans_", "").split("_")[0]
        for sb_scene in project.storyboard.get("scenes", []):
            for shot in sb_scene.get("shots", []):
                if shot.get("id", "").startswith(hint) and not shot.get("clip_url"):
                    shot["clip_url"] = str(clip_path)
                    shot["status"] = ShotStatus.clip_generated
