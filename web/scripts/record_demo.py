"""Records the six demo runs from the engine into JSON the public site replays in mock mode.

Run from server/: `uv run python ../web/scripts/record_demo.py ../web/src/content/demo-runs`
(or `npm run record:demo` from web/). Re-run whenever prompts change. It calls the same
DemoService that serves /demo, so a recorded run and a live run come from one code path.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import get_args

from app.api.ports import DemoScenario
from app.demo.service import DemoService
from app.demo.settings import DemoSettings


def main(out_dir: Path) -> None:
    demo = DemoService(DemoSettings())
    for scenario in get_args(DemoScenario):
        run = demo.run(scenario).model_dump(mode="json")
        run["run_id"] = f"rec_{scenario}"
        run["recorded_at"] = date.today().isoformat()
        (out_dir / f"{scenario}.json").write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
