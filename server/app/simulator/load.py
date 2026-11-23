"""`make load`: N concurrent mock sessions (11.10). Writes reports/load/<ts>.json.

LiveKit 1.8.13 ships no load-test tool for this text/mock pipeline, so this is
the asyncio harness the brief allows. Sessions run on worker threads
(the engine is synchronous); CPU and RSS per session feed the M10 sizing.
With mock providers this measures orchestration cost only: real STT/TTS/LLM
work happens in the providers' processes, not here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import resource
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.simulator.assertions import check_run, guardrail_pass
from app.simulator.caller import load_personas
from app.simulator.scenario import run_text

REPORT_DIR = Path(__file__).resolve().parents[3] / "reports" / "load"


async def run_load(sessions: int) -> dict[str, Any]:
    settings = Settings(environment="test", database_url="sqlite://")
    personas = load_personas()
    loop = asyncio.get_running_loop()
    start_cpu = resource.getrusage(resource.RUSAGE_SELF)
    start = time.perf_counter()

    def one(i: int) -> tuple[bool, float]:
        persona = personas[i % len(personas)]
        t0 = time.perf_counter()
        run = run_text(settings, persona, persona.languages[i % len(persona.languages)], i)
        return guardrail_pass(check_run(run)), time.perf_counter() - t0

    with ThreadPoolExecutor(max_workers=sessions) as pool:
        results = await asyncio.gather(
            *(loop.run_in_executor(pool, one, i) for i in range(sessions))
        )
    wall = time.perf_counter() - start
    end_cpu = resource.getrusage(resource.RUSAGE_SELF)
    cpu = (end_cpu.ru_utime - start_cpu.ru_utime) + (end_cpu.ru_stime - start_cpu.ru_stime)
    durations = sorted(d for _, d in results)
    return {
        "sessions": sessions,
        "concurrency": sessions,
        "wall_s": round(wall, 3),
        "cpu_s_total": round(cpu, 3),
        "cpu_ms_per_session": round(cpu / sessions * 1000, 2),
        "peak_rss_mb": round(end_cpu.ru_maxrss / 1024, 1),
        "rss_mb_per_session_upper_bound": round(end_cpu.ru_maxrss / 1024 / sessions, 2),
        "session_s_p50": round(durations[len(durations) // 2], 4),
        "session_s_p95": round(durations[int(0.95 * (len(durations) - 1))], 4),
        "guardrail_pass_rate": sum(ok for ok, _ in results) / sessions,
        "note": "mock providers; orchestration cost only (see module docstring)",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=int, default=200)
    args = parser.parse_args()
    report = asyncio.run(run_load(args.sessions))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    print(f"report: {path}")
    if report["guardrail_pass_rate"] < 1.0:
        raise SystemExit("guardrail failures under load")


if __name__ == "__main__":
    main()
