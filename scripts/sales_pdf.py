"""Renders docs/sales/*.md to docs/sales/pdf/*.pdf.

Run from the repo root: `uv run --project server --with markdown python scripts/sales_pdf.py`.
Markdown becomes standalone HTML here; web/scripts/print-html.mjs prints it with Chromium.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SALES = ROOT / "docs" / "sales"
CSS = """
body { font: 10.5pt/1.5 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #141414; }
h1 { font-size: 18pt; margin: 0 0 8pt; } h2 { font-size: 13pt; margin: 18pt 0 6pt; break-after: avoid; }
h3 { font-size: 11pt; margin: 12pt 0 4pt; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 9pt; break-inside: auto; }
th, td { border-bottom: 1px solid #dedad1; padding: 4pt 6pt; text-align: left; vertical-align: top; }
th { font-weight: 600; } tr { break-inside: avoid; }
pre { background: #f2f0eb; padding: 8pt; font-size: 8.5pt; white-space: pre-wrap; }
code { font-size: 9pt; } a { color: #1f4e5f; }
"""


def render(md_path: Path, html_dir: Path) -> Path:
    body = markdown.markdown(md_path.read_text(), extensions=["tables", "fenced_code"])
    html = html_dir / f"{md_path.stem}.html"
    html.write_text(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{md_path.stem}</title>'
        f"<style>{CSS}</style></head><body>{body}</body></html>"
    )
    return html


def main() -> None:
    out = SALES / "pdf"
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pairs: list[str] = []
        for md_path in sorted(SALES.glob("*.md")):
            pairs += [str(render(md_path, Path(tmp))), str(out / f"{md_path.stem}.pdf")]
        node = shutil.which("node")
        if node is None:
            raise FileNotFoundError("node is required to print the PDFs")
        # Arguments are paths this script built from files in the repo, never user input.
        subprocess.run([node, "scripts/print-html.mjs", *pairs], cwd=ROOT / "web", check=True)  # noqa: S603


if __name__ == "__main__":
    main()
