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


def render_markdown(report_md: str) -> str:
    """Render the report markdown to HTML; escape-and-<br> only if the
    markdown package is unavailable (that path produces literal ## and **
    in the PDF, so it is strictly a last resort)."""
    try:
        import markdown
    except ImportError:
        escaped = html.escape(report_md)
        return escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>\n")
    return markdown.markdown(
        report_md,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )


def strip_duplicate_header(report_md: str, title: str) -> str:
    """The generator renders its own <h1> title and verdict badge, so drop a
    leading '# Title' and '**Verdict:** ...' from the report markdown to avoid
    showing both on page 1."""
    lines = report_md.lstrip().split("\n")
    while lines and (
        re.match(r"^#\s+\S", lines[0])
        or re.match(r"^\*\*Verdict:?\*\*", lines[0], re.IGNORECASE)
        or not lines[0].strip()
    ):
        lines.pop(0)
    return "\n".join(lines)


def write_html(title: str, report_md: str, verdict: str) -> str:
    body = render_markdown(strip_duplicate_header(report_md, title))
    html_text = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>{t}</title>"
        "<style>@page{{margin:2cm 1.8cm;}}"
        "body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:11.5pt;line-height:1.6;color:#1a1a1a;margin:0;}}"
        "h1{{font-size:18pt;border-bottom:2px solid {vc};padding-bottom:6px;}}"
        "h2{{font-size:13pt;margin-top:18pt;color:#112;border-bottom:1px solid #e3e7ec;padding-bottom:3px;}}"
        "h3{{font-size:11.5pt;margin-top:14pt;color:#223;}}"
        "table{{border-collapse:collapse;width:100%;margin:12pt 0;font-size:10pt;page-break-inside:auto;}}"
        "tr{{page-break-inside:avoid;}}"
        "th{{background:#f4f6f8;text-align:left;border:1px solid #d4dce6;padding:6px 8px;}}"
        "td{{border:1px solid #d4dce6;padding:6px 8px;vertical-align:top;}}"
        "ul,ol{{margin:6pt 0;padding-left:22pt;}}"
        "li{{margin:2pt 0;}}"
        "code{{font-family:Consolas,Menlo,monospace;font-size:9.5pt;background:#f4f6f8;padding:1px 4px;border-radius:3px;}}"
        "pre{{background:#f4f6f8;border:1px solid #e3e7ec;border-radius:4px;padding:8px 10px;overflow-wrap:break-word;white-space:pre-wrap;page-break-inside:avoid;}}"
        "pre code{{background:none;padding:0;}}"
        "blockquote{{border-left:3px solid #d4dce6;margin:10pt 0;padding:2pt 12pt;color:#445;}}"
        "hr{{border:none;border-top:1px solid #e3e7ec;margin:14pt 0;}}"
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
            [
                edge,
                "--headless",
                "--disable-gpu",
                # both spellings so old and new Edge builds skip the
                # default date/URL header and footer Chromium prints
                "--no-pdf-header-footer",
                "--print-to-pdf-no-header",
                "--print-to-pdf=" + pdf_path,
                html_path,
            ],
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
