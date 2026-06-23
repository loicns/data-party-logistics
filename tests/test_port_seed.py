"""Guard the UN/LOCODE seed that the ingestion Lambdas load at import time.

commit 60d2f78 deleted warehouse/seeds/un_locode.csv during the dbt->Athena
refactor, but ais_stream/weather still read it to build port bounding boxes.
The Lambdas then failed at import (FileNotFoundError) and AIS ingestion went
dark for ~2 days. These tests fail loudly if the seed ever goes missing again
or stops covering the pilot ports.
"""

from __future__ import annotations

from pathlib import Path

from ingestion.port_loader import load_port_bboxes, load_port_centers

SEED = Path(__file__).resolve().parents[1] / "warehouse" / "seeds" / "un_locode.csv"


def test_seed_file_exists() -> None:
    assert SEED.exists(), (
        f"UN/LOCODE seed missing at {SEED} — ingestion Lambdas will "
        "FileNotFoundError at import. Restore it and keep it tracked in git."
    )


def test_seed_builds_bounding_boxes() -> None:
    # ais_stream subscribes to these boxes; an empty list = no AIS captured.
    bboxes = load_port_bboxes(SEED)
    assert len(bboxes) > 1000, (
        f"Seed produced only {len(bboxes)} bounding boxes — looks truncated; "
        "the real UN/LOCODE export yields thousands of maritime ports."
    )


def test_seed_resolves_full_locode_dataset() -> None:
    # Sanity that we restored the real seed, not a stub.
    centers = load_port_centers(SEED)
    assert len(centers) > 1000, (
        f"Seed resolved only {len(centers)} port centers — looks truncated."
    )


def test_seed_covers_all_pilot_ports() -> None:
    # Every port the pilot scores must have its own AIS bounding box.
    # CNSHA/GBFXT/TWKHH were missing from the upstream export and were added
    # manually — if this regresses, those ports silently lose AIS coverage.
    pilot = [
        "NLRTM",
        "SGSIN",
        "USLAX",
        "CNSHA",
        "DEHAM",
        "BEANR",
        "GBFXT",
        "AEDXB",
        "USNYC",
        "TWKHH",
    ]
    centers = load_port_centers(SEED)
    missing = [code for code in pilot if code not in centers]
    assert not missing, f"Seed is missing pilot ports: {missing}"


def test_seed_can_build_only_pilot_bounding_boxes() -> None:
    # AISStream closes connections when we send the whole global LOCODE set.
    # The serverless subscription must stay scoped to pilot ports.
    pilot = {
        "NLRTM",
        "SGSIN",
        "USLAX",
        "CNSHA",
        "DEHAM",
        "BEANR",
        "GBFXT",
        "AEDXB",
        "USNYC",
        "TWKHH",
    }
    bboxes = load_port_bboxes(SEED, include_locodes=pilot)
    assert len(bboxes) == len(pilot)
