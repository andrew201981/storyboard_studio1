# IDs cortos y consistentes

from __future__ import annotations

import uuid


def short_id() -> str:
    return uuid.uuid4().hex[:8]


def scene_id() -> str:
    return str(uuid.uuid4())


def asset_id() -> str:
    return str(uuid.uuid4())
