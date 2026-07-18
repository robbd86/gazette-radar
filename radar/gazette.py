"""The Gazette official notices feed client (free, no auth).

API docs: https://github.com/TheGazette/DevDocs
NOTE: the endpoint returns HTTP 500 to non-browser user agents, so we send one.
"""
import logging
import re
from datetime import date, timedelta

import requests

log = logging.getLogger("gazette")

BASE = "https://www.thegazette.co.uk/all-notices/notice/data.json"
# NB: do NOT send an "Accept: application/json" header - the Gazette server
# returns HTTP 500 when it's combined with the data.json URL (verified 2026-07).
# The .json extension alone selects the format.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
}

COMPANY_NO_RE = re.compile(r"Company Number\s*:?\s*(\w{6,10})", re.IGNORECASE)
REG_OFFICE_RE = re.compile(
    r"Registered office\s*:?\s*(.{10,120}?)(?:\s+In the|\s+Nature of|\s*$)",
    re.IGNORECASE,
)
TAG_RE = re.compile(r"<[^>]+>")


def _clean(html: str) -> str:
    return " ".join(TAG_RE.sub(" ", html or "").split())


def _get_with_retries(params: dict, attempts: int = 4) -> dict | None:
    """The Gazette API throws transient 500s; retry with backoff."""
    import time

    for i in range(attempts):
        try:
            r = requests.get(BASE, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            log.warning("Gazette HTTP %s (attempt %d)", r.status_code, i + 1)
        except Exception as e:
            log.warning("Gazette request error (attempt %d): %s", i + 1, e)
        time.sleep(10 * (i + 1))
    log.error("Gazette API failed after %d attempts", attempts)
    return None


def fetch_notices(centre: str, radius_miles: int, lookback_days: int) -> list[dict]:
    """All corporate-insolvency notices within radius, published in the window."""
    since = (date.today() - timedelta(days=lookback_days)).isoformat()
    notices, page = [], 1
    while page <= 10:  # hard safety cap
        params = {
            "categorycode": "24",
            "results-page-size": "50",
            "results-page": str(page),
            "location-postcode-1": centre,
            "location-distance-1": str(radius_miles),
            "start-publish-date": since,
        }
        data = _get_with_retries(params)
        if data is None:
            break
        entries = data.get("entry") or []
        if isinstance(entries, dict):  # single result comes back as a bare object
            entries = [entries]
        if not entries:
            break
        for e in entries:
            notices.append(_parse(e))
        total = int(data.get("f:total") or 0)
        if page * 50 >= total:
            break
        page += 1
        import time as _t; _t.sleep(2)
    log.info("Gazette returned %d notices since %s", len(notices), since)
    return notices


def _parse(entry: dict) -> dict:
    content = _clean(str(entry.get("content", "")))
    m_no = COMPANY_NO_RE.search(content)
    m_office = REG_OFFICE_RE.search(content)
    links = entry.get("link") or []
    if isinstance(links, dict):
        links = [links]
    url = next(
        (l.get("@href") for l in links if l.get("@rel") is None and l.get("@href")),
        entry.get("id", ""),
    )
    return {
        "id": entry.get("id", ""),
        "company": (entry.get("title") or "").strip(),
        "notice_type": ((entry.get("category") or {}).get("@term") or "").strip(),
        "published": (entry.get("published") or "")[:10],
        "company_number": m_no.group(1) if m_no else None,
        "registered_office": m_office.group(1).strip() if m_office else None,
        "snippet": content[:300],
        "url": url,
    }
