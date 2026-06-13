import json
import logging
from pathlib import Path
from typing import Any

from models.training.predict import load_model, predict
from serverless.ports import PORTS

logger = logging.getLogger(__name__)


def refresh_predictions(output_path: Path) -> dict[str, Any]:
    """Score all configured ports and write dashboard predictions JSON."""
    model = load_model()
    results: dict[str, Any] = {}
    succeeded, failed = 0, 0

    for port_code in PORTS:
        try:
            results[port_code] = predict(model, port_code)
            succeeded += 1
        except Exception as exc:
            results[port_code] = None
            failed += 1
            logger.warning("prediction_failed port_code=%s error=%s", port_code, exc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    logger.info(
        "predictions_refreshed succeeded=%s failed=%s output_path=%s",
        succeeded,
        failed,
        output_path,
    )
    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    refresh_predictions(Path("dashboard-v2/public/predictions.json"))


if __name__ == "__main__":
    main()
