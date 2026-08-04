# Validación de JSON contra schema y Pydantic

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from schemas.project import StoryboardProject


def load_project(path: str | Path) -> StoryboardProject:
    text = Path(path).read_text(encoding="utf-8")
    data = json.loads(text)
    return StoryboardProject.model_validate(data)


def validate_dict(data: dict) -> StoryboardProject:
    try:
        return StoryboardProject.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Proyecto inválido: {exc}") from exc


def save_project(project: StoryboardProject, path: str | Path) -> None:
    Path(path).write_text(
        project.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
