"""Talk to Apple's public, keyless endpoints: iTunes Search/Lookup and the
customer-reviews RSS feed. Standard library only."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

USER_AGENT = "app-inspect-cli (+https://github.com/Harrison0223-svg/app-inspect-cli)"
LOOKUP_URL = "https://itunes.apple.com/lookup?id={id}&country={country}"
SEARCH_URL = "https://itunes.apple.com/search?term={term}&entity=software&country={country}&limit={limit}"
REVIEWS_URL = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={id}/sortby=mostrecent/json"
MAX_REVIEW_PAGES = 10  # Apple serves at most 10 pages x 50 reviews

Getter = Callable[[str], Any]


class AppInspectError(Exception):
    """A problem worth showing the user without a traceback."""


def http_get_json(url: str, timeout: float = 20.0, retries: int = 2) -> Any:
    last: Optional[Exception] = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return {}
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            # Apple answers 400/404 for past-the-end review pages; that is not an error.
            if exc.code in (400, 404):
                return {}
            last = exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise AppInspectError(f"Could not reach Apple ({url}): {last}")


_URL_ID = re.compile(r"(?:/id|[?&]id=)(\d{5,})")
_URL_COUNTRY = re.compile(r"apps\.apple\.com/([a-z]{2})/", re.I)


def parse_app_ref(ref: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (app_id, country_from_url). app_id is None when ref is a search term."""
    ref = ref.strip()
    if ref.isdigit():
        return ref, None
    if ref.lower().startswith("id") and ref[2:].isdigit():
        return ref[2:], None
    m = _URL_ID.search(ref)
    if m:
        c = _URL_COUNTRY.search(ref)
        return m.group(1), (c.group(1).lower() if c else None)
    return None, None


def search(term: str, country: str = "us", limit: int = 5, get: Getter = http_get_json) -> List[Dict[str, Any]]:
    url = SEARCH_URL.format(term=urllib.parse.quote(term), country=country, limit=limit)
    data = get(url) or {}
    return list(data.get("results") or [])


def lookup(app_id: str, country: str = "us", get: Getter = http_get_json) -> Dict[str, Any]:
    data = get(LOOKUP_URL.format(id=app_id, country=country)) or {}
    results = data.get("results") or []
    if not results:
        raise AppInspectError(f"No App Store app with id {app_id} in country '{country}'.")
    return results[0]


def _entries(feed_json: Any) -> List[Dict[str, Any]]:
    feed = (feed_json or {}).get("feed") or {}
    entries = feed.get("entry") or []
    if isinstance(entries, dict):  # a single entry comes back as an object
        entries = [entries]
    return [e for e in entries if isinstance(e, dict) and "im:rating" in e]


def parse_review(entry: Dict[str, Any]) -> Dict[str, Any]:
    def label(key: str, default: str = "") -> str:
        v = entry.get(key) or {}
        return v.get("label", default) if isinstance(v, dict) else default

    return {
        "id": label("id"),
        "rating": int(label("im:rating", "0") or 0),
        "version": label("im:version") or None,
        "updated": label("updated") or None,
        "title": label("title"),
        "content": label("content"),
        "votes": int(label("im:voteCount", "0") or 0),
    }


def reviews(app_id: str, country: str = "us", pages: int = MAX_REVIEW_PAGES, get: Getter = http_get_json) -> List[Dict[str, Any]]:
    pages = max(1, min(int(pages), MAX_REVIEW_PAGES))
    out: List[Dict[str, Any]] = []
    seen = set()
    for page in range(1, pages + 1):
        entries = _entries(get(REVIEWS_URL.format(country=country, page=page, id=app_id)))
        if not entries:
            break
        for e in entries:
            r = parse_review(e)
            if r["id"] in seen or not 1 <= r["rating"] <= 5:
                continue
            seen.add(r["id"])
            out.append(r)
        if len(entries) < 50:
            break
    return out
