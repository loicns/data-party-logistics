# 08 — Operations Runbook

_How to deploy, verify, retrain, and troubleshoot the DPL serverless pilot._

## Architecture in one breath

Hourly, in `eu-west-3`, stack `dpl-serverless-pilot` (SAM, **arm64**):

```
:00  ais-snapshot     capture ~5 min of AIS  -> raw/source=ais/
:10  weather          fetch marine weather   -> raw/source=weather/
:15  features         DROP+CTAS gold tables from raw (Athena)
:25  export           publish demo-data.js (vessels + metrics) -> dashboard bucket -> CloudFront
:30  predict          score 10 ports -> predictions.json -> CloudFront
```

Dashboard (Vercel, `dashboard-v2/`) reads `demo-data.js` + `predictions.json` from CloudFront.

## Buckets & names

| Thing | Value |
|---|---|
| Data bucket | `dpl-serverless-pilot-861276086413-pilot-data` |
| Public/dashboard bucket | `dpl-dashboard-861276086413` |
| CloudFront base | `https://dz4lgcial54jx.cloudfront.net` |
| Model artifact | `models/port_congestion/model.txt` (native LightGBM booster) |
| Athena DB | `dpl_pilot` |

## Deploy

**Always use `./deploy.sh`** — never a bare `sam deploy`.

```bash
./deploy.sh                       # build + deploy (loads the AIS key from .env)
./deploy.sh --no-confirm-changeset
```

`deploy.sh` injects `AisStreamApiKey` from `.env` (the single source of truth; it
is never stored in `samconfig.toml` or git).

### The arm64 native-wheel rule (critical)

The stack runs **arm64 Lambdas**. Compiled deps (`pydantic_core`, `lightgbm`,
`scipy`, `numpy`) must be **Linux arm64** wheels regardless of where you build
(macOS laptop or x86_64 CI). The Makefile enforces this with
`pip --platform manylinux2014_aarch64 --only-binary=:all:` for every function.
`libgomp.so.1` (OpenMP, needed by lightgbm) is vendored in `vendor/lib/`.

> If a function fails at runtime with `No module named '..._core'` or
> `cannot open shared object file`, a wheel was built for the wrong platform —
> check the Makefile platform flags.

### The seed-file rule

`ais_stream` / `weather` load `warehouse/seeds/un_locode.csv` **at import** to
build AIS bounding boxes. It must be tracked in git and bundled (it's in
`LAMBDA_MODULES`). `tests/test_port_seed.py` guards against it going missing.

## Retrain the model

```bash
uv run python models/training/build_dataset.py   # gold tables -> training parquet
uv run python models/training/train.py           # trains, asserts AUC>=0.65, uploads model.txt
# copy to the bucket the predict Lambda reads:
aws s3 cp s3://dpl-raw-861276086413/models/port_congestion/model.txt \
  s3://dpl-serverless-pilot-861276086413-pilot-data/models/port_congestion/model.txt \
  --profile dpl --region eu-west-3
```

## Verify the loop

```bash
# predictions fresh + non-null?
curl -s "https://dz4lgcial54jx.cloudfront.net/predictions.json" | head -c 300

# dashboard data has vessels?
curl -s "https://dz4lgcial54jx.cloudfront.net/demo-data.js" \
  | sed 's/^window.DEMO_DATA = //; s/;$//' \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(sum(len(p['vessels']) for p in d['ports'].values()),'vessels')"
```

## Troubleshooting — dashboard shows zeros / empty map

1. **Check the freshness banner** on the dashboard — if data is hours old, the
   pipeline is stale, not the port calm.
2. **ais-snapshot logs:**
   ```bash
   aws logs filter-log-events --log-group-name /aws/lambda/dpl-serverless-pilot-ais-snapshot \
     --region eu-west-3 --start-time $(( ($(date +%s)-3600)*1000 )) \
     --query "events[*].message" --output text | grep -iE "error|batch_flushed"
   ```
   Expect `batch_flushed ... date=<today>`. `ImportModuleError` -> wrong-arch
   wheel; `FileNotFoundError un_locode.csv` -> seed not bundled.
3. **Latest raw partition:**
   `aws s3 ls s3://dpl-serverless-pilot-861276086413-pilot-data/raw/source=ais/`
   — should show today.
4. The export vessel query only surfaces vessels seen in the **last 6 hours**, so
   stale AIS => empty vessels by design.

## Known gaps (see v1.3)

- **CNSHA (Shanghai) surfaces 0 vessels** — likely a bbox/coords coverage gap.
- ETA / "confidence" are heuristics (distance ÷ speed), not modelled.
- Train/test split is stratified-random (mild leakage) pending more history.
