# 04 — Performance Evaluation

_Last updated 2026-06-09 · Update this whenever the model or system is measured._

## 1. Model performance

### How we evaluate
- **Split:** time-aware 80/20 (chronological, no shuffle) — prevents future leakage.
- **Metric:** AUC-ROC (robust to class imbalance; positive rate ≈ 0.20).
- **Imbalance:** `scale_pos_weight = neg_count / pos_count` from the training labels.

### Results log

| Date | Dataset rows | Pos. rate | AUC-ROC | Notes |
|---|---|---|---|---|
| 2026-05 (v1) | ~168 | 0.20 | 0.82 | Noisy — 3 days of data, tiny test set. Pipeline-proof, not production-accuracy. |
| _next_ | _TBD_ | | | Retrain after weeks of ingestion |

### Honest caveats
- 168 rows is far too small for a trustworthy AUC. 0.82 is a **noisy point estimate**.
- The real deliverable in v1 is the *pipeline*, not the score. Accuracy improves as
  data accumulates with zero code changes (retrain = re-run).
- No cross-validation yet (too little data). Add k-fold once rows > ~2,000.

## 2. System performance

| Metric | Target (NFR) | Current | How measured |
|---|---|---|---|
| Forecast freshness | ≤ 2h (NFR1) | manual today | `predictions.json` timestamp vs now |
| Running cost | < $10/mo (NFR2) | ~$3/mo paused | AWS Cost Explorer (eu-west-3) |
| Batch failure isolation | 1 port ≠ whole batch (NFR3) | ✅ try/except | code review |
| Lint/test | green (NFR5) | ✅ ruff | `ruff check`, `pytest` |

## 3. Cost model (honest)

The only meaningful recurring cost is **Athena scan volume** ($5/TB scanned).

| Cost source | Driver | Status |
|---|---|---|
| `export_lambda` querying RAW NDJSON hourly | ~30 queries/hr re-scanning raw | **#1 cost (W3)** — deferred fix |
| CTAS rebuild (v1.2) | full 30-day re-scan per rebuild | acceptable at current size; flag for incremental |
| Lambda compute | seconds/run | negligible |
| S3 storage | grows slowly | pennies |
| CloudFront + static JSON | serving | ≈ $0 |
| CloudWatch dashboard | fixed | ~$3/mo |

**Cost levers (in priority order):**
1. Read gold (compressed, partitioned Parquet), never raw, in the hot path.
2. Compact small files (Athena hates thousands of tiny NDJSON objects).
3. Keep serving static + cached.
4. Pause ingestion when not collecting (`scripts/pause.sh`).

## 4. Engineering maturity scorecard

| Capability | v1.1 | v1.2 target |
|---|---|---|
| Reproducible deploy (IaC) | ✅ SAM | ✅ |
| Declared dependencies | ❌ ML deps missing | ✅ |
| Self-updating pipeline | ❌ manual | ✅ cloud loop |
| Single source of truth | ✅ ports/features | ✅ |
| Data honesty | ✅ (berth fix) | ✅ |
| Tests | partial | + smoke tests on new lambdas |
| CI/CD | ❌ | deferred (Phase 7) |
| Model registry / drift | ❌ | deferred (justified by scale) |

## 5. Self-evaluation prompts (revisit each phase)

- Did this change reduce or increase Athena scan volume?
- Is every number on the dashboard real or labelled derived?
- Could a stranger deploy this from the repo alone?
- Did I add a dependency? If so, is it justified in this blueprint?
