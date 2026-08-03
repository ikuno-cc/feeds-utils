import re
import logging
import asyncio
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup
import httpx
from curl_cffi import requests as cffi_requests

try:
    from playwright.async_api import async_playwright
    from playwright_stealth.stealth import Stealth
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)

MIRROR_DOMAINS = [
    "archive.ph",
    "archive.today",
    "archive.is",
    "archive.md"
]


def extract_single_archive_url(html_content: str, domain: str = "archive.ph") -> Optional[str]:
    """
    Parses HTML content from archive.ph search or submission page.
    If multiple snapshot results exist (e.g. thumbnails page), selects the first/newest snapshot URL.
    Returns canonical shortlink (e.g. https://archive.ph/H6GcX).
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 1. Look for snapshot links in search result items / thumbnail wrappers
    shortlinks: List[str] = []
    
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        
        # Match pattern like /H6GcX or https://archive.ph/H6GcX or /2026.08.03-095512/...
        match = re.search(r'/(?:[a-zA-Z0-9]{5,8}|[0-9]{4}\.[0-9]{2}\.[0-9]{2}-[0-9]{6}/.+)$', href)
        if match:
            # Clean base domain
            if href.startswith("http://") or href.startswith("https://"):
                full_url = href
            else:
                full_url = f"https://{domain.rstrip('/')}{href}"
                
            # Exclude navigational endpoints
            if not any(full_url.endswith(x) for x in ["/submit/", "/search/", "/w/"]):
                if full_url not in shortlinks:
                    shortlinks.append(full_url)

    if shortlinks:
        # Return the newest snapshot shortlink
        return shortlinks[0]

    # 2. Check canonical link tag or meta og:url
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        href = canonical["href"]
        if "archive." in href:
            return href

    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content"):
        content = og_url["content"]
        if "archive." in content:
            return content

    return None


class ArchiveService:
    @staticmethod
    async def get_or_create_archive(target_url: str, preferred_domain: str = "archive.ph") -> Tuple[str, str, str]:
        """
        Main method to retrieve or submit an archived URL.
        Returns tuple: (archive_url, domain_used, status)
        """
        domain = preferred_domain if preferred_domain in MIRROR_DOMAINS else "archive.ph"
        
        # 1. Try Playwright on primary domain first
        if HAS_PLAYWRIGHT:
            try:
                res = await ArchiveService._try_playwright(target_url, domain)
                if res:
                    return res[0], domain, "success"
            except Exception as e:
                logger.warning(f"Playwright attempt failed for {domain}: {e}")

        # 2. Try curl_cffi on primary domain
        try:
            res = await ArchiveService._try_curl_cffi(target_url, domain)
            if res:
                return res[0], domain, "success"
        except Exception as e:
            logger.warning(f"curl_cffi attempt failed for {domain}: {e}")

        # 3. Fast fallback to Wayback Machine (web.archive.org)
        wayback_url = await ArchiveService._try_wayback(target_url)
        if wayback_url:
            return wayback_url, "web.archive.org", "wayback_fallback"

        # 4. Canonical search link format
        fallback_url = f"https://{domain}/{target_url}"
        return fallback_url, domain, "cached_redirect"

    @staticmethod
    async def _try_playwright(target_url: str, domain: str) -> Optional[Tuple[str, str]]:
        """
        Uses Playwright async browser with stealth context to navigate archive.ph,
        search/submit target_url, and resolve multi-result pages.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
            
            try:
                stealth = Stealth()
                await stealth.apply_stealth_async(page)
            except Exception:
                pass

            search_endpoint = f"https://{domain}/search/?q={target_url}"
            try:
                await page.goto(search_endpoint, wait_until="domcontentloaded", timeout=7000)
            except Exception:
                pass
            
            final_url = page.url
            if re.search(r'archive\.[a-z]+/[a-zA-Z0-9]{5,8}$', final_url):
                await browser.close()
                return final_url, "direct_redirect"

            content = await page.content()
            extracted = extract_single_archive_url(content, domain)
            
            if extracted:
                await browser.close()
                return extracted, "parsed_results"

            await browser.close()
            return None

    @staticmethod
    async def _try_curl_cffi(target_url: str, domain: str) -> Optional[Tuple[str, str]]:
        """
        Uses curl_cffi with TLS fingerprint impersonation.
        """
        def sync_req():
            url = f"https://{domain}/search/?q={target_url}"
            resp = cffi_requests.get(
                url,
                impersonate="chrome124",
                allow_redirects=True,
                timeout=5
            )
            if resp.status_code == 200:
                if re.search(r'archive\.[a-z]+/[a-zA-Z0-9]{5,8}$', resp.url):
                    return resp.url, "direct"
                ext = extract_single_archive_url(resp.text, domain)
                if ext:
                    return ext, "parsed"
            return None

        return await asyncio.to_thread(sync_req)

    @staticmethod
    async def _try_wayback(target_url: str) -> Optional[str]:
        """
        Queries Wayback Machine (archive.org) API as a fallback.
        """
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                api_url = f"https://archive.org/wayback/available?url={target_url}"
                res = await client.get(api_url)
                if res.status_code == 200:
                    data = res.json()
                    snapshots = data.get("archived_snapshots", {})
                    closest = snapshots.get("closest", {})
                    if closest.get("available") and closest.get("url"):
                        return closest.get("url")
        except Exception as e:
            logger.warning(f"Wayback Machine fallback failed: {e}")
        return None
