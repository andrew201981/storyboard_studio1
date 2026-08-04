# TTS — narración por escena

from __future__ import annotations

import os
from pathlib import Path

from schemas.project import StoryboardProject, Dialogue
from backends.tts_provider import (
    generate_dialogue_audio,
    generate_scene_narration,
    concatenate_audio_files,
)


def generate_scene_audio(
    project: StoryboardProject,
    audio_dir: Path,
    voice: str = "es-MX-JorgeNeural",
) -> None:
    audio_dir.mkdir(parents=True, exist_ok=True)

    scenes = project.script.get("scenes", [])
    dialogues = project.script.get("dialogues", [])

    for scene in scenes:
        scene_id = scene["id"]
        scene_dialogues = [d for d in dialogues if d["scene_id"] == scene_id]

        if not scene_dialogues:
            continue

        scene_number = scene.get("id", "01")
        output = audio_dir / f"scene_{scene_number}_narration.mp3"

        # Generar audio por diálogo y concatenar
        dialogue_audios: list[Path] = []
        for d in scene_dialogues:
            dialogue = Dialogue(**d)
            audio_path = generate_dialogue_audio(dialogue, audio_dir, voice=voice)
            if audio_path:
                dialogue_audios.append(audio_path)

        if not dialogue_audios:
            continue

        if len(dialogue_audios) == 1:
            dialogue_audios[0].rename(output)
        else:
            concatenate_audio_files(dialogue_audios, output)

        # Limpiar audios individuales
        for p in dialogue_audios:
            try:
                p.unlink()
            except OSError:
                pass
