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


def _preprocess_html_for_pdf(html_content, interactive, site_url=''):
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
      <video> and <audio> → styled placeholder boxes with active hyperlinks.
    """
    import mimetypes as _mt
    from urllib.parse import urljoin as _urljoin

    media_items = []
    _base = (site_url or '').rstrip('/')

    def _attr(html, name):
        m = re.search(rf'\b{name}="([^"]*)"', html)
        return m.group(1) if m else ''

    def _source_src(html):
        m = re.search(r'<source\s[^>]*src="([^"]*)"', html)
        return m.group(1) if m else ''

    def _abs(src):
        """Make a server-relative URL absolute so PDF links work when downloaded."""
        if not src:
            return src
        if src.startswith(('http://', 'https://')):
            return src
        if _base:
            return _urljoin(_base + '/', src.lstrip('/'))
        return src

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
        # Media is stream-only (HLS + signed short-lived URLs): never embed or link
        # the file in a downloadable PDF. Show the poster + a "view online" note.
        src = ''
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
                    f'<img src="{poster}" alt="" style="display:block;width:100%;max-height:15cm;object-fit:contain;">'
                    f'<figcaption>{caption}'
                    f' <span style="font-size:8pt;color:#FF4500;">&#9654; Video — view in the online article</span>'
                    f'</figcaption></figure>'
                )
            return (
                f'<figure id="{fig_id}" class="pdf-media-placeholder">'
                f'<div class="pdf-media-box">'
                f'<span class="pdf-media-icon">&#9654;</span>'
                f' <span class="pdf-media-label">Video — view in the online article</span>'
                f'</div>{cap_html}</figure>'
            )

        # Flat mode: styled placeholder with active hyperlink.
        if src:
            fname = src.rstrip('/').rsplit('/', 1)[-1]
            return (
                f'<figure id="{fig_id}" class="pdf-media-placeholder">'
                f'<div class="pdf-media-box">'
                f'<span class="pdf-media-icon">&#9654;</span>'
                f'<span class="pdf-media-label">Video</span>'
                f'<a href="{src}" class="pdf-media-filelink">{fname}</a>'
                f'</div>{cap_html}</figure>'
            )
        return _placeholder_box(fig_id, '▶', 'Video', caption)

    def replace_audio(m):
        html = m.group(0)
        fig_id = _attr(html, 'id')
        caption = _figcaption(html)
        # Stream-only: never embed/link the audio file in a downloadable PDF.
        src = ''
        cap_html = f'<figcaption>{caption}</figcaption>' if caption else ''

        if interactive:
            return (
                f'<figure id="{fig_id}" class="pdf-media-placeholder">'
                f'<div class="pdf-media-box">'
                f'<span class="pdf-media-icon">&#9835;</span>'
                f' <span class="pdf-media-label">Audio — listen in the online article</span>'
                f'</div>{cap_html}</figure>'
            )

        # Flat mode: styled placeholder with active hyperlink.
        if src:
            fname = src.rstrip('/').rsplit('/', 1)[-1]
            return (
                f'<figure id="{fig_id}" class="pdf-media-placeholder">'
                f'<div class="pdf-media-box">'
                f'<span class="pdf-media-icon">&#9835;</span>'
                f'<span class="pdf-media-label">Audio</span>'
                f'<a href="{src}" class="pdf-media-filelink">{fname}</a>'
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

    # Cap embedded image resolution: WeasyPrint ignores srcset, so pick a
    # print-sized derivative from each <img>'s srcset and use it as src. This
    # keeps 2500px originals out of the PDF. Images without a srcset (logos,
    # or pre-derivative builds) are left untouched → embedded at natural size.
    from apps.submissions.imaging import PRINT_CAP

    def _pick_from_srcset(srcset, cap):
        best_url, best_w = '', -1
        smallest_url, smallest_w = '', 1 << 30
        for part in srcset.split(','):
            bits = part.strip().split()
            if len(bits) != 2 or not bits[1].endswith('w'):
                continue
            try:
                w = int(bits[1][:-1])
            except ValueError:
                continue
            if w < smallest_w:
                smallest_w, smallest_url = w, bits[0]
            if cap >= w > best_w:
                best_w, best_url = w, bits[0]
        return best_url or smallest_url

    def replace_img(m):
        tag = m.group(0)
        srcset = _attr(tag, 'srcset')
        if not srcset:
            return tag
        capped = _pick_from_srcset(srcset, PRINT_CAP)
        if not capped:
            return tag
        tag = re.sub(r'\bsrc="[^"]*"', f'src="{capped}"', tag, count=1)
        tag = re.sub(r'\s(?:srcset|sizes)="[^"]*"', '', tag)
        return tag

    html_content = re.sub(r'<img\b[^>]*>', replace_img, html_content)
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
        # Keep each person in the raw BibTeX form ("Family, Given" or "Given
        # Family") so the renderer can extract surnames reliably (needed for the
        # Cambridge "Surname Initials" reference format and alphabetical sort).
        authors = [p.strip() for p in re.split(r'\s+and\s+', raw_author, flags=re.IGNORECASE) if p.strip()]
        raw_editor = _get_field(body, 'editor')
        editors = [p.strip() for p in re.split(r'\s+and\s+', raw_editor, flags=re.IGNORECASE) if p.strip()]

        entries[cite_key] = {
            'type': entry_type,
            'title': _get_field(body, 'title'),
            'authors': authors,
            'editors': editors,
            'year': _get_field(body, 'year'),
            'journal': _get_field(body, 'journal'),
            'volume': _get_field(body, 'volume'),
            'number': _get_field(body, 'number'),
            'pages': _get_field(body, 'pages'),
            'publisher': _get_field(body, 'publisher'),
            'booktitle': _get_field(body, 'booktitle'),
            'editor': _get_field(body, 'editor'),
            'school': _get_field(body, 'school'),
            'institution': _get_field(body, 'institution'),
            'organization': _get_field(body, 'organization'),
            'address': _get_field(body, 'address'),
            'edition': _get_field(body, 'edition'),
            'series': _get_field(body, 'series'),
            'howpublished': _get_field(body, 'howpublished'),
            'note': _get_field(body, 'note'),
            'doi': _get_field(body, 'doi'),
            'url': _get_field(body, 'url'),
        }

    return entries


@shared_task
def ingest_submission(revision_pk):
    """Parse manuscript → canonical JSON → queue HTML build.

    Supports two source types:
      - 'latex'   : reads .tex file and runs the LaTeX parser
      - 'wysiwyg' : uses wysiwyg_data already stored on the revision
    """
    from apps.submissions.models import SubmissionRevision, RevisionSource
    from apps.documents.models import CanonicalDocument
    from apps.documents.parsers.latex_parser import parse_latex

    revision = SubmissionRevision.objects.select_related('submission').get(pk=revision_pk)
    submission = revision.submission

    if revision.source_type == RevisionSource.WYSIWYG:
        from apps.documents.wysiwyg_ingest import build_canonical_from_wysiwyg
        if not revision.wysiwyg_data:
            return {'error': 'WYSIWYG revision has no wysiwyg_data saved.'}
        canonical_data = build_canonical_from_wysiwyg(revision)
    else:
        # LaTeX path
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

    # ── Gather metadata ──────────────────────────────────────────
    from apps.journal.models import JournalConfig as _JC
    _journal  = _JC.objects.first()
    _jname    = _journal.name    if _journal else 'inAct'
    _issn_p   = _journal.issn_print   if _journal else ''
    _issn_o   = _journal.issn_online  if _journal else ''

    _doi = ''
    try:
        _doi = export.document.doi_deposit.doi or ''
    except Exception:
        pass

    _author      = submission.author
    _author_name = html_lib.escape(_author.display_name)
    _orcid       = html_lib.escape(_author.orcid_id or '')
    _institution = _dept = _country = ''
    try:
        _prof = _author.profile
        _institution = html_lib.escape(_prof.institution or '')
        _dept        = html_lib.escape(_prof.department  or '')
        _country     = html_lib.escape(_prof.country     or '')
    except Exception:
        pass

    _issue      = submission.issue
    _vol        = str(_issue.volume) if _issue else ''
    _num        = str(_issue.number) if _issue else ''
    _year       = str(_issue.year)   if _issue else ''
    _issue_title = html_lib.escape(_issue.title or '') if _issue else ''

    # ── Publication + acceptance dates (cover line + footer copyright year) ──
    _pub_dt = getattr(build, 'published_at', None) or getattr(build, 'built_at', None)
    from apps.editorial.models import DecisionType as _DecisionType
    _accept_decision = (
        submission.editorial_decisions
        .filter(decision_type=_DecisionType.ACCEPT)
        .order_by('-sent_at').first()
    )
    _approved_dt = _accept_decision.sent_at if _accept_decision else None
    _pub_date_str      = _pub_dt.strftime('%d %B %Y') if _pub_dt else ''
    _approved_date_str = _approved_dt.strftime('%d %B %Y') if _approved_dt else ''
    # Copyright year: the article's publication year, falling back to the issue year.
    _copyright_year = str(_pub_dt.year) if _pub_dt else _year

    _article_type = ''
    if hasattr(submission, 'get_article_type_display'):
        _article_type = submission.get_article_type_display()

    _abstract = html_lib.escape(submission.abstract or '')
    _keywords = ' · '.join(submission.keywords or [])

    # Running-header short strings for page margins
    _name_parts = _author.display_name.split()
    _short_auth = _name_parts[-1] if len(_name_parts) > 1 else _author.display_name
    _ttl_max    = 52
    _short_ttl  = submission.title[:_ttl_max] + ('…' if len(submission.title) > _ttl_max else '')

    # Footer left: a DOI/ISSN identifier when the article has one; otherwise left
    # blank (the journal name would just duplicate the © notice on the right).
    if _doi:
        _footer_l = f'https://doi.org/{_doi}'
    elif _issn_o:
        _footer_l = f'e-ISSN {_issn_o}'
    elif _issn_p:
        _footer_l = f'ISSN {_issn_p}'
    else:
        _footer_l = ''

    # Copyright holder is the journal, not a name token — deriving it from the
    # author's surname produced junk for accounts whose surname is a mail domain.
    # The year is the article's publication year.
    _copyright = f'© {_copyright_year} {_jname}' if _copyright_year else f'© {_jname}'

    def _css_str(s):
        """Escape a value for use inside a CSS single-quoted content: string."""
        return s.replace('\\', '\\\\').replace("'", "\\'")

    # ── @page rules — running header + footer on all pages ───────
    _page_css = f"""
    @page {{
      margin: 2.5cm 2cm 2.8cm 2cm;

      @top-left {{
        content: '{_css_str(_jname)}';
        font-family: Helvetica, Arial, sans-serif;
        font-size: 7.5pt; color: #999;
        border-bottom: 0.5pt solid #D0D0D0;
        padding-bottom: 5pt; vertical-align: bottom;
        width: 52%;
      }}
      @top-right {{
        content: '{_css_str(_short_auth)} — “{_css_str(_short_ttl)}”';
        font-family: Helvetica, Arial, sans-serif;
        font-size: 7.5pt; color: #999; font-style: italic;
        border-bottom: 0.5pt solid #D0D0D0;
        padding-bottom: 5pt; vertical-align: bottom;
        text-align: right; width: 48%;
      }}
      @bottom-left {{
        content: '{_css_str(_footer_l)}';
        font-family: Helvetica, Arial, sans-serif;
        font-size: 7pt; color: #aaa;
        border-top: 0.5pt solid #D0D0D0;
        padding-top: 5pt; vertical-align: top;
        width: 42%;
      }}
      @bottom-center {{
        content: counter(page) " / " counter(pages);
        font-family: Helvetica, Arial, sans-serif;
        font-size: 8.5pt; color: #888;
        border-top: 0.5pt solid #D0D0D0;
        padding-top: 5pt; vertical-align: top;
        text-align: center; width: 16%;
      }}
      @bottom-right {{
        content: '{_css_str(_copyright)}';
        font-family: Helvetica, Arial, sans-serif;
        font-size: 7pt; color: #aaa;
        border-top: 0.5pt solid #D0D0D0;
        padding-top: 5pt; vertical-align: top;
        text-align: right; width: 42%;
      }}
    }}
    /* First page: title block replaces running header */
    @page :first {{
      @top-left  {{ content: ''; border: none; padding: 0; }}
      @top-right {{ content: ''; border: none; padding: 0; }}
    }}
    """

    # ── Body / element styles (static — no f-string) ─────────────
    _body_css = """
    * { box-sizing: border-box; }
    body {
      font-family: 'Space Grotesk', 'Helvetica Neue', Arial, sans-serif;
      font-size: 11pt;
      line-height: 1.65;
      color: #21252B;
      margin: 0;
      text-align: justify;
    }

    /* ── Cover / title page ──────────────────────────── */
    .pdf-cover { margin-bottom: 2.2rem; }
    .pdf-cover__journal-bar {
      padding-bottom: 0.4rem;
      border-bottom: 2pt solid #FF4500;
      margin-bottom: 1.4rem;
      overflow: hidden;
    }
    .pdf-cover__journal-name {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 9pt; font-weight: bold;
      color: #FF4500; letter-spacing: 0.03em;
      float: left;
    }
    .pdf-cover__issue-ref {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 8.5pt; color: #888;
      float: right;
    }
    .pdf-cover__article-type {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 7.5pt; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.12em;
      color: #FF4500; margin: 0 0 0.8rem;
    }
    .pdf-cover__title {
      font-size: 22pt; font-weight: bold;
      line-height: 1.18; color: #111;
      margin: 0 0 0.5rem; text-align: left;
    }
    .pdf-cover__subtitle {
      font-size: 13.5pt; font-style: italic;
      color: #555; margin: 0 0 1.2rem; text-align: left;
    }
    .pdf-cover__author-name {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 11pt; font-weight: 600;
      color: #222; margin: 0 0 0.18rem;
    }
    .pdf-cover__author-affil {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 9.5pt; font-style: italic;
      color: #666; margin: 0 0 0.12rem;
    }
    .pdf-cover__dates {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 8.5pt; color: #888; margin: 0.2rem 0 0.12rem;
    }
    .pdf-cover__author-orcid {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 8.5pt; color: #999; margin: 0 0 0.8rem;
    }
    .pdf-cover__author-orcid a { color: #999; text-decoration: none; }
    .pdf-cover__ids {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 9pt; color: #666;
      margin: 0.2rem 0 0;
    }
    .pdf-cover__ids span { margin-right: 1.6rem; }
    .pdf-cover__ids a { color: #FF4500; text-decoration: none; }
    .pdf-cover__rule {
      border: none; border-top: 0.75pt solid #D0D0D0;
      margin: 1.1rem 0 1rem;
    }
    .pdf-cover__abs-label {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 7.5pt; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.1em;
      color: #999; margin: 0 0 0.3rem;
    }
    .pdf-cover__abstract {
      border-left: 2.5pt solid #FF4500;
      padding-left: 0.9rem;
      font-size: 10pt; line-height: 1.6;
      color: #333; margin-bottom: 0.65rem;
      text-align: justify;
    }
    .pdf-cover__keywords {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 9pt; color: #555; margin: 0;
    }
    .pdf-cover__keywords strong { color: #333; }
    .pdf-cover__bottom-rule {
      border: none; border-top: 2pt solid #FF4500;
      margin: 1.4rem 0 0;
    }

    /* ── Article body ────────────────────────────────── */
    .article-body { margin: 0; }
    /* Suppress rendered abstract/keywords/authors in body —
       they are already displayed in the cover block above  */
    .article-abstract { display: none; }
    .article-keywords { display: none; }
    .article-authors  { display: none; }
    h1 { font-size: 16pt; margin: 2rem 0 0.8rem; text-align: left; }
    h2 { font-size: 13pt; margin: 1.6rem 0 0.6rem; text-align: left; }
    h3 { font-size: 11pt; margin: 1.2rem 0 0.4rem; text-align: left; }
    p { margin: 0 0 0.8rem; }
    figure { margin: 1.5rem 0; text-align: center; }
    figcaption { font-size: 9pt; color: #6B6B6B; margin-top: 0.4rem;
                 font-style: italic; text-align: center; }
    /* max-height caps portrait/vertical media so a phone photo can't tower
       down the page; it scales to a landscape-like height and stays centred. */
    img { max-width: 100%; height: auto; max-height: 15cm; }
    figure.article-figure { text-align: center; }
    table { width: 100%; border-collapse: collapse; margin: 1.2rem 0; font-size: 10pt; }
    th { background: #f5f5f5; border-bottom: 2px solid #E5E5E5;
         padding: 0.4rem 0.6rem; text-align: left; }
    td { border-bottom: 1px solid #E5E5E5; padding: 0.4rem 0.6rem; text-align: left; }
    a { color: #FF4500; text-decoration: none; }
    .article-blockquote {
      margin-left: 36pt; margin-right: 36pt;
      font-style: italic; color: #444;
    }
    .article-blockquote p { margin: 0; }
    .article-cite { color: #21252B; text-decoration: none; }
    /* Footnotes — rendered as ENDNOTES in the PDF.
       WeasyPrint's `float: footnote` cannot reliably keep a note on the same
       page as its reference: when that page fills with body text it defers the
       note to the next page's footnote area instead of reflowing the body. To
       guarantee correct, predictable output we keep the in-text superscript
       marker (.fn-ref-num) and collect the note bodies into a "Notes" section
       at the end of the document (the .article-footnotes block, which the HTML
       renderer already emits). The inline note copies (.fn-note) are hidden.
       Numbering here is entirely from the HTML markers — no float:footnote, so
       WeasyPrint generates no competing counter and nothing is doubled. */
    .fn-wrap { display: inline; }
    .fn-ref-num { font-size: 0.7em; vertical-align: super; line-height: 0;
                  color: #FF4500; font-weight: bold; }
    .fn-note { display: none; }
    .article-footnotes {
      margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #E5E5E5;
    }
    .article-footnotes__title {
      font-size: 10pt; text-transform: uppercase; letter-spacing: 0.05em;
      color: #6B6B6B; margin-bottom: 0.6rem;
    }
    .article-footnotes__list { list-style: none; padding: 0; margin: 0; }
    .article-footnote {
      font-size: 9pt; margin-bottom: 0.4rem;
      padding-left: 1.4em; text-indent: -1.4em; line-height: 1.45;
    }
    .fn-note__num { font-weight: bold; color: #FF4500; margin-right: 0.3em; }
    .fn-back { display: none; }
    .para-num { display: none; }
    pre.article-verbatim {
      background: #f5f5f5; border: 1px solid #E5E5E5; border-radius: 3px;
      padding: 0.5rem 0.7rem; margin: 0.8rem 0;
      font-size: 8.5pt; line-height: 1.4; white-space: pre;
    }
    pre.article-verbatim code { background: none; padding: 0; font-size: inherit; }
    code { font-family: Courier, 'Courier New', monospace; font-size: 0.88em;
           background: #f5f5f5; padding: 0.1em 0.2em; border-radius: 2px; }
    .article-list { margin: 0.5rem 0 0.8rem 1.4rem; padding: 0; }
    .article-list li { margin-bottom: 0.25rem; line-height: 1.55; }
    .article-dl { margin: 0.5rem 0 0.8rem; }
    .article-dl dt { font-weight: bold; margin-top: 0.4rem; }
    .article-dl dd { margin-left: 1.5rem; margin-bottom: 0.2rem; }
    .article-bibliography { margin-top: 2rem; padding-top: 1rem;
                             border-top: 1px solid #E5E5E5; }
    .article-bibliography h2 { font-size: 10pt; text-transform: uppercase;
                                letter-spacing: 0.05em; color: #6B6B6B;
                                margin-bottom: 0.6rem; }
    .article-bibliography__list { list-style: none; padding: 0; margin: 0; }
    .bibliography-item { font-size: 9pt; margin-bottom: 0.5rem;
                         padding-left: 1.2em; text-indent: -1.2em;
                         line-height: 1.45; }
    .bib-title { font-style: italic; }
    .article-bibliography__note { font-size: 9pt; color: #6B6B6B; font-style: italic; }
    """

    base_css = _page_css + _body_css

    bookmark_css = """
    h1 { bookmark-level: 1; bookmark-label: content(); }
    h2 { bookmark-level: 2; bookmark-label: content(); }
    h3 { bookmark-level: 3; bookmark-label: content(); }
    a { color: #FF4500; text-decoration: underline; }
    .article-cite { text-decoration: none; }
    """ if interactive else ""

    media_placeholder_css = """
    .pdf-media-placeholder { margin: 1.5rem 0 0.25rem; }
    .pdf-media-box {
      display: block;
      border: 1px solid #D0D0D0;
      border-left: 3px solid #FF4500;
      background: #FAFAFA;
      padding: 0.6rem 1rem;
      font-family: Helvetica, Arial, sans-serif;
      font-size: 10pt; color: #6B6B6B;
    }
    .pdf-media-icon { font-size: 11pt; margin-right: 0.3em; }
    .pdf-media-label { font-style: italic; margin-right: 0.4em; }
    .pdf-media-filelink {
      color: #FF4500;
      font-style: normal;
      font-size: 9pt;
      word-break: break-all;
    }
    .pdf-media-link {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 8pt; color: #999; margin: 0 0 1.2rem 0;
    }
    .pdf-media-link a { color: #FF4500; }
    """

    # Pre-process HTML: replace <video>/<audio> with PDF-safe equivalents
    from django.conf import settings as _djsettings
    article_html, media_items = _preprocess_html_for_pdf(
        build.html_content, interactive, site_url=_djsettings.SITE_URL
    )

    if interactive and not media_items:
        media_items = _collect_media_items_from_assets(export.document, submission)

    # ── Build cover / title-page block ───────────────────────────
    # Issue / volume / year bar
    _issue_parts = []
    if _vol:
        _issue_parts.append(f'Vol.&#8239;{html_lib.escape(_vol)}')
    if _num:
        _issue_parts.append(f'No.&#8239;{html_lib.escape(_num)}')
    if _year:
        _issue_parts.append(html_lib.escape(_year))
    _issue_ref = ' &middot; '.join(_issue_parts)
    if _issue_title:
        _issue_ref += f' &mdash; {_issue_title}'

    # Affiliation line: Institution [, Department] [, Country]
    _affil_parts = [p for p in (_institution, _dept, _country) if p]
    _affil_line  = (
        f'<p class="pdf-cover__author-affil">{", ".join(_affil_parts)}</p>'
        if _affil_parts else ''
    )
    # Approved / Published dates line (below the affiliation)
    _date_bits = []
    if _approved_date_str:
        _date_bits.append(f'Approved on {_approved_date_str}')
    if _pub_date_str:
        _date_bits.append(f'Published on {_pub_date_str}')
    _dates_line = (
        f'<p class="pdf-cover__dates">{" &middot; ".join(_date_bits)}</p>'
        if _date_bits else ''
    )
    _orcid_line = (
        f'<p class="pdf-cover__author-orcid">ORCID:&#8239;'
        f'<a href="https://orcid.org/{_orcid}">{_orcid}</a></p>'
        if _orcid else ''
    )

    # Identifiers row: DOI, ISSNs
    _id_spans = []
    if _doi:
        _id_spans.append(
            f'<span class="pdf-cover__doi">'
            f'DOI:&#8239;<a href="https://doi.org/{html_lib.escape(_doi)}">'
            f'{html_lib.escape(_doi)}</a></span>'
        )
    if _issn_p:
        _id_spans.append(f'<span>ISSN&#8239;{html_lib.escape(_issn_p)} (print)</span>')
    if _issn_o:
        _id_spans.append(f'<span>ISSN&#8239;{html_lib.escape(_issn_o)} (online)</span>')
    _ids_html = (
        f'<p class="pdf-cover__ids">{"".join(_id_spans)}</p>'
        if _id_spans else ''
    )

    # Abstract + keywords block (only if abstract text is available)
    if _abstract:
        _abs_block = (
            f'<hr class="pdf-cover__rule">'
            f'<p class="pdf-cover__abs-label">Abstract</p>'
            f'<div class="pdf-cover__abstract"><p>{_abstract}</p></div>'
        )
        _kw_line = (
            f'<p class="pdf-cover__keywords">'
            f'<strong>Keywords:</strong>&#8239;{html_lib.escape(_keywords)}</p>'
            if _keywords else ''
        )
    else:
        _abs_block = _kw_line = ''

    _cover_html = f"""<div class="pdf-cover">
  <div class="pdf-cover__journal-bar">
    <span class="pdf-cover__journal-name">{html_lib.escape(_jname)}</span>
    {'<span class="pdf-cover__issue-ref">' + _issue_ref + '</span>' if _issue_ref else ''}
  </div>
  {'<p class="pdf-cover__article-type">' + html_lib.escape(_article_type) + '</p>' if _article_type else ''}
  <h1 class="pdf-cover__title">{html_lib.escape(submission.title)}</h1>
  {'<p class="pdf-cover__subtitle">' + html_lib.escape(submission.subtitle) + '</p>' if submission.subtitle else ''}
  <p class="pdf-cover__author-name">{_author_name}</p>
  {_affil_line}
  {_dates_line}
  {_orcid_line}
  {_ids_html}
  {_abs_block}
  {_kw_line}
  <hr class="pdf-cover__bottom-rule">
</div>"""

    html_doc = f"""<!DOCTYPE html>
<html lang="{html_lib.escape(submission.language)}">
<head>
<meta charset="utf-8">
<title>{html_lib.escape(submission.title)}</title>
<style>{base_css}{bookmark_css}{media_placeholder_css}</style>
</head>
<body>
{_cover_html}
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

    from django.conf import settings as _settings
    weasy = HTML(
        string=html_doc,
        base_url=_settings.SITE_URL,
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


@shared_task
def transcode_asset(asset_pk):
    """Transcode a video/audio SubmissionAsset into a protected HLS package.

    Runs on the dedicated `transcode` Celery queue (see CELERY_TASK_ROUTES).
    Output lands in MEDIA_ROOT/hls/<asset_pk>/ and is served only through the
    signed streaming view — never as a direct file.
    """
    import os
    from django.conf import settings
    from apps.submissions.models import SubmissionAsset
    from apps.production import transcode as _t

    asset = SubmissionAsset.objects.filter(pk=asset_pk).first()
    if not asset or asset.kind not in ('video', 'audio') or not asset.file:
        return {'skipped': True}
    if getattr(settings, 'USE_S3', False):
        # Transcoding reads from the local filesystem; skip on remote storage.
        return {'skipped': 's3'}

    asset.hls_status = SubmissionAsset.HLS_PROCESSING
    asset.hls_error = ''
    asset.save(update_fields=['hls_status', 'hls_error'])
    try:
        src = asset.file.path
        out_rel = f'hls/{asset.pk}'
        out_dir = os.path.join(settings.MEDIA_ROOT, out_rel)
        result = _t.transcode(src, out_dir, is_audio=(asset.kind == 'audio'),
                              ladder=getattr(settings, 'HLS_LADDER', None))
        asset.hls_master = f'{out_rel}/{result["master"]}'
        asset.duration_seconds = result.get('duration')
        asset.hls_status = SubmissionAsset.HLS_READY
        asset.save(update_fields=['hls_master', 'duration_seconds', 'hls_status'])
        return {'ok': True, 'master': asset.hls_master, 'renditions': result.get('renditions')}
    except Exception as e:  # noqa: BLE001 — record and surface, never crash the worker
        asset.hls_status = SubmissionAsset.HLS_ERROR
        asset.hls_error = str(e)[:2000]
        asset.save(update_fields=['hls_status', 'hls_error'])
        return {'error': str(e)}


@shared_task
def generate_submission_cover_derivatives(submission_pk):
    """Generate responsive WebP renditions for a submission's cover image.

    Runs on the `transcode` queue (see CELERY_TASK_ROUTES). Best-effort — the
    original cover is always the fallback (Submission.cover_url), so failures are
    non-fatal. Works on both local disk and S3 storage (generate_derivatives goes
    through default_storage), so there is no S3 skip here.
    """
    from apps.submissions.models import Submission
    from apps.submissions.imaging import generate_derivatives

    sub = Submission.objects.filter(pk=submission_pk).first()
    if not sub or not sub.cover_image:
        return {'skipped': True}
    info = generate_derivatives(sub.cover_image, role_hint='hero')
    sub.cover_derivatives = info.get('derivatives', {}) if info else {}
    sub.save(update_fields=['cover_derivatives'])
    return {'ok': True, 'count': len(sub.cover_derivatives)}
