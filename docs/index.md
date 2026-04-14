# Data Party Logistics

A Machine Learning platform that predicts **vessel ETAs** and **port congestion** using live global shipping data.

## What this project does

| Capability | Description |
|---|---|
| **Real-time data ingestion** | Streams live AIS vessel positions + trade flows + weather + news |
| **Star-schema warehouse** | Clean dimensional model in PostgreSQL with dbt |
| **ML prediction** | ETA regression + congestion classification with XGBoost/LightGBM |
| **Production API** | FastAPI service deployed on AWS ECS Fargate |
| **Drift monitoring** | Evidently reports detect when the model needs retraining |
| **AI news agent** | LangGraph agent extracts disruption events from global news |

## Quick links

- [Live Dashboard](#) *(coming Week 8)*
- [API Documentation](#) *(coming Week 7)*
- [GitHub Repository](https://github.com/loicns/data-party-logistics)

## Project status

Currently in **Week 1** — setting up foundations.

---

*Built as a portfolio project demonstrating end-to-end ML engineering on real-world supply chain data.*
