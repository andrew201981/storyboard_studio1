# Parser de guion Markdown → scenes + dialogues
# Reconstrucción de markdown desde scenes/dialogues

from __future__ import annotations

import re
from pathlib import Path


def parse_script(markdown: str) -> dict:
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    scenes: list[dict] = []
    dialogues: list[dict] = []

    pattern = re.compile(
        r"^###\s+(INT\.|EXT\.)\s+.+$",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(markdown))
    if not matches:
        return {"scenes": [], "dialogues": []}

    for i, match in enumerate(matches):
        header = match.group(0).replace("### ", "").strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        lines = markdown[start:end].splitlines()

        description_lines: list[str] = []
        pending_char: str | None = None
        scene_id = str(len(scenes) + 1)

        for raw in lines:
            line = raw.strip()
            if not line:
                if pending_char:
                    pending_char = None
                continue
            if line.startswith("#####") or line.startswith("<!--"):
                continue

            m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", line)
            if m:
                pending_char = m.group(1).strip()
                rest = m.group(2).strip().lstrip("_").strip()
                if rest:
                    dialogues.append(
                        {
                            "id": f"{scene_id}_{len(dialogues)+1}",
                            "scene_id": scene_id,
                            "character": pending_char,
                            "text": rest,
                            "emotion": "neutral",
                        }
                    )
                continue

            if line.startswith("**") and line.endswith("**"):
                pending_char = line[2:-2].strip()
                continue

            if line.startswith("_") and line.endswith("_"):
                text = line[1:-1].strip()
                if pending_char:
                    dialogues.append(
                        {
                            "id": f"{scene_id}_{len(dialogues)+1}",
                            "scene_id": scene_id,
                            "character": pending_char,
                            "text": text,
                            "emotion": "neutral",
                        }
                    )
                else:
                    description_lines.append(text)
                continue

            if pending_char:
                dialogues.append(
                    {
                        "id": f"{scene_id}_{len(dialogues)+1}",
                        "scene_id": scene_id,
                        "character": pending_char,
                        "text": line,
                        "emotion": "neutral",
                    }
                )
                continue

            description_lines.append(line)

        time_of_day = ""
        to_match = re.search(
            r"-\s*(DÍA|NOCHE|TARDE|MADRUGADA|AMANECER|ATARDECER)",
            header,
            re.IGNORECASE,
        )
        if to_match:
            time_of_day = to_match.group(1).capitalize()

        scenes.append(
            {
                "id": scene_id,
                "slugline": header,
                "description": " ".join(description_lines),
                "time_of_day": time_of_day,
            }
        )

    return {"scenes": scenes, "dialogues": dialogues}


def rebuild_markdown(project) -> str:
    """Reconstruye markdown legible desde scenes + dialogues."""
    title = getattr(project, "projectTitle", "Proyecto")
    script = getattr(project, "script", {"scenes": [], "dialogues": []})
    scenes = script.get("scenes", [])
    dialogues = script.get("dialogues", [])

    if not scenes:
        return f"# {title}\n\n##### FADE IN:\n\n"

    parts: list[str] = [f"# {title}", "", "##### FADE IN:", ""]

    for idx, scene in enumerate(scenes):
        parts.append(f"### {scene.get('slugline', '')}")
        desc = scene.get("description", "").strip()
        if desc:
            parts.append(desc)
            parts.append("")

        scene_dialogues = [
            d for d in dialogues if d.get("scene_id") == scene.get("id")
        ]
        for d in scene_dialogues:
            char = d.get("character", "")
            text = d.get("text", "")
            emotion = d.get("emotion", "neutral")
            if char:
                if emotion and emotion != "neutral":
                    parts.append(f"**{char}**")
                    parts.append(f"_(emotion: {emotion})_")
                else:
                    parts.append(f"**{char}**")
            parts.append(text)
            parts.append("")

        if idx < len(scenes) - 1:
            parts.append("##### CUT TO:")
            parts.append("")

    parts.append("##### FADE OUT.")
    parts.append("")
    return "\n".join(parts)


def load_script(path: str | Path) -> dict:
    return parse_script(Path(path).read_text(encoding="utf-8"))
