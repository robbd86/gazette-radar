#!/usr/bin/env python3
"""Gazette Liquidation Radar - daily scan for insolvent manufacturing companies
near you, so you can contact the administrator about surplus control equipment
before assets reach the auction houses.

Runs once daily via GitHub Actions. Secrets: TELEGRAM_BOT_TOKEN,
TELEGRAM_CHAT_ID, optionally CH_API_KEY for Companies House SIC filtering.
"""
import logging
import os
import sys
from collections import defaultdict

import yaml

from radar import companies_house, gazette, store

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
log = logging.getLogger("main")


def keyword_match(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in keywords)


def main():
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    bot = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    ch_key = os.environ.get("CH_API_KEY", "")

    fcfg = cfg["filtering"]
    mode = fcfg.get("mode", "both")
    if mode in ("sic", "both") and not ch_key:
        log.warning("No CH_API_KEY set - falling back to keyword filtering only")
        mode = "keywords"

    notices = gazette.fetch_notices(
        cfg["location"]["centre"],
        cfg["location"]["radius_miles"],
        cfg.get("lookback_days", 2),
    )

    wanted_types = cfg["notice_types"]
    con = store.connect()
    store.prune(con)

    # Group new, wanted notices by company
    by_company: dict[str, list[dict]] = defaultdict(list)
    for n in notices:
        if not any(t.lower() in n["notice_type"].lower() for t in wanted_types):
            continue
        if not store.is_new(con, n["id"]):
            continue
        if keyword_match(n["company"], fcfg.get("exclude_keywords", [])):
            continue
        by_company[n["company"]].append(n)

    log.info("%d companies with new relevant notices", len(by_company))

    alerts_sent = 0
    for company, comp_notices in by_company.items():
        text_blob = company + " " + " ".join(n["snippet"] for n in comp_notices)
        enrichment = None
        interesting = False

        if mode in ("sic", "both"):
            num = next(
                (n["company_number"] for n in comp_notices if n["company_number"]), None
            )
            if num:
                enrichment = companies_house.get_company(ch_key, num)
            if enrichment:
                interesting = companies_house.sic_matches(
                    enrichment["sic_codes"], fcfg["sic_ranges"]
                )
            elif mode == "both":
                interesting = keyword_match(text_blob, fcfg["industry_keywords"])
        else:
            interesting = keyword_match(text_blob, fcfg["industry_keywords"])

        if not interesting:
            continue

        store.send_telegram(
            bot, chat, store.format_company(company, comp_notices, enrichment)
        )
        alerts_sent += 1

    if alerts_sent:
        log.info("Sent %d company alerts", alerts_sent)
    else:
        log.info("No interesting insolvencies today")
    con.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.critical("Fatal: %s", e)
        sys.exit(1)
