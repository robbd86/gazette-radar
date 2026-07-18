"""Optional Companies House enrichment (free API key).

Get a key at https://developer.company-information.service.gov.uk
(register an application, copy the REST API key). Used to pull SIC codes so
we can filter to manufacturing/engineering companies properly.
"""
import logging

import requests

log = logging.getLogger("companies_house")

BASE = "https://api.company-information.service.gov.uk/company/"


def get_company(api_key: str, company_number: str) -> dict | None:
    """Returns {'sic_codes': [...], 'company_name': ..., 'status': ...} or None."""
    try:
        r = requests.get(
            BASE + company_number.strip().upper(),
            auth=(api_key, ""),
            timeout=15,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        d = r.json()
        return {
            "sic_codes": d.get("sic_codes") or [],
            "company_name": d.get("company_name"),
            "status": d.get("company_status"),
        }
    except Exception as e:
        log.warning("CH lookup failed for %s: %s", company_number, e)
        return None


def sic_matches(sic_codes: list[str], ranges: list[list[int]]) -> bool:
    for code in sic_codes:
        try:
            n = int(str(code)[:5])
        except ValueError:
            continue
        for lo, hi in ranges:
            if lo <= n <= hi:
                return True
    return False
