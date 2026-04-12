"""
Management command: generate the sample PDF for the author template pack.

Usage:
    python manage.py generate_sample_pdf

Writes template_pack/transact_sample_article.pdf — a fully rendered sample
article demonstrating every feature of the Trans/Act publication format:
inline markup, block quotations, footnotes, citations, figures, tables,
and bibliography.

This HTML is written directly (not through the LaTeX parser) so it reliably
represents what the published pipeline produces, independent of parser edge cases.

Run this command whenever the PDF stylesheet or this template is updated.

Note on rendering differences
------------------------------
The local LaTeX compilation you do in VS Code (pdflatex + arjournal.cls) uses
TeX's typesetting engine with Computer Modern fonts. The published article uses a
completely different pipeline: LaTeX source → canonical JSON → HTML → WeasyPrint
PDF. The two outputs will look different — that is intentional. This sample PDF
shows the PUBLISHED format that readers see, not the local compile format.
"""
import os
import sys

from django.core.management.base import BaseCommand
from django.conf import settings


# ── PDF stylesheet ────────────────────────────────────────────────────────────
# Mirrors apps/production/tasks.py. Keep in sync when updating the stylesheet.

_PDF_CSS = """
:root {
  --color-text: #1A1A1A;
  --color-muted: #6B6B6B;
  --color-accent: #E86B1F;
  --color-border: #E5E5E5;
}
@page {
  margin: 2.5cm 2cm 2.5cm 2cm;
  @bottom-center { content: counter(page); font-size: 9pt; color: #999; }
}
* { box-sizing: border-box; }
body {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 11pt;
  line-height: 1.65;
  color: #1A1A1A;
  margin: 0;
}
/* ── Sample notice banner ──────────────────────────────────────────────── */
.sample-banner {
  border: 2px solid #E86B1F;
  border-radius: 6px;
  padding: 16px 20px;
  margin-bottom: 2rem;
  background: #fff8f4;
  page-break-inside: avoid;
}
.sample-banner__label {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 8pt;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #E86B1F;
  margin: 0 0 6px;
}
.sample-banner__title {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 13pt;
  font-weight: bold;
  color: #1A1A1A;
  margin: 0 0 8px;
}
.sample-banner__body {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 9pt;
  color: #444;
  line-height: 1.6;
  margin: 0;
}
.sample-banner__files {
  margin: 8px 0 0;
  padding-left: 1.2em;
  font-family: Helvetica, Arial, sans-serif;
  font-size: 9pt;
  color: #555;
  line-height: 1.7;
}
.sample-banner__url {
  font-family: Courier, monospace;
  font-size: 8.5pt;
  color: #E86B1F;
}
/* ── Article header ────────────────────────────────────────────────────── */
.pdf-header {
  border-bottom: 2px solid #E86B1F;
  padding-bottom: 1.5rem;
  margin-bottom: 2rem;
}
.pdf-issue   { font-size: 9pt; color: #6B6B6B; margin-bottom: 0.4rem; }
.pdf-title   { font-size: 22pt; line-height: 1.2; margin-bottom: 0.5rem; font-weight: bold; }
.pdf-subtitle{ font-size: 13pt; color: #555; margin-bottom: 0.5rem; font-style: italic; }
.pdf-author  { font-size: 11pt; color: #444; font-family: Helvetica, Arial, sans-serif; }
/* ── Article body ──────────────────────────────────────────────────────── */
.article-body { margin: 0; }
.article-abstract {
  border-left: 3px solid #E86B1F;
  padding-left: 1rem;
  margin: 1.5rem 0;
}
.article-abstract h2 {
  font-size: 10pt;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6B6B6B;
  margin-bottom: 0.4rem;
}
.article-abstract p { font-size: 10pt; color: #444; }
.article-authors { font-size: 10pt; color: #6B6B6B; margin-bottom: 1rem; }
h1 { font-size: 16pt; margin: 2rem 0 0.8rem; }
h2 { font-size: 13pt; margin: 1.6rem 0 0.6rem; }
h3 { font-size: 11pt; margin: 1.2rem 0 0.4rem; }
p  { margin: 0 0 0.8rem; }
figure { margin: 1.5rem 0; text-align: center; }
figcaption { font-size: 9pt; color: #6B6B6B; margin-top: 0.4rem; font-style: italic; }
img { max-width: 100%; height: auto; }
table { width: 100%; border-collapse: collapse; margin: 1.2rem 0; font-size: 10pt; }
th { background: #f5f5f5; border-bottom: 2px solid #E5E5E5; padding: 0.4rem 0.6rem; text-align: left; }
td { border-bottom: 1px solid #E5E5E5; padding: 0.4rem 0.6rem; }
a  { color: #E86B1F; text-decoration: none; }
strong { font-weight: bold; }
em { font-style: italic; }
/* Blockquotes — 0.5 inch indent both sides, no quotation marks */
.article-blockquote {
  margin-left: 36pt;
  margin-right: 36pt;
  font-style: italic;
  color: #444;
}
.article-blockquote p { margin: 0; }
/* Footnotes — WeasyPrint float: footnote places them at page bottom */
.fn-wrap { display: inline; }
.fn-ref-num {
  font-size: 0.7em;
  vertical-align: super;
  color: #E86B1F;
  font-weight: bold;
  line-height: 0;
}
.fn-note {
  float: footnote;
  font-size: 9pt;
  color: #444;
  line-height: 1.4;
}
.fn-note__num { font-weight: bold; color: #E86B1F; margin-right: 0.2em; }
/* Hide the footnotes section — WeasyPrint handles footnotes via float: footnote */
.article-footnotes { display: none; }
/* Paragraph anchor numbers — used for reviewer targeting only, not displayed */
.para-num { display: none; }
/* Inline citations */
.article-cite { color: #1A1A1A; text-decoration: none; }
/* Keywords */
.article-keywords { font-size: 9pt; color: #6B6B6B; margin-bottom: 1.5rem; }
.keyword { margin-right: 0.3em; }
.keyword::after { content: ';'; }
.keyword:last-child::after { content: ''; }
/* Bibliography */
.article-bibliography {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #E5E5E5;
}
.article-bibliography h2 {
  font-size: 10pt;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6B6B6B;
  margin-bottom: 0.6rem;
}
.article-bibliography__list { list-style: none; padding: 0; margin: 0; }
.bibliography-item {
  font-size: 9pt;
  margin-bottom: 0.5rem;
  padding-left: 1.2em;
  text-indent: -1.2em;
  line-height: 1.45;
}
.bib-title { font-style: italic; }
/* Bookmarks for interactive PDF navigation */
h1 { bookmark-level: 1; bookmark-label: content(); }
h2 { bookmark-level: 2; bookmark-label: content(); }
h3 { bookmark-level: 3; bookmark-label: content(); }
/* Verbatim / inline code */
pre.article-verbatim {
  background: #f5f5f5; border: 1px solid #E5E5E5; border-radius: 3px;
  padding: 0.5rem 0.7rem; margin: 0.8rem 0;
  font-size: 8.5pt; line-height: 1.4; white-space: pre;
}
pre.article-verbatim code { background: none; padding: 0; font-size: inherit; }
code { font-family: Courier, 'Courier New', monospace; font-size: 0.88em;
       background: #f5f5f5; padding: 0.1em 0.2em; border-radius: 2px; }
/* Lists */
.article-list { margin: 0.5rem 0 0.8rem 1.4rem; padding: 0; }
.article-list li { margin-bottom: 0.25rem; line-height: 1.55; }
/* Description lists */
.article-dl { margin: 0.5rem 0 0.8rem; }
.article-dl dt { font-weight: bold; margin-top: 0.4rem; }
.article-dl dd { margin-left: 1.5rem; margin-bottom: 0.2rem; }
"""


# ── BibTeX helper ─────────────────────────────────────────────────────────────

def _parse_bib(bib_path) -> dict:
    """Minimal BibTeX parser — returns {citeKey: {title, year, authors, doi}}."""
    import re
    result = {}
    text = bib_path.read_text(encoding='utf-8')
    for entry_m in re.finditer(r'@\w+\{(\w+),(.*?)(?=\n@|\Z)', text, re.DOTALL):
        key = entry_m.group(1).strip()
        body = entry_m.group(2)

        def field(name, _body=body):
            m = re.search(
                rf'(?i){name}\s*=\s*(?:\{{((?:[^{{}}]|\{{[^{{}}]*\}})*)\}}|"([^"]*)")',
                _body,
            )
            if not m:
                return ''
            val = (m.group(1) or m.group(2) or '').strip()
            # Strip inner braces used for case protection
            val = re.sub(r'\{([^}]*)\}', r'\1', val)
            return val

        author_raw = field('author')
        authors = []
        if author_raw:
            for a in re.split(r'\s+and\s+', author_raw, flags=re.IGNORECASE):
                a = a.strip()
                if ',' in a:
                    last, first = a.split(',', 1)
                    a = f'{first.strip()} {last.strip()}'
                authors.append(a)

        result[key] = {
            'title': field('title'),
            'year': field('year'),
            'authors': authors,
            'doi': field('doi'),
        }
    return result





def _build_pdf_html(html_content: str, site_url: str) -> str:
    import html as _html
    download_url = f'{site_url}/download/template/'

    sample_banner = f"""<div class="sample-banner">
  <p class="sample-banner__label">Sample output &mdash; author template pack</p>
  <p class="sample-banner__title">This document shows how your submission will look after publication.</p>
  <p class="sample-banner__body">
    It was generated from the Trans/Act production pipeline (HTML + WeasyPrint renderer).
    Your submitted <code>.tex</code> file goes through the same process to produce the
    HTML article and this downloadable PDF. <strong>Note:</strong> the local PDF you
    compile from the same source in LaTeX (via pdflatex or VS&nbsp;Code) uses a
    completely different rendering engine and will look different. Both are correct.
    This document shows the <em>published</em> format that readers see.
  </p>
  <p class="sample-banner__body" style="margin-top:8px;">The template pack contains:</p>
  <ul class="sample-banner__files">
    <li><strong>arjournal.cls</strong> &mdash; document class with all custom macros</li>
    <li><strong>arjournal_template.tex</strong> &mdash; comprehensive tutorial; read this file to learn every feature</li>
    <li><strong>arjournal_references_template.bib</strong> &mdash; bibliography template with example entries</li>
    <li><strong>transact_sample_article.pdf</strong> &mdash; this document</li>
  </ul>
  <p class="sample-banner__body" style="margin-top:10px;">
    Download the latest template pack at any time:<br>
    <span class="sample-banner__url">{_html.escape(download_url)}</span>
  </p>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Trans/Act &mdash; Sample Article</title>
  <style>{_PDF_CSS}</style>
</head>
<body>
{sample_banner}

{html_content}
</body>
</html>"""


class Command(BaseCommand):
    help = (
        'Generate transact_sample_article.pdf in the template_pack directory. '
        'Run this whenever the PDF stylesheet or this command is updated.'
    )

    def handle(self, *args, **options):
        template_dir = settings.BASE_DIR / 'template_pack'
        out_path = template_dir / 'transact_sample_article.pdf'
        site_url = getattr(settings, 'SITE_URL', 'https://trans-act-journal.org').rstrip('/')

        # Parse the .tex template → canonical JSON → HTML
        from apps.documents.parsers.latex_parser import parse_latex
        from apps.documents.renderers.html_renderer import render_html

        tex_path = template_dir / 'arjournal_template.tex'
        self.stdout.write(f'Reading {tex_path} …')
        with open(tex_path, encoding='utf-8') as f:
            tex_source = f.read()

        meta = {
            'language': 'en',
            'article_type': 'Research Article',
        }
        self.stdout.write('Parsing LaTeX …')
        canonical = parse_latex(tex_source, meta)

        # Enrich bibliography items from the .bib file
        bib_path = template_dir / 'arjournal_references_template.bib'
        if bib_path.exists():
            bib_data = _parse_bib(bib_path)
            for item in canonical.get('citations', {}).get('items', []):
                ck = item.get('citeKey', '')
                if ck in bib_data:
                    item.update(bib_data[ck])
            for block in canonical.get('content', []):
                if block.get('type') == 'bibliography':
                    for item in block.get('items', []):
                        ck = item.get('citeKey', '')
                        if ck in bib_data:
                            item.update(bib_data[ck])

        self.stdout.write('Rendering HTML …')
        html_content = render_html(canonical)
        html_doc = _build_pdf_html(html_content, site_url)

        # On macOS + Homebrew, GLib/Pango libs live in /opt/homebrew/lib.
        if sys.platform == 'darwin':
            brew_lib = '/opt/homebrew/lib'
            dyld = os.environ.get('DYLD_LIBRARY_PATH', '')
            if brew_lib not in dyld:
                os.environ['DYLD_LIBRARY_PATH'] = f'{brew_lib}:{dyld}' if dyld else brew_lib

        self.stdout.write('Generating PDF with WeasyPrint…')
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_doc, base_url=str(template_dir)).write_pdf()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'WeasyPrint failed: {exc}'))
            self.stderr.write(
                'Make sure the OS libraries are installed:\n'
                '  macOS:  brew install pango cairo glib libffi\n'
                '  Linux:  apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0\n'
            )
            raise SystemExit(1)

        with open(out_path, 'wb') as f:
            f.write(pdf_bytes)

        size_kb = round(len(pdf_bytes) / 1024)
        self.stdout.write(self.style.SUCCESS(
            f'Sample PDF written → {out_path}  ({size_kb} KB)\n'
            f'It will be included automatically in the /download/template/ zip.'
        ))
