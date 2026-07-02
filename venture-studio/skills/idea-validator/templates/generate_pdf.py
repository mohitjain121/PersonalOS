"""
generate_pdf.py — Generates a formatted PDF validation report using WeasyPrint

Install: pip install weasyprint markdown
"""

import os
import sys
import json
import argparse
from datetime import datetime

try:
    from weasyprint import HTML, CSS
    import markdown
except ImportError:
    print(json.dumps({"error": "weasyprint or markdown not installed"}))
    sys.exit(1)

PDF_OUTPUT_DIR = os.path.expanduser("~/.hermes/venture-studio/reports")

VERDICT_LABEL = {
    "strong": "STRONG SIGNAL", "promising": "PROMISING",
    "weak": "WEAK SIGNAL", "dead": "DEAD END",
}

VERDICT_COLOR = {
    "strong": "#22c55e", "promising": "#eab308",
    "weak": "#f97316", "dead": "#ef4444",
}

PDF_CSS_TEMPLATE = """
@page {{
    size: A4; margin: 2cm;
    @top-left {{ content: "VENTURE STUDIO"; font-size: 8pt; color: #999; }}
    @top-right {{ content: "{date}"; font-size: 8pt; color: #999; }}
    @bottom-center {{ content: "Page " counter(page); font-size: 7pt; color: #999; }}
}}
body {{ font-family: Arial; font-size: 10pt; line-height: 1.6; color: #333; }}
h1 {{ font-size: 20pt; color: #1a1a1a; margin-bottom: 10pt; 
      border-bottom: 3px solid {verdict_color}; padding-bottom: 8pt; }}
h2 {{ font-size: 13pt; margin-top: 20pt; border-bottom: 1px solid #e0e0e0; }}
table {{ width: 100%; border-collapse: collapse; margin: 15pt 0; }}
th {{ background: #f5f5f5; border: 1pt solid #ddd; padding: 8pt; }}
td {{ border: 1pt solid #ddd; padding: 8pt; }}
.verdict-badge {{ background: {verdict_color}; color: white; 
                  padding: 6pt 12pt; border-radius: 3pt; }}
"""

def generate_pdf(title, report_md, verdict, domain, idea_id, output_dir=PDF_OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)
    
    date_slug = datetime.now().strftime("%Y%m%d")
    title_slug = "".join(c if c.isalnum() else "-" for c in title)[:50]
    filename = f"{date_slug}-{title_slug}-{idea_id[:8]}.pdf"
    output_path = os.path.join(output_dir, filename)
    
    verdict_color = VERDICT_COLOR.get(verdict, "#6b7280")
    verdict_label = VERDICT_LABEL.get(verdict, "UNKNOWN")
    
    css = PDF_CSS_TEMPLATE.format(
        verdict_color=verdict_color,
        date=datetime.now().strftime("%d %b %Y")
    )
    
    md_html = markdown.markdown(
        report_md,
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
    )
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head><body>
<h1>{title}</h1>
<div><span class="verdict-badge">{verdict_label}</span></div>
{md_html}
<hr><p style="text-align:center;font-size:8pt;color:#999;">
ID: {idea_id} · Hermes venture-studio</p>
</body></html>"""
    
    HTML(string=html).write_pdf(output_path, stylesheets=[CSS(string=css)])
    return output_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--report-md", required=True)
    parser.add_argument("--verdict", default="uncertain")
    parser.add_argument("--domain", default="other")
    parser.add_argument("--idea-id", required=True)
    parser.add_argument("--output-dir", default=PDF_OUTPUT_DIR)
    args = parser.parse_args()
    
    if os.path.exists(args.report_md):
        with open(args.report_md, 'r', encoding='utf-8') as f:
            report_content = f.read()
    else:
        report_content = args.report_md
    
    pdf_path = generate_pdf(
        args.title, report_content, args.verdict,
        args.domain, args.idea_id, args.output_dir
    )
    
    print(json.dumps({"pdf_path": pdf_path}))

if __name__ == "__main__":
    main()
