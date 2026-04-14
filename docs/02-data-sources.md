# Data Sources

Formal audit of every data source used in the Data Party Logistics platform. Each source was tested with a live API call before any ingestion code was written.

## Audit table

| Source | License | Auth | Rate limit | Latency | Update freq | Schema stability | Historical depth | Status |
|---|---|---|---|---|---|---|---|---|
| AISStream.io | Free tier (non-commercial) | API key (WebSocket) | ~1000 concurrent | 2-5s | Real-time | Stable (v0) | Live only | Tested |
| UN Comtrade | Free (public) | Optional registration | 100 req/hr (anon) | 1-3s | Monthly | Stable | 1962-present | Tested |
| Open-Meteo | Free (CC BY 4.0) | None | 10k req/day | <500ms | Hourly | Very stable | ~3 months | Tested |
| NOAA CDO | Free (US gov) | API token | 1000 req/day | <1s | Daily | Stable | Decades | Tested |
| FRED | Free (public) | API key | 120 req/min | <200ms | Monthly | Very stable | 1997-present | Tested |
| GDELT 2.0 | Free (public) | None | Unlimited | <2s | Every 15 min | Stable | 1979-present | Tested |
| WPI (NGA) | Public domain (US gov) | None — bulk download | N/A | N/A | Annual | Stable | 2017 edition (3,669 ports) | Seeded |

## Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AISStream changes WebSocket schema | Low | High | Pin to v0, validate with Pydantic, alert on schema mismatch |
| Comtrade rate limit hit | Medium | Low | Batch requests, cache responses, implement backoff |
| Open-Meteo downtime | Low | Medium | Fall back to NOAA for weather data |
| GDELT feed URL changes | Low | Medium | The lastupdate.txt pattern has been stable for years; monitor with freshness check |
| WPI edition is outdated (2017) | Medium | Low | Port locations are stable; only facilities data degrades. Re-download from msi.nga.mil annually |

## Notes

- All sources were tested on 2026-04-14 with live API calls or direct downloads.
- API keys are stored in `.env` (Zone 2 — local only, never committed).
- Detailed per-source documentation is in the ingestion client code (Week 2).

## WPI detail

- **Source:** NGA Maritime Safety Information — [msi.nga.mil/Publications/WPI](https://msi.nga.mil/Publications/WPI)
- **Format:** ESRI Shapefile (`.shp` + `.dbf`), converted to CSV via `pyshp`
- **File in repo:** `warehouse/seeds/wpi/wpi.csv`
- **Edition:** 2017 (latest available on HDX mirror)
- **Records:** 3,669 ports, 78 columns
- **Key columns for modelling:** `INDEX_NO`, `PORT_NAME`, `COUNTRY`, `LATITUDE`, `LONGITUDE`, `HARBORSIZE`, `HARBORTYPE`, `SHELTER`, `CHAN_DEPTH`, `TIDE_RANGE`, `MAX_VESSEL`, `ENTRY_TIDE`, `ENTRYSWELL`, `ENTRY_ICE`, `PILOT_REQD`, `PILOTAVAIL`, `TUG_ASSIST`, `PORTOFENTR`
- **Dropped columns:** ~50 vessel services fields (cranes, provisions, comms, repairs) — not relevant to ETA/congestion models
- **Update cadence:** Static seed — re-download annually from NGA, no scheduled ingestion needed
