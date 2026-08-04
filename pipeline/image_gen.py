# Generación de imágenes por shot

from __future__ import annotations

import json
from pathlib import Path

from schemas.project import StoryboardProject, ShotStatus
from utils.prompt_builder import build_shot_prompt
from backends.fal_image import generate_shot_image


def generate_all_frames(
    project: StoryboardProject,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    style = project.globalStyle

    # Mapa de assets por id
    assets_by_id = {a.id: a for a in project.assets}

    for sb_scene in project.storyboard.get("scenes", []):
        for shot in sb_scene.get("shots", []):
            if shot.get("status") == ShotStatus.image_generated:
                continue

            prompt = build_shot_prompt(
                project,
                shot,
                list(assets_by_id.values()),
            )

            path = generate_shot_image(
                prompt=prompt,
                style=style,
                output_dir=output_dir,
                shot_id=shot["id"],
            )

            if path:
                shot["image_url"] = path
                shot["status"] = ShotStatus.image_generated
            else:
                shot["status"] = ShotStatus.failed


def mark_scene_frames_from_dir(
    project: StoryboardProject,
    frames_dir: Path,
) -> None:
    """
    Marca shots como generados si hay imágenes en frames_dir
    que coincidan por shot_id.
    """
    for image_path in frames_dir.glob("shot_*.png"):
        shot_id_hint = image_path.stem.replace("shot_", "")
        for sb_scene in project.storyboard.get("scenes", []):
            for shot in sb_scene.get("shots", []):
                if shot.get("id", "").startswith(shot_id_hint) and not shot.get("image_url"):
                    shot["image_url"] = str(image_path)
                    shot["status"] = ShotStatus.image_generated
