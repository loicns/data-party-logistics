# DPL Dashboard (dashboard-v2)

React + Vite dashboard for the Data Party Logistics port-congestion pilot.
Runs on Vercel and reads static artifacts from CloudFront — no backend API in
production. CloudFront is data-only; its root path is not a dashboard UI.

## Data sources

| Artifact | Produced by | Contents |
|---|---|---|
| `demo-data.js` | export Lambda (hourly :25) | vessels, metrics, trend, berth aggregate |
| `predictions.json` | predict Lambda (hourly :30) | LightGBM 24h congestion forecast |

The predictions URL is **derived** from `VITE_DATA_URL` by filename swap
(`demo-data.js` → `predictions.json`), so both must live under the same
CloudFront prefix. Field meanings & provenance: `../docs/blueprint/10-DATA-DICTIONARY.md`.

## Environment

| Var | Where | Value |
|---|---|---|
| `VITE_DATA_URL` | Vercel env + `.env.production` | `https://dz4lgcial54jx.cloudfront.net/demo-data.js` |

Unset in local dev → falls back to `public/demo-data.js` fixture / local API proxy.

## Develop / build

```bash
npm ci
npm run dev      # local dev server
npm run lint     # eslint
npm run build    # production build (route-level code splitting)
```

## Deploy

Push to `main` — the Vercel git integration builds and promotes automatically
(project `dpl-dashboard`, root directory `dashboard-v2`). CLI alternative:
run `vercel --prod` from the **repo root**, not from inside `dashboard-v2`
(the project's root-directory setting would double the path).

Production UI: `https://dpl-dashboadrd.vercel.app/`
Data CDN: `https://dz4lgcial54jx.cloudfront.net/` (`/demo-data.js`,
`/demo-data.json`, `/predictions.json`, `/roadmap.json`; `/` intentionally does
not serve the app).

## Page map

| Route | Page | Data |
|---|---|---|
| `/` | Operations dashboard | metrics, map, Active Traffic preview (6) |
| `/map` | Traffic map | all surfaced vessels (≤250/port), zone filters |
| `/schedule` | Traffic board | filterable table, heuristic ETAs (`est.`) |
| `/berth` | Berth occupancy | aggregate only — no vessel-to-berth claims |
| `/insights` | Congestion insights | trend + **model** 24h forecast card |
| `/predictive` | Predictive analysis | **model** forecast hero + observed trend |

## Honesty rules (enforced in code)

- Every number is real, derived, or labelled `est.` — see the data dictionary.
- The staleness banner appears when data is older than the 2 h SLA.
- No decorative/non-functional controls.
