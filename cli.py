# CLI principal — Storyboard Studio V1

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml

from schemas.project import StoryboardProject, ShotStatus
from schemas.validator import load_project, save_project, validate_dict
from pipeline.script_parser import parse_script, load_script
from utils.ids import short_id


def load_config() -> dict:
    cfg_path = Path("config.yaml")
    if not cfg_path.exists():
        return {}
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def ensure_output_dirs(project_id: str, base: Path) -> dict:
    out = base / project_id
    dirs = {
        "assets": out / "assets",
        "frames": out / "frames",
        "clips": out / "clips",
        "scenes": out / "scenes",
        "audio": out / "audio",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


@click.group()
def cli() -> None:
    """Storyboard Studio V1 — CLI"""
    pass


@cli.command()
@click.argument("guion", type=click.Path(exists=True))
@click.option("--output", "-o", default="project.json", help="Archivo JSON de salida")
def init(guion: str, output: str) -> None:
    """Inicializa proyecto desde guion Markdown."""
    script_data = load_script(guion)
    cfg = load_config()

    title = Path(guion).stem
    project = StoryboardProject(
        projectTitle=title,
        globalStyle=cfg.get("project", {}).get("default_style", "Realistic"),
        script=script_data,
    )

    save_project(project, output)
    click.echo(f"✅ Proyecto creado: {output}")
    click.echo(f"   Escenas: {len(script_data['scenes'])}")
    click.echo(f"   Diálogos: {len(script_data['dialogues'])}")


@cli.command()
@click.argument("project", type=click.Path(exists=True))
@click.option("--style", "-s", default=None, help="Override estilo visual")
def generate_assets(project: str, style: str | None) -> None:
    """Genera assets (personajes, locaciones, props) desde el proyecto."""
    from pipeline.asset_gen import generate_all_assets

    proj = load_project(project)
    style = style or proj.globalStyle
    cfg = load_config()
    out = Path(cfg.get("output", {}).get("base_dir", "output"))
    dirs = ensure_output_dirs(short_id(), out)

    result = generate_all_assets(proj, style, dirs["assets"])
    save_project(proj, project)

    click.echo(f"✅ Assets generados: {result['characters']} chars, {result['locations']} locs, {result['props']} props")


@cli.command()
@click.argument("project", type=click.Path(exists=True))
def generate_frames(project: str) -> None:
    """Genera imágenes por shot."""
    from pipeline.image_gen import generate_all_frames

    proj = load_project(project)
    cfg = load_config()
    out = Path(cfg.get("output", {}).get("base_dir", "output"))
    dirs = ensure_output_dirs(short_id(), out)

    generate_all_frames(proj, dirs["frames"])
    save_project(proj, project)
    click.echo("✅ Frames generados")


@cli.command()
@click.argument("project", type=click.Path(exists=True))
def generate_audio(project: str) -> None:
    """Genera narración TTS por escena."""
    from pipeline.tts_gen import generate_scene_audio

    proj = load_project(project)
    cfg = load_config()
    out = Path(cfg.get("output", {}).get("base_dir", "output"))
    dirs = ensure_output_dirs(short_id(), out)
    voice = cfg.get("tts", {}).get("voice", "es-MX-JorgeNeural")

    generate_scene_audio(proj, dirs["audio"], voice=voice)
    save_project(proj, project)
    click.echo("✅ Audio generado")


@cli.command()
@click.argument("project", type=click.Path(exists=True))
def render_video(project: str) -> None:
    """Genera video final (requiere video API configurada)."""
    from pipeline.scene_render import render_all_scenes
    from pipeline.final_mux import mux_final

    proj = load_project(project)
    cfg = load_config()
    out = Path(cfg.get("output", {}).get("base_dir", "output"))
    dirs = ensure_output_dirs(short_id(), out)

    if not dirs["clips"].exists() or not any(dirs["clips"].iterdir()):
        click.echo("⚠️  Sin clips de transición. Ejecuta 'transitions' primero.")
        sys.exit(1)

    scene_videos = render_all_scenes(proj, dirs["clips"], dirs["scenes"])
    final_path = dirs["scenes"].parent / "final.mp4"

    audio_path = dirs["audio"] / "scene_01_narration.mp3"
    mux_final(scene_videos, audio_path, final_path)

    proj.render = {
        "output_path": str(final_path),
        "fps": cfg.get("project", {}).get("fps", 24),
        "resolution": cfg.get("project", {}).get("resolution", "1920x1080"),
    }
    save_project(proj, project)
    click.echo(f"✅ Video final: {final_path}")


@cli.command()
@click.argument("project", type=click.Path(exists=True))
def transitions(project: str) -> None:
    """Genera clips de transición (requiere video API key)."""
    from pipeline.transition_gen import generate_all_transitions

    proj = load_project(project)
    cfg = load_config()
    out = Path(cfg.get("output", {}).get("base_dir", "output"))
    dirs = ensure_output_dirs(short_id(), out)

    try:
        generate_all_transitions(proj, dirs["frames"], dirs["clips"])
        save_project(proj, project)
        click.echo("✅ Transiciones generadas")
    except RuntimeError as exc:
        click.echo(f"❌ {exc}")
        sys.exit(1)


@cli.command()
@click.argument("project", type=click.Path(exists=True))
def status(project: str) -> None:
    """Muestra estado del proyecto."""
    proj = load_project(project)

    click.echo(f"🎬 {proj.projectTitle}")
    click.echo(f"   Estilo: {proj.globalStyle}")
    click.echo(f"   Escenas: {len(proj.script.get('scenes', []))}")
    click.echo(f"   Diálogos: {len(proj.script.get('dialogues', []))}")
    click.echo(f"   Assets: {len(proj.assets)}")

    total_shots = sum(
        len(s.get("shots", [])) for s in proj.storyboard.get("scenes", [])
    )
    generated = sum(
        1
        for s in proj.storyboard.get("scenes", [])
        for shot in s.get("shots", [])
        if shot.get("status") in ("image_generated", "clip_generated", "scene_rendered")
    )
    click.echo(f"   Shots: {total_shots} total, {generated} generados")

    if proj.render:
        click.echo(f"   Render: {proj.render.output_path}")


if __name__ == "__main__":
    cli()
