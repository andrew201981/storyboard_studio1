# Backend Hugging Face — Text-to-Image via Inference API

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from huggingface_hub import InferenceClient  # type: ignore
from PIL import Image


def _resolve_output_dir() -> Path | None:
    try:
        from main import load_config  # type: ignore

        cfg = load_config()
        out = cfg.get("output", {})
        base = out.get("base_dir") or "output"
        return Path(__file__).resolve().parent.parent / base
    except Exception:
        return None


def generate_from_prompt(prompt: str, aspect_ratio: str = "1:1", output_dir: Path | None = None, dest: Path | None = None) -> str | None:
    try:
        from main import load_config

        cfg = load_config()
        provider = cfg.get("providers", {}).get("hf_image", {})
        api_key = provider.get("api_key", "") or os.environ.get("HF_API_KEY", "")
        model = provider.get("model", "black-forest-labs/FLUX.1-schnell")
    except Exception:
        api_key = os.environ.get("HF_API_KEY", "")
        model = "black-forest-labs/FLUX.1-schnell"

    if not api_key:
        return None

    try:
        client = InferenceClient(api_key=api_key)
        image = client.text_to_image(prompt, model=model)

        # Crop to 16:9 without distortion
        if image.size != (1280, 720):
            img_w, img_h = image.size
            target_ratio = 16 / 9
            current_ratio = img_w / img_h

            if current_ratio > target_ratio:
                # Too wide - crop sides
                new_w = int(img_h * target_ratio)
                left = (img_w - new_w) // 2
                image = image.crop((left, 0, left + new_w, img_h))
            elif current_ratio < target_ratio:
                # Too tall - crop top/bottom
                new_h = int(img_w / target_ratio)
                top = (img_h - new_h) // 2
                image = image.crop((0, top, img_w, top + new_h))

            # Resize to target 16:9 resolution
            image = image.resize((1280, 720), Image.Resampling.LANCZOS)

        out_dir = output_dir or (_resolve_output_dir() or Path("output"))
        out_dir = out_dir / "_asset_images"
        out_dir.mkdir(parents=True, exist_ok=True)
        if dest is None:
            dest = out_dir / f"{hash(prompt)}_{hash(model)}.png"
        image.save(dest)
        return str(dest)
    except Exception:
        return None
