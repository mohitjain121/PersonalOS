"""Offline PDF fallback using headless Edge HTML→PDF, with a final plain-text fallback."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

PDF_OUTPUT_DIR = os.path.expanduser("~/.hermes/venture-studio/reports")
VERDICT_LABEL = {
    "strong": "STRONG SIGNAL",
    "promising": "PROMISING",
    "weak": "WEAK SIGNAL",
    "dead": "DEAD END",
}
VERDICT_COLOR = {
    "strong": "#22c55e",
    "promising": "#eab308",
    "weak": "#f97316",
    "dead": "#ef4444",
}


def write_html(title: str, report_md: str, verdict: str) -> str:
    escaped = html.escape(report_md)
    body = escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>\n")
    html_text = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>{t}</title>"
        "<style>body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:11.5pt;line-height:1.6;color:#1a1a1a;padding:28px;}}"
        "h1{{font-size:18pt;border-bottom:2px solid {vc};padding-bottom:6px;}}"
        "h2{{font-size:13pt;margin-top:18pt;color:#112;}}"
        "h3{{font-size:11.5pt;margin-top:14pt;color:#223;}}"
        "table{{border-collapse:collapse;width:100%;margin:12pt 0;}}"
        "th{{background:#f4f6f8;text-align:left;border:1px solid #d4dce6;padding:6px 8px;}}"
        "td{{border:1px solid #d4dce6;padding:6px 8px;}}"
        ".badge{{display:inline-block;padding:5px 10px;background:{vc};color:#fff;font-size:10pt;border-radius:3px;margin:8px 0;}}</style></head>"
        "<body><h1>{t}</h1><div class='badge'>{vl}</div><p class='meta'>Generated {d}</p>{body}</body></html>"
    ).format(
        t=html.escape(title),
        vl=VERDICT_LABEL.get(verdict, "UNKNOWN"),
        vc=VERDICT_COLOR.get(verdict, "#6b7280"),
        d=datetime.now().strftime("%d %b %Y"),
        body=body,
    )
    out_dir = PDF_OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "{d}-{s}-local.html".format(
        d=datetime.now().strftime("%Y%m%d"),
        s=re.sub(r"[^a-zA-Z0-9]+", "-", title)[:60],
    ))
    Path(path).write_text(html_text, encoding="utf-8")
    return path


def render_with_headless_edge(html_path: str, pdf_path: str) -> bool:
    possible_edge = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    edge = next((p for p in possible_edge if os.path.exists(p)), None)
    if not edge:
        return False
    try:
        subprocess.run(
            [edge, "--headless", "--disable-gpu", "--print-to-pdf=" + pdf_path, html_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1024
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--report-md", required=True)
    parser.add_argument("--verdict", default="uncertain")
    parser.add_argument("--domain", default="other")
    parser.add_argument("--idea-id", required=True)
    parser.add_argument("--output-dir", default=PDF_OUTPUT_DIR)
    args = parser.parse_args()

    report_content = args.report_md
    if os.path.exists(args.report_md):
        report_content = Path(args.report_md).read_text(encoding="utf-8")

    slug = "".join(c if c.isalnum() else "-" for c in args.title)[:60]
    date_slug = datetime.now().strftime("%Y%m%d")
    base_name = "{d}-{s}-{i}".format(d=date_slug, s=slug, i=args.idea_id[:8])
    out_path = os.path.join(args.output_dir, base_name + ".pdf")

    html_path = write_html(args.title, report_content, args.verdict)

    if render_with_headless_edge(html_path, out_path):
        try:
            os.remove(html_path)
        except OSError:
            pass
        print(json.dumps({"pdf_path": out_path, "fallback": "edge"}))
        return

    try:
        os.remove(html_path)
    except OSError:
        pass

    txt_path = os.path.join(args.output_dir, base_name + ".txt")
    Path(txt_path).write_text(report_content, encoding="utf-8")
    print(json.dumps({"pdf_path": txt_path, "fallback": "txt"}))


if __name__ == "__main__":
    main()
