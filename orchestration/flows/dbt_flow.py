"""Hourly dbt transformation pipeline."""

import subprocess
from pathlib import Path
from typing import Any

from prefect import flow, get_run_logger, task

# We find the absolute path to your dbt 'warehouse' directory
DBT_PROJECT_DIR = Path(__file__).parent.parent.parent / "warehouse"


def classify_loader_output(stdout: str) -> str:
    """Translate loader stdout into a simple operational status.

    WHY THIS HELPER EXISTS:
    The S3 loader now has three valid outcomes:
    - it loaded new files
    - it found no new files
    - it failed

    Prefect operators should be able to tell those cases apart quickly in logs
    and in the returned flow payload. A tiny helper keeps that interpretation
    logic in one place instead of scattering string checks through the task body.
    """
    if "no_new_files_found" in stdout:
        return "no_new_files"
    if "load_complete" in stdout:
        return "loaded_new_files"
    return "completed"


@task(retries=2, retry_delay_seconds=30, tags=["dbt", "load"])
def load_raw_to_postgres() -> dict[str, dict[str, Any]]:
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
        )

        if result.returncode != 0:
            log.error(f"Failed to load {source_name}. Error:\n{result.stderr}")
            results[source_name] = {
                "ok": False,
                "status": "failed",
                "table": config["table"],
                "prefix": config["prefix"],
            }
            continue

        status = classify_loader_output(result.stdout)
        if status == "no_new_files":
            log.info(
                "No new files found for %s under %s. Raw load skipped cleanly.",
                source_name,
                config["prefix"],
            )
        else:
            log.info(f"Loader output for {source_name}:\n{result.stdout}")

        results[source_name] = {
            "ok": True,
            "status": status,
            "table": config["table"],
            "prefix": config["prefix"],
        }

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

    loaded_sources = [
        name
        for name, result in load_results.items()
        if result["status"] == "loaded_new_files"
    ]
    idle_sources = [
        name
        for name, result in load_results.items()
        if result["status"] == "no_new_files"
    ]
    failed_sources = [name for name, result in load_results.items() if not result["ok"]]

    # This concise summary makes Prefect runs easier to scan:
    # operators can immediately see whether the run processed fresh input,
    # merely confirmed nothing new arrived, or hit a real ingestion problem.
    log.info(
        "Raw load summary | loaded=%s | no_new_files=%s | failed=%s",
        loaded_sources or ["none"],
        idle_sources or ["none"],
        failed_sources or ["none"],
    )

    return {"load": load_results, "build": dbt_success, "freshness": freshness_ok}


if __name__ == "__main__":
    hourly_dbt_flow()
