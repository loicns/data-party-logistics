# DPL Blueprint — Single Source of Governance

This folder is the **authoritative blueprint** for Data Party Logistics (DPL).
From now on, **every change, addition, or removal is documented here** before or
alongside the work. If a decision is not written down here, it did not happen.

## How to use this folder

| When you… | Do this |
|---|---|
| Change scope or requirements | Update `01-PRD.md` |
| Change how the system is built | Update `02-ARCHITECTURE.md` |
| Plan or finish a unit of work | Update `03-PROJECT-PLAN.md` |
| Touch the model or measure the system | Update `04-PERFORMANCE-EVALUATION.md` |
| Add/remove a file, dir, or dependency | Add a row to `05-CLEANUP-PLAN.md` |
| Make ANY notable change | Add a dated entry to `06-CHANGELOG.md` |

## The documents

1. **[01-PRD.md](01-PRD.md)** — what we're building and why. Product requirements.
2. **[02-ARCHITECTURE.md](02-ARCHITECTURE.md)** — design doc. Current (v1.1) state + target (v1.2).
3. **[03-PROJECT-PLAN.md](03-PROJECT-PLAN.md)** — the ordered action list and roadmap.
4. **[04-PERFORMANCE-EVALUATION.md](04-PERFORMANCE-EVALUATION.md)** — model + system + cost metrics.
5. **[05-CLEANUP-PLAN.md](05-CLEANUP-PLAN.md)** — exact removal of dead code/deps to reach a clean state.
6. **[06-CHANGELOG.md](06-CHANGELOG.md)** — running, dated log of every change.

## The one rule

> The simplest system that is reproducible, tested, observed, and self-updating.
> Match architecture to scale. No tool enters the stack without a documented reason here.

## Project facts (do not re-derive)

| Fact | Value |
|---|---|
| AWS region | `eu-west-3` |
| AWS profile | `dpl` |
| Data bucket | `dpl-serverless-pilot-861276086413-pilot-data` |
| Athena database | `dpl_pilot` |
| Stack name | `dpl-serverless-pilot` |
| Paradigm | **Lambda + Athena + SAM only** (dbt/Prefect/Postgres were dropped for cost) |

_Last updated: 2026-06-09_
