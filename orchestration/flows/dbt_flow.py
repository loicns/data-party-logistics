"""Hourly dbt transformation pipeline."""

import subprocess
from pathlib import Path

from prefect import flow, get_run_logger, task

# We find the absolute path to your dbt 'warehouse' directory
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent / "warehouse"


@task(retries=2, retry_delay_seconds=30, tags=["dbt", "load"])
def load_raw_to_postgres() -> dict[str, bool]:
    log = get_run_logger()

    sources = {
        "ais": {"table": "raw_ais_positions", "prefix": "raw/source=ais/"},
        "weather": {
            "table": "raw_weather_observations",
            "prefix": "raw/source=weather/",
        },
    }

    results = {}
    for source_name, config in sources.items():
        log.info(f"Loading {source_name} into {config['table']}...")

        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "ingestion.loaders.s3_to_postgres",
                    "--table",
                    config["table"],
                    "--prefix",
                    config["prefix"],
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            log.info(f"Successfully loaded {source_name}:\n{result.stdout}")
            results[source_name] = True

        except subprocess.CalledProcessError as e:
            log.error(f"Failed to load {source_name}. Error:\n{e.stderr}")
            results[source_name] = False

    return results


@task(retries=1, retry_delay_seconds=60, tags=["dbt", "build"])
def run_dbt_build() -> bool:
    log = get_run_logger()
    log.info("Running dbt build...")

    # We execute 'uv run dbt build' via the terminal
    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--project-dir", str(DBT_PROJECT_DIR)],
        capture_output=True,
        text=True,
    )

    log.info(result.stdout)
    if result.returncode != 0:
        log.error(f"dbt build FAILED:\n{result.stderr}")
        return False
    return True


@task(tags=["dbt", "freshness"])
def check_dbt_freshness() -> bool:
    log = get_run_logger()
    log.info("Checking dbt source freshness...")

    result = subprocess.run(
        [
            "uv",
            "run",
            "dbt",
            "source",
            "freshness",
            "--project-dir",
            str(DBT_PROJECT_DIR),
        ],
        capture_output=True,
        text=True,
    )

    log.info(result.stdout)
    if result.returncode != 0:
        log.warning(f"dbt freshness check FAILED:\n{result.stderr}")
        return False
    return True


@flow(name="hourly-dbt-flow", log_prints=True)
def hourly_dbt_flow() -> dict:
    log = get_run_logger()
    log.info("Starting hourly dbt flow")

    # 1. Load data from S3 to Postgres
    load_results = load_raw_to_postgres()

    # 2. Transform the data in Postgres using dbt
    dbt_success = run_dbt_build()

    # 3. Check if the source data is arriving on time
    freshness_ok = check_dbt_freshness()

    return {"load": load_results, "build": dbt_success, "freshness": freshness_ok}


if __name__ == "__main__":
    hourly_dbt_flow()
