"""Writes the API's OpenAPI document to the given path as YAML. Run from server/ with uv.

The app is built with stub ports: the document depends only on routes and
models, never on what the ports return.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from app.api.app import create_app
from app.api.stubs import build_stub_deps
from app.core.bus import MemoryBus
from app.core.clock import SystemClock
from app.core.config import Settings
from app.core.db import make_engine, make_session_factory


def main(out: Path) -> None:
    settings = Settings(environment="test", database_url="sqlite://")
    factory = make_session_factory(make_engine(settings.database_url))
    app = create_app(build_stub_deps(settings, factory, MemoryBus(), SystemClock()))
    out.write_text(yaml.safe_dump(app.openapi(), sort_keys=True, allow_unicode=True))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
