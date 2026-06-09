from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit

from radar.models import TechItem


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip().lower())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def canonical_entity(title: str, url: str = "") -> str | None:
    """Normalize repo/model slug for cross-source matching."""
    t = title.strip().lower()
    if "/" in t and " " not in t and len(t) < 120:
        slug = re.sub(r"[^a-z0-9/._-]", "", t)
        return slug or None
    url_l = url.lower()
    for prefix in ("huggingface.co/", "github.com/"):
        if prefix in url_l:
            slug = url_l.split(prefix, 1)[-1].strip("/").split("?")[0]
            if "/" in slug:
                return slug
    return None


def _entity_cross_match(entity: str | None, title: str, desc: str) -> bool:
    if not entity:
        return False
    slug = entity.split("/")[-1]
    if len(slug) < 6:
        return False
    text = f"{title} {desc}".lower().replace("_", "-")
    normalized = slug.replace("_", "-")
    if normalized in text:
        return True
    parts = re.split(r"[-_.]+", slug)
    if len(parts) >= 2:
        key = "-".join(parts[:2])
        if len(key) >= 6 and key in text:
            return True
    return False


def same_event(url_a: str, url_b: str, title_a: str, title_b: str,
               threshold: float, desc_a: str = "", desc_b: str = "") -> bool:
    if normalize_url(url_a) == normalize_url(url_b):
        return True
    if title_similarity(title_a, title_b) >= threshold:
        return True
    ent_a = canonical_entity(title_a, url_a)
    ent_b = canonical_entity(title_b, url_b)
    if ent_a and ent_b and ent_a == ent_b:
        return True
    if _entity_cross_match(ent_a, title_b, desc_b):
        return True
    if _entity_cross_match(ent_b, title_a, desc_a):
        return True
    return False


def same_item_event(a: TechItem, b: TechItem, threshold: float) -> bool:
    return same_event(
        a.url, b.url, a.title, b.title, threshold,
        desc_a=a.description, desc_b=b.description,
    )
