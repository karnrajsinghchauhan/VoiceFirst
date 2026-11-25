"""Dispatcher process: `python -m app.wiring.run_dispatcher`. One replica keeps attempt caps exact."""

from __future__ import annotations

import time

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.wiring.main import build_dispatcher, build_runtime

# Short enough that a dropped queue after the kill switch is seen within one tick.
TICK_SECONDS = 2.0


def main() -> None:
    configure_logging()
    dispatcher = build_dispatcher(build_runtime(get_settings()))
    log = get_logger(__name__)
    while True:
        results = dispatcher.run_due()
        if results:
            log.info("dispatched", extra={"count": len(results)})
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main()
