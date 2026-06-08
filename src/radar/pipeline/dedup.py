from __future__ import annotations

from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip().lower())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def same_event(url_a: str, url_b: str, title_a: str, title_b: str,
               threshold: float) -> bool:
    if normalize_url(url_a) == normalize_url(url_b):
        return True
    return title_similarity(title_a, title_b) >= threshold
