from __future__ import annotations

from urllib.parse import urlparse
from typing import Optional

import requests


def parse_cookie_header(cookie_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in cookie_header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        cookies[k.strip()] = v.strip()
    return cookies


def ranking_slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    parts = [p for p in path.split("/") if p]
    if not parts:
        raise ValueError(f"Unable to extract ranking slug from URL: {url}")
    return parts[-1]


def fetch_ranking_payload(url: str, cookie_header: Optional[str] = None, timeout: int = 30) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
    }
    cookies = parse_cookie_header(cookie_header) if cookie_header else None
    slug = ranking_slug_from_url(url)
    api_url = f"https://tv.dartconnect.com/api/rankings/{slug}"

    with requests.Session() as session:
        resp = session.post(api_url, json={}, headers=headers, cookies=cookies, timeout=timeout)

    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch rankings API ({api_url}): HTTP {resp.status_code}")

    payload = resp.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("players"), list):
        raise RuntimeError(f"Unexpected API payload from {api_url}")

    return payload


def fetch_player_events(slug: str, player_id: int, cookie_header: Optional[str] = None, timeout: int = 30) -> list[dict]:
    """Fetch per-tournament breakdown for a single player."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
    }
    cookies = parse_cookie_header(cookie_header) if cookie_header else None
    api_url = f"https://tv.dartconnect.com/api/rankings/{slug}/players/{player_id}"

    with requests.Session() as session:
        resp = session.post(api_url, json={}, headers=headers, cookies=cookies, timeout=timeout)

    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch player API ({api_url}): HTTP {resp.status_code}")

    payload = resp.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected player API payload from {api_url}")

    return payload
