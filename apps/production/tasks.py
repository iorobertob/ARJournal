"""Celery tasks for document production."""
import os
import subprocess
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
    build_html_for_document.delay(doc.pk)
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
    """Generate PDF from LaTeX source using pdflatex subprocess."""
    from apps.production.models import PDFExport
    from django.core.files.base import ContentFile

    export = PDFExport.objects.select_related('document__revision').get(pk=export_pk)
    revision = export.document.revision

    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy .tex file
        tex_path = os.path.join(tmpdir, 'article.tex')
        try:
            with revision.manuscript_file.open('rb') as src:
                with open(tex_path, 'wb') as dst:
                    dst.write(src.read())
        except Exception:
            export.document.pdf_build_ok = False
            export.document.save(update_fields=['pdf_build_ok'])
            return

        # Run pdflatex twice (for references)
        for _ in range(2):
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-output-directory', tmpdir, tex_path],
                capture_output=True, timeout=120,
            )

        pdf_path = os.path.join(tmpdir, 'article.pdf')
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pf:
                export.file.save('article.pdf', ContentFile(pf.read()), save=True)
            export.document.pdf_build_ok = True
            export.document.save(update_fields=['pdf_build_ok'])
        else:
            export.document.pdf_build_ok = False
            export.document.save(update_fields=['pdf_build_ok'])
