# Backend Kling AI — Text-to-Image and Image-to-Image

from __future__ import annotations

import base64
import os
import time
from pathlib import Path

import requests

from .hf_image import _resolve_output_dir

KLA_API_BASE = "https://api-singapore.klingai.com"
DEFAULT_IMAGE_MODEL = "kling-v2-1"
DEFAULT_IMG2IMG_MODEL = "kling-v3"
POLL_INTERVAL = 5


def _load_image_config() -> tuple[str, str, str]:
    try:
        from main import load_config

        cfg = load_config()
        provider = cfg.get("providers", {}).get("kling_image", {})
        api_key = provider.get("api_key", "") or os.environ.get("KLING_API_KEY", "")
        text_model = provider.get("text_to_image_model", DEFAULT_IMAGE_MODEL)
        img2img_model = provider.get("image_to_image_model", DEFAULT_IMG2IMG_MODEL)
        return api_key, text_model, img2img_model
    except Exception:
        return os.environ.get("KLING_API_KEY", ""), DEFAULT_IMAGE_MODEL, DEFAULT_IMG2IMG_MODEL


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def create_image_task(prompt: str, model_name: str, aspect_ratio: str = "16:9", n: int = 1, image_url: str | None = None, image_path: str | Path | None = None) -> dict:
    api_key, _, _ = _load_image_config()
    if not api_key:
        raise RuntimeError("Missing Kling image API key")

    payload: dict = {
        "model_name": model_name,
        "prompt": prompt,
        "n": n,
        "aspect_ratio": aspect_ratio,
    }

    if image_url:
        payload["image"] = image_url
    elif image_path:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Missing reference image: {path}")
        payload["image"] = path.resolve().as_uri()

    response = requests.post(f"{KLA_API_BASE}/v1/images/generations", headers=_headers(api_key), json=payload, timeout=60)
    response.raise_for_status()
    body = response.json()
    if body.get("code") != 0:
        raise RuntimeError(f"Kling image error: {body}")
    return body.get("data", {})


def query_image_task(task_id: str, timeout: int = 300) -> dict:
    api_key, _, _ = _load_image_config()
    if not api_key:
        raise RuntimeError("Missing Kling image API key")

    url = f"{KLA_API_BASE}/v1/images/generations"
    headers = _headers(api_key)
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        response = requests.get(url, params={"pageNum": 1, "pageSize": 30}, headers=headers, timeout=30)
        response.raise_for_status()
        body = response.json()
        if body.get("code") != 0:
            raise RuntimeError(f"Kling image query error: {body}")
        data = body.get("data", [])
        for item in data:
            if item.get("task_id") == task_id:
                last = item
                status = item.get("task_status")
                if status in ("succeed", "failed"):
                    return item
        time.sleep(POLL_INTERVAL)
    if last.get("task_status") == "failed":
        return last
    raise TimeoutError(f"Kling image task {task_id} did not complete within {timeout}s")


def _download_image(url: str, dest: Path) -> Path:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest


def _extract_image_url(task: dict) -> str | None:
    task_result = task.get("task_result") or {}
    images = task_result.get("images") or []
    if images:
        first = images[0]
        if isinstance(first, dict):
            return first.get("url")
    return None


def generate_text_to_image(prompt: str, aspect_ratio: str = "16:9", output_dir: Path | None = None, dest: Path | None = None) -> str | None:
    api_key, text_model, _ = _load_image_config()
    if not api_key:
        return None

    try:
        created = create_image_task(prompt=prompt, model_name=text_model, aspect_ratio=aspect_ratio)
        task_id = created.get("task_id")
        if not task_id:
            return None
        task = query_image_task(task_id)
        image_url = _extract_image_url(task)
        if not image_url:
            return None
        out_dir = output_dir or (_resolve_output_dir() or Path("output"))
        out_dir = out_dir / "_asset_images"
        out_dir.mkdir(parents=True, exist_ok=True)
        if dest is None:
            dest = out_dir / f"{task_id}.png"
        _download_image(image_url, dest)
        return str(dest)
    except Exception:
        return None


def generate_image_to_image(prompt: str, image_path: str | Path | None = None, image_url: str | None = None, aspect_ratio: str = "16:9", output_dir: Path | None = None, dest: Path | None = None) -> str | None:
    api_key, _, img2img_model = _load_image_config()
    if not api_key:
        return None
    if not image_url and not image_path:
        return None

    try:
        created = create_image_task(prompt=prompt, model_name=img2img_model, aspect_ratio=aspect_ratio, image_url=image_url, image_path=image_path)
        task_id = created.get("task_id")
        if not task_id:
            return None
        task = query_image_task(task_id)
        image_url = _extract_image_url(task)
        if not image_url:
            return None
        out_dir = output_dir or (_resolve_output_dir() or Path("output"))
        out_dir = out_dir / "_asset_images"
        out_dir.mkdir(parents=True, exist_ok=True)
        if dest is None:
            dest = out_dir / f"{task_id}.png"
        _download_image(image_url, dest)
        return str(dest)
    except Exception:
        return None
