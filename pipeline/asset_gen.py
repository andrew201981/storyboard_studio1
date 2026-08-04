# Generación de assets: characters, locations, props

from __future__ import annotations

from pathlib import Path

from schemas.project import StoryboardProject, CharacterAsset, LocationAsset, PropAsset, AssetType
from backends.fal_image import generate_character_image, generate_location_image
from utils.prompt_builder import build_character_reference, build_location_reference


def generate_all_assets(
    project: StoryboardProject,
    style: str,
    output_dir: Path,
) -> dict:
    result = {"characters": 0, "locations": 0, "props": 0}

    for asset in project.assets:
        if asset.type == "character":
            path = generate_character_image(asset, style, output_dir)
            if path:
                result["characters"] += 1
        elif asset.type == "location":
            path = generate_location_image(asset, style, output_dir)
            if path:
                result["locations"] += 1
        # props se generan junto con las escenas/frames

    return result


def build_asset_prompt(asset) -> str:
    """Prompt estructurado para regenerar un asset."""
    if asset.type == "character":
        parts = [asset.name, asset.physical, asset.clothing]
        return ". ".join(p for p in parts if p)
    elif asset.type == "location":
        parts = [asset.name, asset.time_of_day, asset.prompt]
        return ". ".join(p for p in parts if p)
    elif asset.type == "prop":
        return asset.prompt or asset.name
    return asset.name
