"""Celery tasks for document production."""
import os
import re
import tempfile
from celery import shared_task


def _pdf_url_fetcher(url):
    """
    WeasyPrint url_fetcher that serves /media/ assets directly from Django
    storage, bypassing the HTTP stack entirely.

    For any other URL (unlikely, since all CSS is inlined) falls through to
    WeasyPrint's default fetcher.
    """
    import mimetypes
    from django.conf import settings
    from django.core.files.storage import default_storage

    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    # Strip protocol + host so both "/media/..." and "http://host/media/..." work
    path_only = re.sub(r'^https?://[^/]+', '', url)

    if path_only.startswith(media_url):
        storage_path = path_only[len(media_url):]
        try:
            with default_storage.open(storage_path, 'rb') as f:
                data = f.read()
            mime_type = mimetypes.guess_type(storage_path)[0] or 'application/octet-stream'
            return {'string': data, 'mime_type': mime_type}
        except Exception:
            pass  # fall through to default

    from weasyprint.urls import default_url_fetcher
    return default_url_fetcher(url)


def _preprocess_html_for_pdf(html_content, interactive):
    """
    Replace <video> and <audio> figures with PDF-safe markup and collect
    media metadata for the Screen-annotation post-processor.

    Returns (processed_html, media_items) where media_items is a list of:
      {'id', 'src', 'media_type': 'video'|'audio', 'mime'}

    Interactive mode
      <video>  → poster image shown on the page (visual placeholder that
                 Acrobat overlays with the playing video); clickable link
                 fallback for non-Acrobat viewers.
                 A Screen annotation will be added over this area by
                 _add_media_annotations().
      <audio>  → styled box with a clickable link fallback; annotation plays
                 audio in the background when clicked in Acrobat.

    Flat mode
      <video> and <audio> → static labelled placeholder boxes, no links.
    """
    import mimetypes as _mt

    media_items = []

    def _attr(html, name):
        m = re.search(rf'\b{name}="([^"]*)"', html)
        return m.group(1) if m else ''

    def _source_src(html):
        m = re.search(r'<source\s[^>]*src="([^"]*)"', html)
        return m.group(1) if m else ''

    def _figcaption(html):
        m = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', html, re.DOTALL)
        return m.group(1) if m else ''

    def _placeholder_box(fig_id, icon, label, caption):
        cap_html = f'<figcaption>{caption}</figcaption>' if caption else ''
        return (
            f'<figure id="{fig_id}" class="pdf-media-placeholder">'
            f'<div class="pdf-media-box">'
            f'<span class="pdf-media-icon">{icon}</span>'
            f' <span class="pdf-media-label">{label}</span>'
            f'</div>'
            f'{cap_html}'
            f'</figure>'
        )

    def _fallback_link(src, label):
        """Link outside the figure so it's not covered by the Screen annotation rect."""
        if not src:
            return ''
        return (
            f'<p class="pdf-media-link">'
            f'<a href="{src}">{label}</a>'
            f'</p>'
        )

    def replace_video(m):
        html = m.group(0)
        fig_id = _attr(html, 'id')
        caption = _figcaption(html)
        src = _source_src(html)
        poster = _attr(html, 'poster')
        cap_html = f'<figcaption>{caption}</figcaption>' if caption else ''

        if interactive:
            if src:
                mime = _mt.guess_type(src.split('?')[0])[0] or 'video/mp4'
                media_items.append({
                    'id': fig_id, 'src': src,
                    'media_type': 'video', 'mime': mime,
                })
            # No <a> inside the figure — the Screen annotation covers the entire
            # figure rect. A link inside would become a /Link annotation underneath
            # the Screen annotation, potentially intercepting clicks in Acrobat.
            # Instead put a plain-text Acrobat hint inside the figure and a
            # separate fallback link *outside* the figure (below its bounding box)
            # for non-Acrobat viewers where Screen annotations don't work.
            fallback = _fallback_link(src, '&#9654; Open video file (non-Acrobat viewers)')
            if poster:
                return (
                    f'<figure id="{fig_id}" class="article-figure">'
                    f'<img src="{poster}" alt="" style="display:block;width:100%;">'
                    f'<figcaption>{caption}'
                    f' <span style="font-size:8pt;color:#E86B1F;">&#9654; Click to play (Adobe Acrobat)</span>'
                    f'</figcaption></figure>{fallback}'
                )
            return (
                f'<figure id="{fig_id}" class="pdf-media-placeholder">'
                f'<div class="pdf-media-box">'
                f'<span class="pdf-media-icon">&#9654;</span>'
                f' <span class="pdf-media-label">Video — click to play (Adobe Acrobat)</span>'
                f'</div>{cap_html}</figure>{fallback}'
            )

        # Flat mode: embed a clickable link directly in the placeholder box.
        if src:
            return (
                f'<figure id="{fig_id}" class="pdf-media-placeholder">'
                f'<div class="pdf-media-box">'
                f'<span class="pdf-media-icon">&#9654;</span>'
                f' <a href="{src}" class="pdf-media-label" style="color:#E86B1F;">Video — open file</a>'
                f'</div>{cap_html}</figure>'
            )
        return _placeholder_box(fig_id, '▶', 'Video', caption)

    def replace_audio(m):
        html = m.group(0)
        fig_id = _attr(html, 'id')
        caption = _figcaption(html)
        src = _source_src(html)
        cap_html = f'<figcaption>{caption}</figcaption>' if caption else ''

        if interactive:
            if src:
                mime = _mt.guess_type(src.split('?')[0])[0] or 'audio/mpeg'
                media_items.append({
                    'id': fig_id, 'src': src,
                    'media_type': 'audio', 'mime': mime,
                })
            fallback = _fallback_link(src, '&#9835; Open audio file (non-Acrobat viewers)')
            return (
                f'<figure id="{fig_id}" class="pdf-media-placeholder">'
                f'<div class="pdf-media-box">'
                f'<span class="pdf-media-icon">&#9835;</span>'
                f' <span class="pdf-media-label">Audio — click to play (Adobe Acrobat)</span>'
                f'</div>{cap_html}</figure>{fallback}'
            )

        # Flat mode: embed a clickable link directly in the placeholder box.
        if src:
            return (
                f'<figure id="{fig_id}" class="pdf-media-placeholder">'
                f'<div class="pdf-media-box">'
                f'<span class="pdf-media-icon">&#9835;</span>'
                f' <a href="{src}" class="pdf-media-label" style="color:#E86B1F;">Audio — open file</a>'
                f'</div>{cap_html}</figure>'
            )
        return _placeholder_box(fig_id, '&#9835;', 'Audio', caption)

    html_content = re.sub(
        r'<figure\b[^>]*class="[^"]*article-video[^"]*"[^>]*>.*?</figure>',
        replace_video, html_content, flags=re.DOTALL,
    )
    html_content = re.sub(
        r'<figure\b[^>]*class="[^"]*article-audio[^"]*"[^>]*>.*?</figure>',
        replace_audio, html_content, flags=re.DOTALL,
    )
    return html_content, media_items


def _find_box_positions(pages, target_ids):
    """
    Traverse WeasyPrint's post-layout page boxes to find the rendered
    position of HTML elements by their id attribute.

    Returns {id: {'page': int, 'x', 'y', 'w', 'h', 'page_h'}}
    All values are in CSS pixels at 96 DPI (WeasyPrint's internal unit).
    Coordinates are relative to the top-left of the full page (incl. margins).
    """
    if not target_ids:
        return {}

    found = {}

    def _walk(box, page_idx, page_h):
        elem = getattr(box, 'element', None)
        if elem is not None:
            try:
                eid = elem.get('id') or ''
            except Exception:
                eid = ''
            if eid in target_ids and eid not in found:
                px = getattr(box, 'position_x', None)
                py = getattr(box, 'position_y', None)
                if px is not None and py is not None:
                    try:
                        pw = box.margin_width()
                        ph = box.margin_height()
                    except Exception:
                        pw = getattr(box, 'width', 0) or 0
                        ph = getattr(box, 'height', 0) or 0
                    found[eid] = {
                        'page': page_idx,
                        'x': float(px),
                        'y': float(py),
                        'w': float(pw),
                        'h': float(ph),
                        'page_h': page_h,
                    }
        for child in getattr(box, 'children', []):
            _walk(child, page_idx, page_h)

    for i, page in enumerate(pages):
        try:
            page_h = float(page._page_box.height)
            _walk(page._page_box, i, page_h)
        except Exception:
            pass

    return found


def _add_media_annotations(pdf_bytes, media_items, positions):
    """
    Post-process a WeasyPrint PDF to embed media files and add PDF Screen
    annotations so Adobe Acrobat can play them in place.

    Each annotation is placed at the exact rendered position of the figure
    element. Non-Acrobat viewers see the underlying poster image / link from
    the page content and can still open the file via the clickable URL.

    Screen annotation behaviour in Acrobat:
      video → plays inside the annotation rectangle (W=2)
      audio → plays as background audio with no window (W=0)
    """
    if not media_items or not positions:
        return pdf_bytes

    import io
    import mimetypes as _mt

    try:
        import pikepdf
    except ImportError:
        return pdf_bytes  # pikepdf not installed — degrade gracefully

    from django.conf import settings
    from django.core.files.storage import default_storage

    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    CSS_TO_PT = 0.75  # 96 DPI → 72 pt/inch

    try:
        pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    except Exception:
        return pdf_bytes

    for item in media_items:
        pos = positions.get(item['id'])
        if not pos or pos['page'] >= len(pdf.pages):
            continue

        page = pdf.pages[pos['page']]

        # ── Convert CSS px → PDF points, flip Y axis ────────────
        # WeasyPrint's position_y is measured from the page top (including
        # margins), in CSS px at 96 DPI. The page_h in positions is the
        # content-area height only. Use the PDF MediaBox to get the true
        # full-page height in pts so the Y-flip is correct.
        try:
            media_box = page.obj['/MediaBox']
            page_h_pt = float(media_box[3])
        except Exception:
            page_h_pt = pos['page_h'] * CSS_TO_PT  # fallback
        x1 = pos['x'] * CSS_TO_PT
        y2 = page_h_pt - pos['y'] * CSS_TO_PT                    # top in PDF coords
        y1 = page_h_pt - (pos['y'] + pos['h']) * CSS_TO_PT       # bottom in PDF coords
        x2 = x1 + pos['w'] * CSS_TO_PT

        # ── Read media file from storage ─────────────────────────
        src_path = re.sub(r'^https?://[^/]+', '', item['src'])
        if not src_path.startswith(media_url):
            continue
        storage_path = src_path[len(media_url):]
        try:
            with default_storage.open(storage_path, 'rb') as f:
                media_data = f.read()
        except Exception:
            continue

        filename = storage_path.split('/')[-1]
        mime_type = item.get('mime') or _mt.guess_type(filename)[0] or 'application/octet-stream'

        # ── Embedded file stream ─────────────────────────────────
        ef_stream = pikepdf.Stream(pdf, media_data)
        ef_stream['/Type'] = pikepdf.Name('/EmbeddedFile')
        ef_ref = pdf.make_indirect(ef_stream)

        # ── File specification ───────────────────────────────────
        filespec = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name('/Filespec'),
            F=pikepdf.String(filename),
            UF=pikepdf.String(filename),
            EF=pikepdf.Dictionary(F=ef_ref),
        ))

        # ── Media clip (MCD = media clip data) ───────────────────
        media_clip = pikepdf.Dictionary(
            Type=pikepdf.Name('/MediaClip'),
            S=pikepdf.Name('/MCD'),
            D=filespec,
            CT=pikepdf.String(mime_type),
        )

        # ── Media play parameters (PDF 1.7 spec Table 284–285) ───
        # W is a "may honor" entry placed directly in MH, not in a
        # sub-dictionary. W values: -1=default, 0=floating window,
        # 1=fullscreen, 2=render in annotation rect, 3=hidden.
        # Video: W=0 (floating player window — most compatible across Acrobat
        #   versions; W=2 "annotation rect" has poor real-world support).
        # Audio: W=3 (hidden — no window, plays in background).
        win_type = 0 if item['media_type'] == 'video' else 3
        play_params = pikepdf.Dictionary(
            Type=pikepdf.Name('/MediaPlayParams'),
            MH=pikepdf.Dictionary(
                W=win_type,
                C=True,     # show controls
            ),
        )

        # ── Rendition ────────────────────────────────────────────
        rendition = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name('/Rendition'),
            S=pikepdf.Name('/MR'),
            N=pikepdf.String(filename),
            C=media_clip,
            P=play_params,
        ))

        # ── Screen annotation ─────────────────────────────────────
        # Must be indirect so the Rendition action can self-reference it.
        annot = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name('/Annot'),
            Subtype=pikepdf.Name('/Screen'),
            Rect=pikepdf.Array([
                pikepdf.Real(x1), pikepdf.Real(y1),
                pikepdf.Real(x2), pikepdf.Real(y2),
            ]),
            F=4,       # print flag
            T=pikepdf.String(filename),
        ))

        # Click → play rendition action
        annot['/A'] = pikepdf.Dictionary(
            Type=pikepdf.Name('/Action'),
            S=pikepdf.Name('/Rendition'),
            OP=0,       # 0 = play
            R=rendition,
            AN=annot,   # self-reference required by spec
        )

        if '/Annots' not in page:
            page['/Annots'] = pikepdf.Array()
        page.Annots.append(annot)

    try:
        out = io.BytesIO()
        pdf.save(out)
        return out.getvalue()
    except Exception:
        return pdf_bytes


def _parse_bib(bib_source: str) -> dict[str, dict]:
    """
    Parse a BibTeX file into a dict keyed by cite key.

    Handles @article, @book, @incollection, @online, @misc and similar entry
    types.  Only extracts the fields used by the bibliography renderer: author,
    title, year, journal/booktitle, publisher, doi, url.

    Returns: {cite_key: {'type', 'title', 'authors', 'year', 'doi', 'url'}}
    """
    entries: dict[str, dict] = {}

    # Match full entry blocks: @type{key, ... }
    entry_pat = re.compile(
        r'@(\w+)\s*\{\s*([^,]+?)\s*,\s*(.*?)\n\}',
        re.DOTALL | re.IGNORECASE,
    )

    def _get_field(body: str, name: str) -> str:
        """Extract a single BibTeX field value (handles {…} and "…" delimiters)."""
        m = re.search(
            rf'\b{re.escape(name)}\s*=\s*(?:\{{(.*?)\}}|"([^"]*)")',
            body, re.DOTALL | re.IGNORECASE,
        )
        if not m:
            return ''
        val = (m.group(1) or m.group(2) or '').strip()
        # Strip inner braces used for case protection: {Smith} → Smith
        val = re.sub(r'\{([^}]*)\}', r'\1', val)
        return val

    for m in entry_pat.finditer(bib_source):
        entry_type = m.group(1).lower()
        cite_key = m.group(2).strip()
        body = m.group(3)

        raw_author = _get_field(body, 'author')
        # "Last, First and Last2, First2" → ["First Last", "First2 Last2"]
        authors: list[str] = []
        for person in re.split(r'\s+and\s+', raw_author, flags=re.IGNORECASE):
            person = person.strip()
            if ',' in person:
                parts = [p.strip() for p in person.split(',', 1)]
                authors.append(f'{parts[1]} {parts[0]}')
            elif person:
                authors.append(person)

        entries[cite_key] = {
            'type': entry_type,
            'title': _get_field(body, 'title'),
            'authors': authors,
            'year': _get_field(body, 'year'),
            'doi': _get_field(body, 'doi'),
            'url': _get_field(body, 'url'),
        }

    return entries


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

    # Enrich bibliography items from the uploaded .bib asset (if present).
    bib_asset = revision.assets.filter(original_filename__endswith='.bib').first()
    if bib_asset:
        try:
            with bib_asset.file.open('rb') as f:
                bib_source = f.read().decode('utf-8', errors='replace')
            bib_entries = _parse_bib(bib_source)
            # Update citation items in canonical_data
            for item in canonical_data.get('citations', {}).get('items', []):
                entry = bib_entries.get(item['citeKey'])
                if entry:
                    item.update(entry)
            # Update bibliography block
            for block in canonical_data.get('content', []):
                if block.get('type') == 'bibliography':
                    for item in block.get('items', []):
                        entry = bib_entries.get(item['citeKey'])
                        if entry:
                            item.update(entry)
        except Exception:
            pass  # Missing or malformed .bib — leave placeholders in place

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
    submission = doc.revision.submission
    html = render_html(doc.data, submission)
    toc = build_toc(doc.data)
    h = hashlib.sha256(html.encode()).hexdigest()[:16]

    # Reuse any existing HTMLBuild for this submission (from a previous revision)
    # rather than creating a new one — prevents the slug unique-constraint violation
    # that occurs when a resubmission produces a new CanonicalDocument.
    build = HTMLBuild.objects.filter(
        document__revision__submission=submission
    ).first()
    if build:
        build.document = doc
    else:
        build = HTMLBuild(document=doc)

    build.html_content = html
    build.table_of_contents = toc
    build.build_hash = h
    build.save()

    doc.html_build_ok = True
    doc.save(update_fields=['html_build_ok'])


def _collect_media_items_from_assets(document, submission):
    """
    Build media_items directly from canonical JSON + SubmissionAssets when the
    HTML-based path yields nothing (e.g. filename mismatch between canonical
    JSON's originalFilename and the DB asset's original_filename).

    Matching strategy:
      1. Exact: asset['originalFilename'] == sa.original_filename
      2. Fallback: first asset whose kind matches the media type (video/audio)
         — useful for test data where filenames diverged during upload.

    Returns the same structure as _preprocess_html_for_pdf:
      [{'id', 'src', 'media_type': 'video'|'audio', 'mime'}]
    """
    import mimetypes as _mt

    canonical_data = getattr(document, 'data', None)
    if not canonical_data:
        return []

    # Build lookup: assetId → canonical asset dict
    assets_by_id = {
        a['assetId']: a
        for a in canonical_data.get('assets', [])
        if 'assetId' in a
    }

    # Gather uploaded assets for this revision, grouped by kind
    revision = submission.get_current_revision()
    if not revision:
        return []

    uploaded = list(revision.assets.filter(kind__in=['video', 'audio']).exclude(file=''))

    # Build exact-match lookup: original_filename → SubmissionAsset
    by_filename = {sa.original_filename: sa for sa in uploaded}

    # Ordered lists by kind for positional fallback
    video_assets = [sa for sa in uploaded if sa.kind == 'video']
    audio_assets = [sa for sa in uploaded if sa.kind == 'audio']
    _used_fallback = {'video': 0, 'audio': 0}

    items = []
    for block in canonical_data.get('content', []):
        if block.get('type') != 'media':
            continue
        media_type = block.get('mediaType', 'video')
        if media_type not in ('video', 'audio'):
            continue

        block_id = block.get('id', '')
        asset_ref = block.get('assetRef', '')
        asset = assets_by_id.get(asset_ref, {})
        original_name = asset.get('originalFilename', '')

        # 1. Exact match by original filename
        sa = by_filename.get(original_name)

        # 2. Fallback: grab the next unused asset of the right kind
        if sa is None:
            pool = video_assets if media_type == 'video' else audio_assets
            idx = _used_fallback[media_type]
            if idx < len(pool):
                sa = pool[idx]
                _used_fallback[media_type] += 1

        if sa is None or not sa.file:
            continue

        src_url = sa.file.url
        mime = sa.mime_type or _mt.guess_type(sa.original_filename)[0] or (
            'video/mp4' if media_type == 'video' else 'audio/mpeg'
        )
        items.append({
            'id': block_id,
            'src': src_url,
            'media_type': media_type,
            'mime': mime,
        })

    return items


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
      text-align: justify;
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
    h1 { font-size: 16pt; margin: 2rem 0 0.8rem; text-align: left; }
    h2 { font-size: 13pt; margin: 1.6rem 0 0.6rem; text-align: left; }
    h3 { font-size: 11pt; margin: 1.2rem 0 0.4rem; text-align: left; }
    p { margin: 0 0 0.8rem; }
    figure { margin: 1.5rem 0; text-align: center; }
    figcaption { font-size: 9pt; color: #6B6B6B; margin-top: 0.4rem; font-style: italic; text-align: center; }
    img { max-width: 100%; height: auto; }
    table { width: 100%; border-collapse: collapse; margin: 1.2rem 0; font-size: 10pt; }
    th { background: #f5f5f5; border-bottom: 2px solid #E5E5E5; padding: 0.4rem 0.6rem; text-align: left; }
    td { border-bottom: 1px solid #E5E5E5; padding: 0.4rem 0.6rem; text-align: left; }
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
    a { color: #E86B1F; text-decoration: underline; }
    .article-cite { text-decoration: none; }
    """ if interactive else ""

    media_placeholder_css = """
    /* Video / audio placeholder boxes */
    .pdf-media-placeholder { margin: 1.5rem 0 0.25rem; }
    .pdf-media-box {
      display: block;
      border: 1px solid #D0D0D0;
      border-left: 3px solid #E86B1F;
      background: #FAFAFA;
      padding: 0.6rem 1rem;
      font-family: Helvetica, Arial, sans-serif;
      font-size: 10pt;
      color: #6B6B6B;
    }
    .pdf-media-icon { font-size: 11pt; margin-right: 0.3em; }
    .pdf-media-label { font-style: italic; }
    /* Fallback link rendered outside the figure (below Screen annotation rect) */
    .pdf-media-link {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 8pt;
      color: #999;
      margin: 0 0 1.2rem 0;
    }
    .pdf-media-link a { color: #E86B1F; }
    """

    # Pre-process HTML: replace <video>/<audio> with PDF-safe equivalents
    # and collect media metadata for Screen annotation post-processing.
    article_html, media_items = _preprocess_html_for_pdf(build.html_content, interactive)

    # Fallback: if the HTML-based extraction found no media (happens when
    # original_filename in the DB doesn't match originalFilename in canonical
    # JSON — e.g. test data uploaded before the filename-preservation fix),
    # reconstruct media_items directly from canonical JSON + SubmissionAssets.
    if interactive and not media_items:
        media_items = _collect_media_items_from_assets(export.document, submission)

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
<style>{base_css}{bookmark_css}{media_placeholder_css}</style>
</head>
<body>
<div class="pdf-header">
  {issue_line}
  <h1 class="pdf-title">{html_lib.escape(submission.title)}</h1>
  {subtitle_line}
  <p class="pdf-author">{html_lib.escape(submission.author.display_name)}</p>
</div>
{article_html}
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

    weasy = HTML(
        string=html_doc,
        base_url='http://localhost/',
        url_fetcher=_pdf_url_fetcher,
    )

    if interactive and media_items:
        # Two-pass: render to get layout positions, then add Screen annotations.
        rendered = weasy.render()
        positions = _find_box_positions(
            rendered.pages,
            {item['id'] for item in media_items},
        )
        pdf_bytes = rendered.write_pdf()
        pdf_bytes = _add_media_annotations(pdf_bytes, media_items, positions)
    else:
        pdf_bytes = weasy.write_pdf()
    filename = f'{submission.slug or "article"}.pdf'
    export.file.save(filename, ContentFile(pdf_bytes), save=True)
    export.document.pdf_build_ok = True
    export.document.save(update_fields=['pdf_build_ok'])
