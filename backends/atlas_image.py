# Backend Atlas Cloud — Text-to-Image via ERNIE Image Turbo

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable

import requests

from schemas.project import BaseAsset


ImageFn = Callable[[str, str], str | None]  # (prompt, aspect_ratio) -> image_path


def _resolve_output_dir() -> Path | None:
    try:
        from main import load_config, OUTPUT_DIR  # type: ignore

        cfg = load_config()
        out = cfg.get("output", {})
        base = out.get("base_dir") or "output"
        return Path(__file__).resolve().parent.parent / base
    except Exception:
        return None


def _download_image(url: str, dest: Path) -> str | None:
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
            return str(dest)
    except Exception:
        pass
    return None


def generate_from_prompt(prompt: str, aspect_ratio: str = "1:1") -> str | None:
    try:
        from main import load_config
        cfg = load_config()
        provider = cfg.get("providers", {}).get("atlas_image", {})
        api_key = provider.get("api_key", "")
        base_url = provider.get("base_url", "https://api.atlascloud.ai/api/v1")
        model = provider.get("model", "baidu/ERNIE-Image-Turbo/text-to-image")
    except Exception:
        api_key = ""
        base_url = "https://api.atlascloud.ai/api/v1"
        model = "baidu/ERNIE-Image-Turbo/text-to-image"

    if not api_key:
        return None

    url = "https://api.atlascloud.ai/api/v1/model/generateImage"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    size_map = {
        "1:1": "1024x1024",
        "16:9": "1280x720",
        "9:16": "720x1280",
    }
    data = {
        "model": "baidu/ERNIE-Image-Turbo/text-to-image",
        "prompt": prompt,
        "size": size_map.get(aspect_ratio, "1024x1024"),
        "n": 1,
        "seed": -1,
        "use_pe": True,
        "num_inference_steps": 8,
        "guidance_scale": 1,
        "enable_sync_mode": False,
        "enable_base64_output": False,
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        if resp.status_code != 200:
            return None
        result = resp.json()
        prediction_id = result.get("data", {}).get("id")
        if not prediction_id:
            return None

        poll_url = f"https://api.atlascloud.ai/api/v1/model/prediction/{prediction_id}"
        for _ in range(60):
            pr = requests.get(poll_url, headers=headers, timeout=60)
            if pr.status_code != 200:
                break
            pred = pr.json().get("data", {})
            status = pred.get("status", "")
            if status in ("completed", "succeeded"):
                outputs = pred.get("outputs") or []
                if outputs:
                    image_url = outputs[0]
                    out_dir = _resolve_output_dir() or Path("output")
                    dest = out_dir / "atlas_images" / f"{prediction_id}.png"
                    return _download_image(image_url, dest)
                return None
            if status == "failed":
                return None
            time.sleep(2)
    except Exception:
        pass
    return None


def generate_character_image(asset: BaseAsset, style: str, output_dir: Path) -> str | None:
    prompt = (
        f"Character portrait, full body shot. "
        f"{asset.physical}. {asset.clothing}. "
        f"Style: {style}. White background, high detail, consistent design."
    )
    return generate_from_prompt(prompt, "1:1")


def generate_location_image(asset: BaseAsset, style: str, output_dir: Path) -> str | None:
    prompt = (
        f"Location shot. {asset.prompt}. {asset.time_of_day}. "
        f"Style: {style}. Cinematic, wide shot."
    )
    return generate_from_prompt(prompt, "16:9")


def generate_shot_image(prompt: str, style: str, output_dir: Path, shot_id: str) -> str | None:
    full_prompt = f"{prompt}. Style: {style}. Cinematic frame, high detail."
    return generate_from_prompt(full_prompt, "16:9")
