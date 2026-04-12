"""Smoke test — verifies the project imports and basic config loads."""


def test_import_config():
    """Config module loads without error."""
    from ingestion.config import Settings

    s = Settings()
    assert s.aws_region == "eu-west-3"


def test_project_structure():
    """Key packages are importable."""
    import ingestion
    import ingestion.clients
    import serving
    import agent

    assert True