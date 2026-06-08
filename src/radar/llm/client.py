from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _FENCE.sub("", text).strip()


class LLMClient:
    def __init__(self, sdk: Any | None = None, model: str = "gpt-4o-mini",
                 api_key: str = "", base_url: str = ""):
        if sdk is None:
            from openai import OpenAI
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            sdk = OpenAI(**kwargs)
        self.sdk = sdk
        self.model = model

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        resp = self.sdk.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(_strip_fences(content))
