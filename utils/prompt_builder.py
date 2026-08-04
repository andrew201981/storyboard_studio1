# Prompt builder — arma prompts enriquecidos con assets

from __future__ import annotations

from schemas.project import StoryboardProject


def build_character_reference(asset) -> str:
    parts = [asset.name]
    if asset.physical:
        parts.append(asset.physical)
    if asset.clothing:
        parts.append(asset.clothing)
    return ", ".join(parts)


def build_location_reference(asset) -> str:
    parts = [asset.name]
    if asset.time_of_day:
        parts.append(asset.time_of_day)
    if asset.prompt:
        parts.append(asset.prompt)
    return ", ".join(parts)


def build_shot_prompt(
    project: StoryboardProject,
    shot,
    assets: list,
) -> str:
    lines: list[str] = []
    lines.append(f"Style: {project.globalStyle}")
    lines.append(f"Scene: {shot.title}")

    linked = [a for a in assets if a.id in shot.linked_asset_ids]
    chars = [a for a in linked if a.type == "character"]
    locs = [a for a in linked if a.type == "location"]
    props = [a for a in linked if a.type == "prop"]

    if chars:
        refs = ", ".join(build_character_reference(c) for c in chars)
        lines.append(f"Characters: {refs}")

    if locs:
        refs = ", ".join(build_location_reference(l) for l in locs)
        lines.append(f"Location: {refs}")

    if props:
        refs = ", ".join(f"{p.name}: {p.prompt}" for p in props)
        lines.append(f"Props: {refs}")

    if shot.prompt:
        lines.append(f"Action: {shot.prompt}")

    if shot.camera and shot.camera != "static":
        lines.append(f"Camera: {shot.camera}")

    return ". ".join(lines)


def build_transition_prompt(shot_a, shot_b, project: StoryboardProject) -> str:
    camera_a = shot_a.camera if shot_a.camera != "static" else "wide shot"
    camera_b = shot_b.camera if shot_b.camera != "static" else "wide shot"
    return (
        f"Smooth cinematic transition from '{shot_a.title}' to '{shot_b.title}'. "
        f"Style: {project.globalStyle}. "
        f"From {camera_a} into {camera_b}. "
        f"Seamless motion, natural continuity."
    )
