from __future__ import annotations

from typing import Any

import httpx

MAX_FEISHU_TEXT = 18000


def send_feishu(webhook_url: str, markdown: str,
                client: Any | None = None) -> None:
    text = markdown if len(markdown) <= MAX_FEISHU_TEXT else (
        markdown[:MAX_FEISHU_TEXT] + "\n\n...(内容过长已截断)"
    )
    http = client or httpx.Client(timeout=20)
    resp = http.post(
        webhook_url,
        json={"msg_type": "text", "content": {"text": text}},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", 0) != 0:
        raise RuntimeError(f"feishu webhook failed: {data}")
