# Incident: AIS ingestion silent outage (2026-06-09 → 2026-06-11)

| | |
|---|---|
| Impact | No fresh AIS for ~2 days; dashboard showed 0 vessels / zeroed metrics for all ports |
| Detected | 2026-06-11, during a frontend audit ("why is the map empty?") — **not** by monitoring |
| Resolved | 2026-06-11 09:02 UTC (first successful `batch_flushed`, 6,046 messages) |
| Severity | High (core data pipeline down) · silent (no alert fired) |

## Timeline

- **2026-06-10** — Stack migrated from x86_64 to arm64 to fix a cross-arch build
  failure. The predict function got platform-targeted wheels; the shared build
  macro for the other six functions did not.
- **~2026-06-10 onward** — every `ais-snapshot` / `weather` / `noaa` invocation
  failed at import: `No module named 'pydantic_core._pydantic_core'` (host-arch
  binary on an arm64 Lambda). Functions without pydantic (features, export,
  predict) kept running, so forecasts kept updating — masking the outage.
- **2026-06-11** — audit found `vessels: []` for all ports; logs revealed the
  ImportModuleError. Fixing it exposed a **second latent bug**: commit `60d2f78`
  had deleted `warehouse/seeds/un_locode.csv`, which `ais_stream.py` loads at
  import to build AIS bounding boxes → `FileNotFoundError`.

## Root causes (two, stacked)

1. **Host-architecture native wheels.** The Makefile's shared `_build` ran a
   plain `pip install`, producing wheels for the build host (macOS laptop or
   x86_64 CI runner) instead of the arm64 Lambda target.
2. **Deleted-but-imported seed file.** A refactor removed the UN/LOCODE CSV
   without checking importers; the serverless ingestion path still required it.
   The wheel crash had been masking this since the seed's deletion.

## Why it stayed silent

- The export Lambda kept publishing (with empty vessel lists), so the dashboard
  rendered *plausible zeros* rather than an error.
- No post-deploy smoke test invoked a deployed function.
- The freshness pill data existed but was easy to miss; no prominent staleness
  signal existed in the UI.

## Fixes shipped

| Fix | Where |
|---|---|
| Force Linux arm64 wheels for **all** functions | `Makefile` (`--platform manylinux2014_aarch64 --only-binary=:all:`) |
| Restore + bundle the seed | `warehouse/seeds/un_locode.csv`, `LAMBDA_MODULES` |
| Guard test for the seed | `tests/test_port_seed.py` |
| Pre-deploy wheel-arch gate | `scripts/check_wheel_arch.sh`, wired into `deploy.sh` + CI |
| Post-deploy smoke test (invokes freshness Lambda) | `.github/workflows/deploy-serverless.yml` |
| Staleness banner in the UI (>2 h SLA) | `dashboard-v2/src/components/FreshnessBanner.jsx` |

## Lessons

1. Build for the **target** platform, never the host.
2. A passing deploy is not a working system — smoke-test the deployed artifact.
3. Files loaded at import are dependencies; grep for importers before deleting.
4. Design dashboards so "no data" looks like an outage, not like calm.
