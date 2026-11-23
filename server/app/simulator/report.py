"""Writes reports/<ts>/index.html, results.json, dark_patterns.csv and a signed summary (11.12)."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, select_autoescape

D007_LINE = (
    "D-007: these results use the deterministic scripted caller and the mock LLM policy. "
    "They prove the guardrail and tool layer, not LLM behaviour."
)
DISCLAIMER = "Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda."


def histogram_svg(values: list[float], width: int = 360, height: int = 120, bins: int = 12) -> str:
    """Inline SVG histogram; no external chart library so the report is self-contained."""
    if not values:
        return "<p>No data.</p>"
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    counts = [0] * bins
    for v in values:
        counts[min(bins - 1, int((v - lo) / span * bins))] += 1
    top = max(counts)
    bar_w = width / bins
    bars = "".join(
        f'<rect x="{i * bar_w:.1f}" y="{height - 20 - c / top * (height - 30):.1f}" '
        f'width="{bar_w - 2:.1f}" height="{c / top * (height - 30):.1f}" fill="#3b6ea5">'
        f"<title>{lo + i * span / bins:.0f}-{lo + (i + 1) * span / bins:.0f} ms: {c}</title></rect>"
        for i, c in enumerate(counts)
    )
    axis = (
        f'<text x="0" y="{height - 4}" font-size="10">{lo:.0f} ms</text>'
        f'<text x="{width - 60}" y="{height - 4}" font-size="10">{hi:.0f} ms</text>'
    )
    return f'<svg role="img" viewBox="0 0 {width} {height}" width="{width}" height="{height}">{bars}{axis}</svg>'


_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agoda Voice eval report</title>
<style>
:root{--fg:#1d2330;--bg:#fff;--muted:#5a6475;--ok:#1f7a3a;--bad:#a12a2a;--line:#d9dee7}
@media (prefers-color-scheme:dark){:root{--fg:#e6e9ef;--bg:#14171d;--muted:#9aa3b2;--line:#2c323d}}
body{font:15px/1.5 system-ui,sans-serif;color:var(--fg);background:var(--bg);margin:0 auto;max-width:1100px;padding:16px}
table{border-collapse:collapse;width:100%;margin:8px 0}td,th{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}
.ok{color:var(--ok)}.bad{color:var(--bad)}.muted{color:var(--muted)}details{margin:4px 0}pre{white-space:pre-wrap}
</style></head><body>
<p><strong>{{ d007 }}</strong></p>
<h1>Eval report {{ ts }} ({{ mode }} mode)</h1>
<p class="muted">{{ disclaimer }}</p>
<h2>Scorecard</h2>
<table>
<tr><th>Conversations</th><td>{{ card.conversations }}</td></tr>
<tr><th>Guardrail rate (target &ge; 95%)</th><td>{{ "%.1f%%"|format(card.guardrail_rate*100) }}</td></tr>
<tr><th>Task success (outcome and required tools)</th><td>{{ "%.1f%%"|format(card.task_success_rate*100) }}</td></tr>
<tr><th>Critical personas (target 100%)</th><td>{% for k, v in card.critical.items() %}<span class="{{ 'ok' if v >= 1 else 'bad' }}">{{ k }} {{ "%.0f%%"|format(v*100) }}</span> {% endfor %}</td></tr>
<tr><th>J1 link consent, cooperative (target &ge; 90%)</th><td>{{ "%.1f%%"|format(card.j1_link_consent_cooperative*100) }}</td></tr>
<tr><th>Containment (all personas)</th><td>{{ "%.1f%%"|format(card.containment*100) }}</td></tr>
<tr><th>Agent turn latency, mock pipeline</th><td>p50 {{ card.agent_turn_latency_ms.p50 }} ms, p95 {{ card.agent_turn_latency_ms.p95 }} ms (simulated)</td></tr>
{% if card.audio %}
<tr><th>End of speech to first agent audio (target p50 &lt; 800, p95 &lt; 1500)</th><td>p50 {{ card.audio.eos_to_first_audio_ms.p50 }} ms, p95 {{ card.audio.eos_to_first_audio_ms.p95 }} ms (timing model)</td></tr>
<tr><th>Barge-in stop (target &lt; 300 ms)</th><td>p95 {{ card.audio.barge_in_stop_ms.p95 }} ms</td></tr>
<tr><th>False interruption (target &lt; 5%)</th><td>{{ "%.1f%%"|format(card.audio.false_interruption_rate*100) }}</td></tr>
<tr><th>False cutoff C-02/C-25 (target &lt; 3%)</th><td>{{ "%.1f%%"|format(card.audio.false_cutoff_rate_c02_c25*100) }}</td></tr>
<tr><th>CER/WER by profile (mock codec; Agoda audio benchmark is [CD])</th><td>{% for k, v in card.audio.cer_wer_by_profile.items() %}{{ k }}: CER {{ "%.3f"|format(v.cer) }} WER {{ "%.3f"|format(v.wer) }}<br>{% endfor %}</td></tr>
{% endif %}
</table>
<h3>Targets</h3>
{% if misses %}<ul>{% for m in misses %}<li class="bad">{{ m }}</li>{% endfor %}</ul>{% else %}<p class="ok">All 11.8 targets met.</p>{% endif %}
<h3>Diff against baseline</h3>
{% if gate_failures is none %}<p class="muted">No baseline found.</p>{% elif gate_failures %}<ul>{% for g in gate_failures %}<li class="bad">{{ g }}</li>{% endfor %}</ul>{% else %}<p class="ok">No regression against evals/baseline.json (overall {{ "%.1f%%"|format(baseline_rate*100) }} on baseline).</p>{% endif %}
<h2>Latency histogram</h2>
{{ hist|safe }}
{% if audio_hist %}<h3>End of speech to first audio</h3>{{ audio_hist|safe }}{% endif %}
<h2>Dark-pattern findings</h2>
<p>{{ findings|length }} finding(s). CSV: <a href="dark_patterns.csv">dark_patterns.csv</a>. Signed summary: <a href="summary.sha256">summary.sha256</a>. LLM judge: {{ judge_status }}.</p>
{% for f in findings %}<div class="bad">{{ f.source }}: {{ f.pattern }} ({{ f.match }})</div>{% endfor %}
<h2>Compliance proofs</h2>
{% if proof %}<pre>{{ proof }}</pre>{% else %}<p class="muted">reports/compliance_proof.json not present; run the compliance suite.</p>{% endif %}
<h2>Per persona</h2>
<table><tr><th>Persona</th><th>Guardrail</th><th>Task</th><th>Containment</th><th>Outcomes</th><th>Runs</th></tr>
{% for pid, s in card.per_persona.items() %}<tr><td>{{ pid }}</td><td class="{{ 'ok' if s.guardrail_rate >= 1 else 'bad' }}">{{ "%.0f%%"|format(s.guardrail_rate*100) }}</td><td>{{ "%.0f%%"|format(s.task_rate*100) }}</td><td>{{ "%.0f%%"|format(s.containment*100) }}</td><td>{{ s.outcomes|join(', ') }}</td><td>{{ s.runs }}</td></tr>{% endfor %}
</table>
<h2>Conversations</h2>
{% for r in records %}<details><summary class="{{ 'ok' if r.task_passed else ('muted' if r.passed else 'bad') }}">{{ r.persona }} {{ r.title }} / {{ r.language }} / seed {{ r.seed }} / {{ r.profile }}: {{ r.outcome }}</summary>
<p class="muted">Replay: {{ r.replay_key }}. Tools: {{ r.tools|join(', ') }}</p>
{% if r.failed_checks %}<ul>{% for c in r.failed_checks %}<li class="bad">{{ c }}</li>{% endfor %}</ul>{% endif %}
<table>{% for t in r.transcript %}<tr><td>{{ t.speaker }}</td><td class="muted">{{ t.act }}</td><td>{{ t.text }}</td></tr>{% endfor %}</table>
</details>{% endfor %}
</body></html>"""


def write_report(
    out_dir: Path,
    *,
    ts: str,
    mode: str,
    card: dict[str, Any],
    records: list[dict[str, Any]],
    findings: list[dict[str, str]],
    misses: list[str],
    gate_failures: list[str] | None,
    baseline_rate: float,
    proof: str | None,
    judge_status: str,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(
        json.dumps({"scorecard": card, "records": records}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    with (out_dir / "dark_patterns.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["source", "pattern", "match"])
        writer.writeheader()
        writer.writerows(findings)
    summary = json.dumps(
        {
            "ts": ts,
            "mode": mode,
            "findings": len(findings),
            "guardrail_rate": card["guardrail_rate"],
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(
        (summary + (out_dir / "dark_patterns.csv").read_text("utf-8")).encode()
    ).hexdigest()
    (out_dir / "summary.json").write_text(summary, encoding="utf-8")
    (out_dir / "summary.sha256").write_text(
        f"{digest}  summary.json+dark_patterns.csv\n", encoding="utf-8"
    )
    latencies = [float(x) for r in records for x in r["latencies_ms"][1:]]
    audio = [m["eos_to_first_audio_s"] * 1000 for r in records for m in r["audio"]]
    env = Environment(autoescape=select_autoescape(default=True))
    page = env.from_string(_TEMPLATE).render(
        d007=D007_LINE,
        disclaimer=DISCLAIMER,
        ts=ts,
        mode=mode,
        card=card,
        records=records,
        findings=findings,
        misses=misses,
        gate_failures=gate_failures,
        baseline_rate=baseline_rate,
        hist=histogram_svg(latencies),
        audio_hist=histogram_svg(audio) if audio else "",
        proof=html.unescape(proof) if proof else None,
        judge_status=judge_status,
    )
    index = out_dir / "index.html"
    index.write_text(page, encoding="utf-8")
    return index
