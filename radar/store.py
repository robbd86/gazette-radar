"""SQLite dedupe + Telegram alerts for the liquidation radar."""
import logging
import sqlite3
import time
from pathlib import Path

import requests

log = logging.getLogger("radar")

DB_PATH = Path(__file__).resolve().parent.parent / "radar.db"


def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """CREATE TABLE IF NOT EXISTS seen (
            notice_id TEXT PRIMARY KEY,
            first_seen INTEGER NOT NULL)"""
    )
    return con


def is_new(con, notice_id: str) -> bool:
    if con.execute("SELECT 1 FROM seen WHERE notice_id=?", (notice_id,)).fetchone():
        return False
    con.execute(
        "INSERT INTO seen (notice_id, first_seen) VALUES (?,?)",
        (notice_id, int(time.time())),
    )
    con.commit()
    return True


def prune(con, days: int = 120):
    cutoff = int(time.time()) - days * 86400
    con.execute("DELETE FROM seen WHERE first_seen < ?", (cutoff,))
    con.commit()


def send_telegram(bot_token: str, chat_id: str, text: str):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        r.raise_for_status()
    except Exception as e:
        log.error("Telegram send failed: %s", e)


def format_company(company: str, notices: list[dict], enrichment: dict | None) -> str:
    """One alert block per company (a company often files several notices at once)."""
    types = " + ".join(sorted({n["notice_type"] for n in notices}))
    first = notices[0]
    lines = [
        f"🏭 <b>{company}</b>",
        f"{types} · published {first['published']}",
    ]
    if first.get("registered_office"):
        lines.append(f"📍 {first['registered_office']}")
    if enrichment and enrichment.get("sic_codes"):
        lines.append(f"SIC: {', '.join(enrichment['sic_codes'][:4])}")
    lines.append(f'<a href="{first["url"]}">Gazette notice</a>')
    if first.get("company_number"):
        lines.append(
            f'<a href="https://find-and-update.company-information.service.gov.uk/'
            f'company/{first["company_number"]}">Companies House</a>'
        )
    return "\n".join(lines)
