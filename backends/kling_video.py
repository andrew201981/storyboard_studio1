# Backend Kling AI — Text-to-Video and Image-to-Video

from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from .kling_image import _load_image_config, _headers, KLA_API_BASE

DEFAULT_VIDEO_MODEL = "kling-video-o1"
DEFAULT_RESOLUTION = "720p"
DEFAULT_DURATION = 5
POLL_INTERVAL = 5


def _load_video_config() -> tuple[str, str]:
    try:
        from main import load_config

        cfg = load_config()
        provider = cfg.get("providers", {}).get("kling_video", {})
        api_key = provider.get("api_key", "") or os.environ.get("KLING_API_KEY", "")
        model = provider.get("model", DEFAULT_VIDEO_MODEL)
        return api_key, model
    except Exception:
        return os.environ.get("KLING_API_KEY", ""), DEFAULT_VIDEO_MODEL


def _resolve_output_dir() -> Path | None:
    try:
        from main import load_config  # type: ignore

        cfg = load_config()
        out = cfg.get("output", {})
        base = out.get("base_dir") or "output"
        return Path(__file__).resolve().parent.parent / base
    except Exception:
        return None


def create_video_task(prompt: str, model: str, *, image_url: str | None = None, duration: int = DEFAULT_DURATION, aspect_ratio: str = "16:9", multi_shot: bool = True, external_task_id: str = "") -> dict:
    api_key, _ = _load_video_config()
    if not api_key:
        raise RuntimeError("Missing Kling video API key")

    contents = [{"type": "prompt", "text": prompt}]
    if image_url:
        contents.append({"type": "first_frame", "url": image_url})

    payload = {
        "contents": contents,
        "settings": {
            "resolution": DEFAULT_RESOLUTION,
            "duration": duration,
            "audio": "off",
            "multi_shot": multi_shot,
            "aspect_ratio": aspect_ratio,
        },
        "options": {
            "callback_url": "",
            "external_task_id": external_task_id,
            "watermark_info": {"enabled": False},
        },
    }

    endpoint = "/image-to-video/kling-3.0" if image_url else "/text-to-video/kling-3.0"
    response = requests.post(f"{KLA_API_BASE}{endpoint}", headers=_headers(api_key), json=payload, timeout=60)
    response.raise_for_status()
    body = response.json()
    if body.get("code") != 0:
        raise RuntimeError(f"Kling video error: {body}")
    return body.get("data", {})


def query_video_task(task_id: str, timeout: int = 600) -> dict:
    api_key, _ = _load_video_config()
    if not api_key:
        raise RuntimeError("Missing Kling video API key")

    url = f"{KLA_API_BASE}/tasks"
    headers = _headers(api_key)
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        response = requests.get(url, params={"task_ids": task_id}, headers=headers, timeout=30)
        response.raise_for_status()
        body = response.json()
        if body.get("code") != 0:
            raise RuntimeError(f"Kling video query error: {body}")
        data = body.get("data", [])
        for item in data:
            if item.get("id") == task_id:
                last = item
                status = item.get("status")
                if status in ("succeeded", "failed"):
                    return item
        time.sleep(POLL_INTERVAL)
    if last.get("status") == "failed":
        return last
    raise TimeoutError(f"Kling video task {task_id} did not complete within {timeout}s")


def _download_video(url: str, dest: Path) -> Path:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest


def generate_text_to_video(prompt: str, output_dir: Path | None = None, dest: Path | None = None, duration: int = DEFAULT_DURATION, aspect_ratio: str = "16:9") -> str | None:
    api_key, model = _load_video_config()
    if not api_key:
        return None

    try:
        created = create_video_task(prompt=prompt, model=model, duration=duration, aspect_ratio=aspect_ratio)
        task_id = created.get("id")
        if not task_id:
            return None
        task = query_video_task(task_id)
        video_url = _extract_video_url(task)
        if not video_url:
            return None
        out_dir = output_dir or (_resolve_output_dir() or Path("output"))
        out_dir = out_dir / "clips"
        out_dir.mkdir(parents=True, exist_ok=True)
        if dest is None:
            dest = out_dir / f"{task_id}.mp4"
        _download_video(video_url, dest)
        return str(dest)
    except Exception:
        return None


def generate_image_to_video(prompt: str, image_url: str | None = None, image_path: str | Path | None = None, output_dir: Path | None = None, dest: Path | None = None, duration: int = DEFAULT_DURATION, aspect_ratio: str = "16:9") -> str | None:
    api_key, model = _load_video_config()
    if not api_key:
        return None

    source_url = image_url
    if not source_url and image_path:
        source_url = str(Path(image_path).resolve().as_uri())

    if not source_url:
        return None

    try:
        created = create_video_task(prompt=prompt, model=model, image_url=source_url, duration=duration, aspect_ratio=aspect_ratio)
        task_id = created.get("id")
        if not task_id:
            return None
        task = query_video_task(task_id)
        video_url = _extract_video_url(task)
        if not video_url:
            return None
        out_dir = output_dir or (_resolve_output_dir() or Path("output"))
        out_dir = out_dir / "clips"
        out_dir.mkdir(parents=True, exist_ok=True)
        if dest is None:
            dest = out_dir / f"{task_id}.mp4"
        _download_video(video_url, dest)
        return str(dest)
    except Exception:
        return None


def _extract_video_url(task: dict) -> str | None:
    task_result = task.get("task_result") or {}
    videos = task_result.get("videos") or []
    if videos:
        first = videos[0]
        if isinstance(first, dict):
            return first.get("url") or first.get("video_url")
    return None
