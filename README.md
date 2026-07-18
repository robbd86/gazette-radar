# Gazette Liquidation Radar

Daily scan of The Gazette (the UK's official insolvency record) for manufacturing
and engineering companies entering administration/liquidation near you — so you can
contact the administrator about surplus control equipment **before** it reaches the
auction houses. Alerts to Telegram each weekday morning.

## How it works
1. Pulls all corporate insolvency notices published in the last 2 days within your
   radius (Gazette official JSON feed, free, no key).
2. Keeps only the useful notice types (administrator/liquidator appointments,
   winding-up resolutions and orders, creditor meetings).
3. Filters to interesting companies by SIC code via Companies House (if you add a
   free CH_API_KEY) and/or industry keywords.
4. One Telegram alert per company: name, notice type, address, SIC codes, links to
   the Gazette notice (administrator's name + contact is in the full notice) and
   the Companies House record.

## Setup (same pattern as plc-sniper)
1. New **private** GitHub repo `gazette-radar`, upload these files (keep the
   `.github/workflows/` path — create radar.yml via "Create new file" if the
   uploader drops it).
2. Settings → Secrets and variables → Actions → add:
   - `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` — same values as plc-sniper
   - `CH_API_KEY` (optional but recommended): free from
     https://developer.company-information.service.gov.uk → register application
     → copy the REST API key. Without it, keyword filtering still works.
3. Edit `config.yaml`: set `location.centre` to your town or full postcode.
4. Actions → Gazette Radar → Run workflow to test.

Runs weekdays at 06:15 UTC automatically.

## What to do with an alert
Open the Gazette notice — it names the administrator/liquidator (usually an
insolvency practitioner firm) and office holder numbers. Ring or email within days
of appointment:

> "I understand you've been appointed over [Company]. I buy surplus control and
> automation equipment — PLCs, HMIs, drives, panels. If there are workshop or
> production assets to realise, I can view quickly and make a fast cash offer."

Administrators want quick, clean asset sales. Being early and easy to deal with is
the entire edge.

## Tuning
- `radius_miles`: 60 is a comfortable day-trip collection radius; widen for
  administration appointments (bigger companies justify longer drives).
- Too much noise → set `filtering.mode: "sic"` (strict, CH key required).
  Too quiet → add keywords or widen `sic_ranges`.
- `notice_types`: "Petitions to Wind Up" would give you even earlier warning
  (before insolvency is confirmed) — add it if you want a heads-up pipeline,
  but don't contact anyone at petition stage; many petitions get dismissed.
