"""`make eval` / `make eval-audio` / `make report`.

Runs every persona x language x seed, writes reports/<ts>/index.html, and exits
non-zero if an 11.8 target is missed or the 11.9 regression gate fails against
evals/baseline.json. `--write-baseline` records the current scorecard as the baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

from judges.llm_judge import judge_status  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.simulator.caller import load_personas  # noqa: E402
from app.simulator.evaluate import (  # noqa: E402
    dark_pattern_findings,
    gate,
    run_suite,
    scorecard,
    targets,
)
from app.simulator.report import write_report  # noqa: E402

REPORTS = ROOT / "reports"
BASELINE = ROOT / "evals" / "baseline.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["text", "audio"], default="text")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument(
        "--report-only", action="store_true", help="re-render the latest results.json"
    )
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    personas = load_personas()
    if args.report_only:
        latest = sorted(p for p in REPORTS.glob("*/results.json"))
        if not latest:
            raise SystemExit("no previous results.json under reports/")
        data = json.loads(latest[-1].read_text(encoding="utf-8"))
        card, records = data["scorecard"], data["records"]
        mode = "audio" if "audio" in card else "text"
    else:
        settings = Settings(environment="test", database_url="sqlite://")
        runs = run_suite(settings, personas, args.seeds, args.mode)
        card = scorecard(runs, personas)
        records = [asdict(r) for r in runs]
        mode = args.mode
    findings = dark_pattern_findings_from(records)
    misses = targets(card)
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else None
    gate_failures = gate(card, baseline[mode]) if baseline and mode in baseline else None
    proof_path = REPORTS / "compliance_proof.json"
    index = write_report(
        REPORTS / f"{ts}-{mode}",
        ts=ts,
        mode=mode,
        card=card,
        records=records,
        findings=findings,
        misses=misses,
        gate_failures=gate_failures,
        baseline_rate=baseline[mode]["guardrail_rate"]
        if gate_failures is not None and baseline
        else 0.0,
        proof=proof_path.read_text(encoding="utf-8") if proof_path.exists() else None,
        judge_status=judge_status(),
    )
    if args.write_baseline:
        stored = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
        stored[mode] = {k: card[k] for k in ("guardrail_rate", "critical", "per_persona")}
        BASELINE.write_text(json.dumps(stored, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in card.items() if k != "per_persona"}, indent=1))
    print(f"report: {index}")
    problems = misses + (gate_failures or []) + [f"dark pattern: {f}" for f in findings]
    for p in problems:
        print(f"FAIL {p}", file=sys.stderr)
    return 1 if problems else 0


def dark_pattern_findings_from(records: list[dict[str, object]]) -> list[dict[str, str]]:
    from app.simulator.evaluate import ConversationRecord

    return dark_pattern_findings([ConversationRecord(**r) for r in records])  # type: ignore[arg-type]


if __name__ == "__main__":
    raise SystemExit(main())
