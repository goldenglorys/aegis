from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

_BOILERPLATE_TAGS = frozenset(["nav", "footer", "header", "aside", "script", "style", "noscript"])
_FETCH_TIMEOUT = 10.0


async def fetch_url(url: str) -> str:
    """Fetch raw HTML from a URL with a 10-second timeout."""
    try:
        async with httpx.AsyncClient(
            timeout=_FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "AEGIS-Crawler/1.0"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "url_fetch_failed",
                "message": "Could not retrieve content from the provided URL.",
                "detail": f"Connection timeout after {int(_FETCH_TIMEOUT)}s",
            },
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "url_fetch_failed",
                "message": "Could not retrieve content from the provided URL.",
                "detail": f"HTTP {exc.response.status_code}",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "url_fetch_failed",
                "message": "Could not retrieve content from the provided URL.",
                "detail": str(exc),
            },
        )


def is_html(content: str) -> bool:
    return bool(BeautifulSoup(content, "html.parser").find())


def strip_boilerplate(html: str) -> str:
    """Remove nav, footer, header, aside, script, style tags from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(list(_BOILERPLATE_TAGS)):
        tag.decompose()
    return str(soup)


def extract_plain_text(content: str, content_is_html: bool) -> str:
    """Return clean plain text from HTML or pass-through plain text."""
    if not content_is_html:
        return content
    stripped = strip_boilerplate(content)
    return BeautifulSoup(stripped, "html.parser").get_text(separator=" ", strip=True)


def extract_first_paragraph(content: str, content_is_html: bool) -> str:
    """Return the first paragraph text for Direct Answer detection."""
    if content_is_html:
        soup = BeautifulSoup(content, "html.parser")
        first_p = soup.find("p")
        if first_p:
            return first_p.get_text(strip=True)
        text = soup.get_text(separator="\n", strip=True)
    else:
        text = content

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs[0] if paragraphs else text.strip()
