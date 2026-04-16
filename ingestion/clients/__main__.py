"""Allow running ingestion clients as modules.

WHY THIS FILE: Running `python -m ingestion.clients.ais_stream` invokes
this __main__.py first, then the module's own __main__ block.
The module form (-m flag) ensures the ingestion package is on sys.path,
making `from ingestion.config import settings` work correctly regardless
of what directory you run the command from.

Example: uv run python -m ingestion.clients.ais_stream
"""
