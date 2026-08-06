# Backend KIE AI — Image-to-Image via grok-imagine

from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from .hf_image import _resolve_output_dir

KIE_API_BASE = "https://api.kie.ai/api/v1/jobs"
DEFAULT_MODEL = "grok-imagine/image-to-image"
DEFAULT_TIMEOUT = 180
POLL_INTERVAL = 5


def _load_api_key() -> str:
    try:
        from main import load_config

        cfg = load_config()
        provider = cfg.get("providers", {}).get("kie_image", {})
        key = provider.get("api_key", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("KIE_API_KEY", "")


def _load_model() -> str:
    try:
        from main import load_config

        cfg = load_config()
        provider = cfg.get("providers", {}).get("kie_image", {})
        model = provider.get("model")
        if model:
            return model
    except Exception:
        pass
    return DEFAULT_MODEL


def _wait_for_task(task_id: str, api_key: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    url = f"{KIE_API_BASE}/recordInfo"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(url, params={"taskId": task_id}, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 200:
            raise RuntimeError(f"KIE API error: {payload}")
        data = payload.get("data", {})
        state = data.get("state")
        if state in ("success", "failed", "complete"):
            return data
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"KIE task {task_id} did not complete within {timeout}s")


def _download_image(url: str, dest: Path) -> Path:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest


def generate_from_image(
    prompt: str,
    image_path: str | Path | None = None,
    image_url: str | None = None,
    output_dir: Path | None = None,
    dest: Path | None = None,
) -> str | None:
    api_key = _load_api_key()
    if not api_key:
        return None

    source_url = image_url
    if not source_url and image_path:
        source_url = Path(image_path).resolve().as_uri()

    if not source_url:
        return None

    model = _load_model()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "callBackUrl": "",
        "input": {
            "prompt": prompt,
            "image_urls": [source_url],
        },
    }

    try:
        response = requests.post(f"{KIE_API_BASE}/createTask", headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 200:
            return None
        task_id = payload.get("data", {}).get("taskId")
        if not task_id:
            return None

        record = _wait_for_task(task_id, api_key)
        result_json = record.get("resultJson")
        if not result_json:
            return None
        result_url = _extract_result_url(result_json)
        if not result_url:
            return None

        out_dir = output_dir or (_resolve_output_dir() or Path("output"))
        out_dir = out_dir / "_asset_images"
        out_dir.mkdir(parents=True, exist_ok=True)
        if dest is None:
            dest = out_dir / f"{task_id}.png"
        _download_image(result_url, dest)
        return str(dest)
    except Exception:
        return None


def _extract_result_url(result_json: str) -> str | None:
    try:
        import json

        data = json.loads(result_json)
        if isinstance(data, dict):
            url = data.get("url") or data.get("image_url") or data.get("result")
            if url:
                return str(url)
            outputs = data.get("outputs") or data.get("images") or []
            if isinstance(outputs, list) and outputs:
                first = outputs[0]
                if isinstance(first, dict):
                    return first.get("url") or first.get("image_url")
                return str(first)
        elif isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                return first.get("url") or first.get("image_url")
            return str(first)
    except Exception:
        pass
    return None
