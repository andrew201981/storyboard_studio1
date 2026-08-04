# Scene render — concatena clips de transición en video por escena

from __future__ import annotations

import os
from pathlib import Path

import click

from schemas.project import StoryboardProject, ShotStatus
from utils.ffmpeg import image_to_video, concat_videos


def render_scene(
    project: StoryboardProject,
    scene_data: dict,
    clips_dir: Path,
    scenes_dir: Path,
    default_duration: float = 4.0,
) -> Path | None:
    """Renderiza una escena completa."""
    scene_number = scene_data.get("sceneNumber", "01")
    output = scenes_dir / f"scene_{scene_number}_raw.mp4"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    shots = scene_data.get("shots", [])
    if not shots:
        return None

    temp_videos: list[Path] = []

    for idx, shot in enumerate(shots):
        img_url = shot.get("image_url")
        clip_url = shot.get("clip_url")

        if clip_url and os.path.exists(clip_url):
            temp_videos.append(Path(clip_url))
        elif img_url and os.path.exists(img_url):
            # Sin clip, imagen estática por N segundos
            duration = default_duration
            if shot.get("camera") and shot["camera"] != "static":
                duration = default_duration * 1.5
            temp_path = scenes_dir / f"temp_shot_{shot['id'][:8]}.mp4"
            image_to_video(Path(img_url), temp_path, duration=duration)
            temp_videos.append(temp_path)
        else:
            click.echo(f"⚠️  Shot sin imagen: {shot.get('title')}")
            continue

    if not temp_videos:
        return None

    try:
        concat_videos(
            inputs=temp_videos,
            output=output,
            fps=project.render.fps if project.render else 24,
            resolution=project.render.resolution if project.render else "1920x1080",
        )
        return output
    except Exception as exc:
        click.echo(f"❌ Error renderizando escena {scene_number}: {exc}")
        return None
    finally:
        # Limpiar temps
        for v in temp_videos:
            if v.exists() and "_raw" not in v.name:
                try:
                    v.unlink()
                except OSError:
                    pass


def render_all_scenes(
    project: StoryboardProject,
    clips_dir: Path,
    scenes_dir: Path,
) -> list[Path]:
    results = []
    for sb_scene in project.storyboard.get("scenes", []):
        path = render_scene(project, sb_scene, clips_dir, scenes_dir)
        if path:
            results.append(path)
            sb_scene["_rendered_path"] = str(path)
    return results
