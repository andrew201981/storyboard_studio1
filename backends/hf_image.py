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
        api_key = _clean_api_key(provider.get("api_key", "") or os.environ.get("HF_API_KEY", ""))
        model = provider.get("model", "black-forest-labs/FLUX.1-schnell")
    except Exception:
        api_key = _clean_api_key(os.environ.get("HF_API_KEY", ""))
        model = "black-forest-labs/FLUX.1-schnell"

    if not api_key:
        return None

    safe_prompt = _safe_prompt(prompt)
    try:
        client = InferenceClient(api_key=api_key)
        if aspect_ratio == "16:9":
            image = client.text_to_image(safe_prompt, model=model, width=1280, height=720)
        else:
            image = client.text_to_image(safe_prompt, model=model)

        out_dir = output_dir or (_resolve_output_dir() or Path("output"))
        out_dir = out_dir / "_asset_images"
        out_dir.mkdir(parents=True, exist_ok=True)
        if dest is None:
            dest = out_dir / f"{hash(safe_prompt)}_{hash(model)}.png"
        image.save(dest)
        return str(dest)
    except Exception as exc:
        print(f"[hf_image] generation failed: {exc}")
        return None


def _clean_api_key(value: str) -> str:
    try:
        return value.encode("ascii", "ignore").decode("ascii", "ignore").strip()
    except Exception:
        return value.strip()



def _safe_prompt(prompt: str) -> str:
    try:
        return prompt.encode("ascii", "ignore").decode("ascii", "ignore")
    except Exception:
        return prompt
