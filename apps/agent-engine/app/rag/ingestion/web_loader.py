"""Fetch a URL and reduce it to readable plain text (Flow A).

Read-only: a plain HTTP GET + HTML-to-text. No JavaScript execution and no
browser — that's Flow B (Playwright). For static/article pages this is enough
and is far cheaper and faster than driving Chromium.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from app.config.settings import settings

_WHITESPACE = re.compile(r"\n\s*\n\s*\n+")


@dataclass
class FetchedPage:
    url: str
    title: str
    text: str
    truncated: bool


class FetchError(Exception):
    """Raised when a URL cannot be fetched (network, status, content-type)."""


async def fetch_page(url: str) -> FetchedPage:
    headers = {"User-Agent": settings.FETCH_USER_AGENT}
    try:
        async with httpx.AsyncClient(
            timeout=settings.FETCH_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise FetchError(
            f"Site returned HTTP {exc.response.status_code} for {url}"
        ) from exc
    except httpx.HTTPError as exc:
        raise FetchError(f"Could not reach {url}: {exc}") from exc

    content_type = resp.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        raise FetchError(f"Unsupported content-type '{content_type}' for {url}")

    title, text = _extract_readable(resp.text)
    truncated = len(text) > settings.FETCH_MAX_CHARS
    if truncated:
        text = text[: settings.FETCH_MAX_CHARS]

    return FetchedPage(url=str(resp.url), title=title, text=text, truncated=truncated)


def _extract_readable(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")

    # Drop non-content nodes.
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()

    title = (soup.title.string or "").strip() if soup.title else ""

    body = soup.body or soup
    text = body.get_text(separator="\n")
    # Collapse runs of blank lines and trailing spaces.
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    text = _WHITESPACE.sub("\n\n", text)
    return title, text
