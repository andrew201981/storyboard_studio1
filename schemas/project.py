# Schemas — Modelos Pydantic del proyecto

from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ShotStatus(str, Enum):
    pending = "pending"
    image_generated = "image_generated"
    clip_generated = "clip_generated"
    scene_rendered = "scene_rendered"
    failed = "failed"


class BaseAsset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    include_in_prompt: bool = True
    image_url: str | None = None


class CharacterAsset(BaseAsset):
    type: Literal["character"] = "character"
    physical: str = ""
    clothing: str = ""
    backstory: str = ""


class LocationAsset(BaseAsset):
    type: Literal["location"] = "location"
    prompt: str = ""
    time_of_day: str = ""


class PropAsset(BaseAsset):
    type: Literal["prop"] = "prop"
    prompt: str = ""


class Shot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    shotNumber: str
    title: str
    prompt: str
    camera: str = "static"
    linked_asset_ids: list[str] = Field(default_factory=list)
    audio_description: str = ""
    transition_prompt: str = ""
    status: ShotStatus = ShotStatus.pending
    image_url: str | None = None
    clip_url: str | None = None


class StoryboardScene(BaseModel):
    sceneId: str
    sceneNumber: str
    sceneTitle: str
    shots: list[Shot] = Field(default_factory=list)


class ScriptScene(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    slugline: str
    description: str
    time_of_day: str = ""


class Dialogue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    scene_id: str
    character: str
    text: str
    emotion: str = "neutral"


class RenderConfig(BaseModel):
    output_path: str = ""
    duration: float = 0.0
    fps: int = 24
    resolution: str = "1920x1080"
    created_at: str = ""


class StoryboardProject(BaseModel):
    version: str = "1.0"
    projectTitle: str
    globalStyle: str = "Realistic"
    script: dict = Field(default_factory=lambda: {"scenes": [], "dialogues": []})
    assets: list[CharacterAsset | LocationAsset | PropAsset] = Field(
        default_factory=list
    )
    storyboard: dict = Field(
        default_factory=lambda: {"scenes": []}
    )
    render: RenderConfig | None = None
