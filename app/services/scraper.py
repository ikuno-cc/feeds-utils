"""
scraper.py – Intelligent web scraping service.

Strategy:
  1. Fetch HTML using playwright-stealth (if available) → curl_cffi → httpx fallback
  2. Parse the HTML with BeautifulSoup, extracting metadata from:
       - JSON-LD structured data
       - Open Graph / Twitter Card meta tags
       - Standard <meta> tags (author, description, keywords, etc.)
       - <article> / main body content
  3. Map extracted fields to the caller-supplied JSON Schema fields using
     field name + description heuristics. No external LLM required.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, Tag

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    from playwright.async_api import async_playwright
    from playwright_stealth.stealth import Stealth
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def _fetch_playwright(url: str) -> Optional[str]:
    """Fetch page HTML using Playwright with stealth context."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent=_DEFAULT_HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        try:
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
        except Exception:
            pass
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            await page.wait_for_timeout(2000)  # let JS settle
            html = await page.content()
            return html
        except Exception as exc:
            logger.warning(f"Playwright fetch failed for {url}: {exc}")
            return None
        finally:
            await browser.close()


async def _fetch_curl_cffi(url: str) -> Optional[str]:
    """Fetch page HTML using curl_cffi with Chrome TLS fingerprint."""
    def _sync():
        resp = cffi_requests.get(
            url,
            impersonate="chrome124",
            headers=_DEFAULT_HEADERS,
            allow_redirects=True,
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.text
        return None

    return await asyncio.to_thread(_sync)


async def _fetch_httpx(url: str) -> Optional[str]:
    """Plain httpx fallback."""
    async with httpx.AsyncClient(
        headers=_DEFAULT_HEADERS,
        follow_redirects=True,
        timeout=15.0,
    ) as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            return resp.text
    return None


async def fetch_html(url: str) -> Optional[str]:
    """Try playwright → curl_cffi → httpx to get page HTML."""
    # 1. Playwright (best anti-bot)
    if HAS_PLAYWRIGHT:
        try:
            html = await _fetch_playwright(url)
            if html:
                logger.info("Fetched via Playwright")
                return html
        except Exception as exc:
            logger.warning(f"Playwright error: {exc}")

    # 2. curl_cffi (TLS fingerprint)
    if HAS_CURL_CFFI:
        try:
            html = await _fetch_curl_cffi(url)
            if html:
                logger.info("Fetched via curl_cffi")
                return html
        except Exception as exc:
            logger.warning(f"curl_cffi error: {exc}")

    # 3. httpx plain
    try:
        html = await _fetch_httpx(url)
        if html:
            logger.info("Fetched via httpx")
            return html
    except Exception as exc:
        logger.warning(f"httpx error: {exc}")

    return None


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _get_json_ld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract all JSON-LD blocks from the page."""
    results: List[Dict[str, Any]] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            text = script.get_text(strip=True)
            obj = json.loads(text)
            if isinstance(obj, list):
                results.extend(obj)
            else:
                results.append(obj)
        except Exception:
            pass
    return results


def _get_meta(soup: BeautifulSoup, *attrs: str) -> Optional[str]:
    """Return the content of the first matching <meta> tag."""
    for attr in attrs:
        # Try property=, name=, itemprop=
        for key in ("property", "name", "itemprop"):
            tag = soup.find("meta", {key: attr})
            if tag and tag.get("content"):
                return tag["content"].strip()
    return None


def _extract_article_html(soup: BeautifulSoup) -> str:
    """
    Extract the main article body as HTML, preserving tables, images,
    RTL divs, etc.  Falls back to <body> if no article element found.
    """
    # Priority: <article>, then common content wrappers
    candidates = [
        soup.find("article"),
        soup.find(id=re.compile(r"article|content|story|post|body", re.I)),
        soup.find(class_=re.compile(r"article|content|story|post|body", re.I)),
        soup.find("main"),
        soup.find("body"),
    ]
    for candidate in candidates:
        if candidate and isinstance(candidate, Tag):
            # Remove nav, header, footer, aside, scripts, styles, ads
            for tag in candidate.find_all(
                ["nav", "header", "footer", "aside", "script", "style", "noscript", "iframe"]
            ):
                tag.decompose()
            html = str(candidate)
            if len(html) > 200:
                return html
    return ""


def _iso_date(raw: Optional[str]) -> Optional[str]:
    """Attempt to parse and normalise a date string to ISO 8601."""
    if not raw:
        return None
    raw = raw.strip()
    # Already looks like ISO
    if re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", raw):
        return raw
    # Try common formats
    for fmt in (
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y/%m/%d",
        "%m/%d/%Y",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return raw  # return as-is if we can't parse it


def _guid_from_url(url: str) -> str:
    """Extract the trailing numeric or alphanumeric ID segment from a URL."""
    path = urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    if parts:
        last = parts[-1]
        # Try to find a numeric segment (e.g. 221709189)
        numeric = re.search(r"(\d{6,})", last)
        if numeric:
            return numeric.group(1)
        return last
    return url


def _source_name_from_url(url: str) -> str:
    """Derive a human-readable source name from the URL domain."""
    netloc = urlparse(url).netloc.lower()
    netloc = re.sub(r"^www\.", "", netloc)
    # e.g. finance.yahoo.com -> Yahoo Finance
    parts = netloc.split(".")
    if len(parts) >= 3:
        sub = parts[0].title()
        domain = parts[1].title()
        return f"{domain} {sub}"
    if len(parts) == 2:
        return parts[0].title()
    return netloc.title()


# ---------------------------------------------------------------------------
# Core extractor
# ---------------------------------------------------------------------------

class PageData:
    """Holds all raw extracted data from a page."""

    def __init__(self, url: str, soup: BeautifulSoup):
        self.url = url
        self.soup = soup
        self.json_ld = _get_json_ld(soup)

    # -- Individual field extractors -----------------------------------------

    @property
    def title(self) -> Optional[str]:
        # 1. JSON-LD headline
        for obj in self.json_ld:
            if v := obj.get("headline"):
                return str(v).strip()
        # 2. OG title
        if v := _get_meta(self.soup, "og:title", "twitter:title"):
            return v
        # 3. <title> tag
        if self.soup.title and self.soup.title.string:
            return self.soup.title.string.strip()
        return None

    @property
    def creator(self) -> Optional[str]:
        # 1. JSON-LD author
        for obj in self.json_ld:
            author = obj.get("author")
            if isinstance(author, dict):
                return author.get("name")
            if isinstance(author, list) and author:
                first = author[0]
                return first.get("name") if isinstance(first, dict) else str(first)
            if isinstance(author, str):
                return author
        # 2. Meta tags
        for attr in ("author", "article:author", "dc.creator", "DC.creator", "byl"):
            if v := _get_meta(self.soup, attr):
                return v
        # 3. Common DOM patterns
        for sel in (
            {"itemprop": "author"},
            {"rel": "author"},
            {"class": re.compile(r"author|byline|writer|creator", re.I)},
        ):
            tag = self.soup.find(attrs=sel)
            if tag and tag.get_text(strip=True):
                text = tag.get_text(strip=True)
                # Remove "By " prefix if present
                text = re.sub(r"(?i)^by\s+", "", text).strip()
                if text:
                    return text
        return None

    @property
    def published_at(self) -> Optional[str]:
        # 1. JSON-LD datePublished
        for obj in self.json_ld:
            if v := obj.get("datePublished"):
                return _iso_date(str(v))
        # 2. Meta tags
        for attr in (
            "article:published_time",
            "og:published_time",
            "datePublished",
            "DC.date",
            "date",
            "pubdate",
            "publish_date",
            "article:modified_time",
        ):
            if v := _get_meta(self.soup, attr):
                return _iso_date(v)
        # 3. <time> element
        for time_tag in self.soup.find_all("time"):
            dt = time_tag.get("datetime") or time_tag.get_text(strip=True)
            if dt:
                return _iso_date(dt)
        return None

    @property
    def content_html(self) -> str:
        return _extract_article_html(self.soup)

    @property
    def categories(self) -> List[str]:
        cats: List[str] = []
        # 1. JSON-LD articleSection / keywords
        for obj in self.json_ld:
            if v := obj.get("articleSection"):
                if isinstance(v, list):
                    cats.extend([str(x) for x in v])
                else:
                    cats.append(str(v))
            if v := obj.get("keywords"):
                if isinstance(v, list):
                    cats.extend([str(x) for x in v])
                elif isinstance(v, str):
                    cats.extend([k.strip() for k in v.split(",") if k.strip()])
        # 2. Meta keywords / article:tag
        for attr in ("keywords", "article:tag", "news_keywords"):
            if v := _get_meta(self.soup, attr):
                cats.extend([k.strip() for k in v.split(",") if k.strip()])
        # De-duplicate preserving order
        seen = set()
        result: List[str] = []
        for c in cats:
            lc = c.lower()
            if lc not in seen:
                seen.add(lc)
                result.append(c)
        return result

    @property
    def guid(self) -> str:
        return _guid_from_url(self.url)

    @property
    def source_name(self) -> str:
        # Check JSON-LD publisher
        for obj in self.json_ld:
            pub = obj.get("publisher")
            if isinstance(pub, dict) and pub.get("name"):
                return str(pub["name"])
        return _source_name_from_url(self.url)


# ---------------------------------------------------------------------------
# Schema-driven extraction
# ---------------------------------------------------------------------------

# Mapping from field name / description keywords → PageData property names
_FIELD_ALIASES: Dict[str, str] = {
    # Creator / author
    "creator": "creator",
    "author": "creator",
    "journalist": "creator",
    "byline": "creator",
    "writer": "creator",
    # Title / headline
    "title": "title",
    "headline": "title",
    # URL
    "url": "url",
    "link": "url",
    "permalink": "url",
    # Published date
    "published_at": "published_at",
    "published": "published_at",
    "date": "published_at",
    "pubdate": "published_at",
    "publish_date": "published_at",
    # Content / body
    "content": "content_html",
    "body": "content_html",
    "article": "content_html",
    "text": "content_html",
    # GUID / ID
    "guid": "guid",
    "id": "guid",
    # Categories / tags
    "categories": "categories",
    "tags": "categories",
    "topics": "categories",
    # Source name
    "source_name": "source_name",
    "source": "source_name",
    "publisher": "source_name",
    "site": "source_name",
}


def _match_field(field_name: str, description: str = "") -> Optional[str]:
    """
    Given a JSON Schema field name and description, return the
    PageData attribute that best matches it.
    """
    key = field_name.lower().replace("-", "_").replace(" ", "_")
    if key in _FIELD_ALIASES:
        return _FIELD_ALIASES[key]
    # Try description keywords
    desc_lower = description.lower()
    for keyword, attr in _FIELD_ALIASES.items():
        if keyword in desc_lower:
            return attr
    return None


def extract_for_schema(
    page: PageData,
    schema: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Given a PageData and a JSON Schema, extract and return a dict
    that satisfies the schema's properties.
    """
    if not schema:
        # No schema — return all available fields
        return {
            "url": page.url,
            "title": page.title,
            "creator": page.creator,
            "published_at": page.published_at,
            "content": page.content_html,
            "guid": page.guid,
            "categories": page.categories,
            "source_name": page.source_name,
        }

    properties: Dict[str, Any] = schema.get("properties", {})
    result: Dict[str, Any] = {}

    for field_name, field_def in properties.items():
        description = field_def.get("description", "") if isinstance(field_def, dict) else ""
        attr_name = _match_field(field_name, description)

        if attr_name:
            value = getattr(page, attr_name, None)
        else:
            value = None

        # Handle special case: url field always returns the scraped URL
        if field_name == "url":
            value = page.url

        result[field_name] = value

    return result


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------

class ScraperService:
    @staticmethod
    async def scrape(url: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch the URL, parse it, and extract data according to the schema.
        Returns a dict that satisfies the schema's properties.
        """
        html = await fetch_html(url)
        if not html:
            raise RuntimeError(f"Failed to fetch content from {url}")

        soup = BeautifulSoup(html, "html.parser")
        page = PageData(url=url, soup=soup)
        return extract_for_schema(page, schema)
