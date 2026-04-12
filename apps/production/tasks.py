"""Celery tasks for document production."""
import os
import tempfile
from celery import shared_task


@shared_task
def ingest_submission(revision_pk):
    """Parse .tex file → canonical JSON → queue HTML build."""
    from apps.submissions.models import SubmissionRevision
    from apps.documents.models import CanonicalDocument
    from apps.documents.parsers.latex_parser import parse_latex

    revision = SubmissionRevision.objects.select_related('submission').get(pk=revision_pk)
    submission = revision.submission

    # Read .tex source
    try:
        with revision.manuscript_file.open('rb') as f:
            tex_source = f.read().decode('utf-8', errors='replace')
    except Exception as e:
        return {'error': f'Could not read manuscript file: {e}'}

    meta = {
        'title': submission.title,
        'subtitle': submission.subtitle,
        'abstract': submission.abstract,
        'keywords': submission.keywords,
        'disciplines': submission.disciplines,
        'language': submission.language,
        'article_type': submission.article_type,
    }

    canonical_data = parse_latex(tex_source, meta)
    doc, created = CanonicalDocument.objects.update_or_create(
        revision=revision,
        defaults={
            'data': canonical_data,
            'schema_version': canonical_data.get('schemaVersion', '1.0'),
        }
    )
    # Build HTML immediately (synchronous — no broker needed)
    build_html_for_document(doc.pk)
    return {'document_id': doc.pk, 'created': created}


@shared_task
def build_html_for_document(document_pk):
    """Build HTML from canonical JSON and store."""
    from apps.documents.models import CanonicalDocument
    from apps.documents.renderers.html_renderer import render_html, build_toc
    from apps.production.models import HTMLBuild
    import hashlib

    doc = CanonicalDocument.objects.get(pk=document_pk)
    html = render_html(doc.data, doc.revision.submission)
    toc = build_toc(doc.data)
    h = hashlib.sha256(html.encode()).hexdigest()[:16]
    build, _ = HTMLBuild.objects.get_or_create(document=doc)
    build.html_content = html
    build.table_of_contents = toc
    build.build_hash = h
    build.save()
    doc.html_build_ok = True
    doc.save(update_fields=['html_build_ok'])


@shared_task
def generate_pdf(export_pk):
    """Generate PDF from the published HTML using WeasyPrint."""
    import html as html_lib
    from apps.production.models import PDFExport
    from django.core.files.base import ContentFile

    export = PDFExport.objects.select_related(
        'document__revision__submission__author',
        'document__revision__submission__issue',
    ).get(pk=export_pk)

    build = getattr(export.document, 'html_build', None)
    if not build or not build.html_content:
        export.document.pdf_build_ok = False
        export.document.save(update_fields=['pdf_build_ok'])
        return

    submission = export.document.revision.submission
    interactive = (export.mode == 'interactive')

    # CSS variables and base typography (no web fonts — WeasyPrint can't fetch them)
    base_css = """
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
    .pdf-header {
      border-bottom: 2px solid #E86B1F;
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }
    .pdf-issue { font-size: 9pt; color: #6B6B6B; margin-bottom: 0.4rem; }
    .pdf-title { font-size: 22pt; line-height: 1.2; margin-bottom: 0.5rem; font-weight: bold; }
    .pdf-subtitle { font-size: 13pt; color: #555; margin-bottom: 0.5rem; font-style: italic; }
    .pdf-author { font-size: 11pt; color: #444; font-family: Helvetica, Arial, sans-serif; }
    /* Article body */
    .article-body { margin: 0; }
    .article-abstract { border-left: 3px solid #E86B1F; padding-left: 1rem; margin: 1.5rem 0; }
    .article-abstract h2 { font-size: 10pt; text-transform: uppercase; letter-spacing: 0.05em; color: #6B6B6B; margin-bottom: 0.4rem; }
    .article-abstract p { font-size: 10pt; color: #444; }
    .article-authors { font-size: 10pt; color: #6B6B6B; margin-bottom: 1rem; }
    h1 { font-size: 16pt; margin: 2rem 0 0.8rem; }
    h2 { font-size: 13pt; margin: 1.6rem 0 0.6rem; }
    h3 { font-size: 11pt; margin: 1.2rem 0 0.4rem; }
    p { margin: 0 0 0.8rem; }
    figure { margin: 1.5rem 0; text-align: center; }
    figcaption { font-size: 9pt; color: #6B6B6B; margin-top: 0.4rem; font-style: italic; }
    img { max-width: 100%; height: auto; }
    table { width: 100%; border-collapse: collapse; margin: 1.2rem 0; font-size: 10pt; }
    th { background: #f5f5f5; border-bottom: 2px solid #E5E5E5; padding: 0.4rem 0.6rem; text-align: left; }
    td { border-bottom: 1px solid #E5E5E5; padding: 0.4rem 0.6rem; }
    a { color: #E86B1F; text-decoration: none; }
    /* Blockquotes — 0.5 inch indent both sides, no quotation marks */
    .article-blockquote {
      margin-left: 36pt;
      margin-right: 36pt;
      font-style: italic;
      color: #444;
    }
    .article-blockquote p { margin: 0; }
    /* Inline citations */
    .article-cite { color: #1A1A1A; text-decoration: none; }
    /* Footnotes — WeasyPrint float: footnote places them at page bottom */
    .fn-wrap { display: inline; }
    .fn-ref-num { font-size: 0.7em; vertical-align: super; color: #E86B1F; font-weight: bold; line-height: 0; }
    .fn-note { float: footnote; font-size: 9pt; color: #444; line-height: 1.4; }
    .fn-note__num { font-weight: bold; color: #E86B1F; margin-right: 0.2em; }
    /* Hide the bottom footnotes section in PDF (WeasyPrint handles via float: footnote) */
    .article-footnotes { display: none; }
    /* Hide paragraph anchor numbers — used for reviewer targeting, not visible in PDF */
    .para-num { display: none; }
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
    /* Bibliography */
    .article-bibliography { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #E5E5E5; }
    .article-bibliography h2 { font-size: 10pt; text-transform: uppercase; letter-spacing: 0.05em; color: #6B6B6B; margin-bottom: 0.6rem; }
    .article-bibliography__list { list-style: none; padding: 0; margin: 0; }
    .bibliography-item { font-size: 9pt; margin-bottom: 0.5rem; padding-left: 1.2em; text-indent: -1.2em; line-height: 1.45; }
    .bib-title { font-style: italic; }
    .article-bibliography__note { font-size: 9pt; color: #6B6B6B; font-style: italic; }
    """

    bookmark_css = """
    h1 { bookmark-level: 1; bookmark-label: content(); }
    h2 { bookmark-level: 2; bookmark-label: content(); }
    h3 { bookmark-level: 3; bookmark-label: content(); }
    a { color: #E86B1F; }
    """ if interactive else ""

    # Metadata header
    issue_line = ''
    if submission.issue:
        issue_line = f'<p class="pdf-issue">Issue #{submission.issue.number} · Vol. {submission.issue.volume} · {submission.issue.year}</p>'

    subtitle_line = ''
    if submission.subtitle:
        subtitle_line = f'<p class="pdf-subtitle">{html_lib.escape(submission.subtitle)}</p>'

    html_doc = f"""<!DOCTYPE html>
<html lang="{html_lib.escape(submission.language)}">
<head>
<meta charset="utf-8">
<title>{html_lib.escape(submission.title)}</title>
<style>{base_css}{bookmark_css}</style>
</head>
<body>
<div class="pdf-header">
  {issue_line}
  <h1 class="pdf-title">{html_lib.escape(submission.title)}</h1>
  {subtitle_line}
  <p class="pdf-author">{html_lib.escape(submission.author.display_name)}</p>
</div>
{build.html_content}
</body>
</html>"""

    # On macOS + Homebrew, GLib/Pango libs live in /opt/homebrew/lib.
    # Ensure the path is present before importing WeasyPrint.
    import sys
    if sys.platform == 'darwin':
        brew_lib = '/opt/homebrew/lib'
        dyld = os.environ.get('DYLD_LIBRARY_PATH', '')
        if brew_lib not in dyld:
            os.environ['DYLD_LIBRARY_PATH'] = f'{brew_lib}:{dyld}' if dyld else brew_lib

    from weasyprint import HTML
    pdf_bytes = HTML(string=html_doc).write_pdf()
    filename = f'{submission.slug or "article"}.pdf'
    export.file.save(filename, ContentFile(pdf_bytes), save=True)
    export.document.pdf_build_ok = True
    export.document.save(update_fields=['pdf_build_ok'])
