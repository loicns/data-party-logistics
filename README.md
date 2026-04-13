# Data Party Logistics

An ML project building a global port congestion and vessel ETA intelligence platform from free public data.

**Status:** Week 1 — foundations.

## What this will become

A production-grade ML platform that:
- Ingests live AIS vessel messages, global trade flows, weather, and disruption news
- Predicts vessel ETAs and port congestion
- Serves predictions via a FastAPI service on AWS
- Monitors data drift with Evidently
- Enriches unstructured news with a LangGraph-based agent

## Tech stack (planned)

Python · uv · dbt · Postgres + PostGIS · Prefect · Feast · MLflow · XGBoost · LightGBM · FastAPI · Docker · AWS ECS Fargate · Terraform · LangGraph · Anthropic Claude

## Documentation

Live site: *(will be added in Week 1 Step 04)*

## License

MIT — see [LICENSE](LICENSE).
