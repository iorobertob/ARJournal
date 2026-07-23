"""
Canonical JSON → semantic HTML renderer.

Produces stable anchor IDs for reviewer annotation targeting.

Block types supported:
  heading, paragraph, blockquote, figure, media (video/audio),
  table, equation, footnotes_section, bibliography

Inline types supported:
  text, bold, italic, link, cite, footnote_ref, ref

Footnote display strategy:
  • Wide screens (CSS ≥ 1200 px): inline sidenotes float to the right margin
    via .fn-note { float: right } — the footnotes_section block is hidden.
  • Narrow screens: the .fn-note spans are hidden; the footnotes_section block
    at the bottom of the article becomes visible.

PDF (WeasyPrint):
  .fn-note uses float: footnote CSS — content is moved to the page footer area.
  The footnotes_section block is hidden via display: none in the PDF stylesheet.
"""
from django.utils.html import escape
from django.conf import settings


# ── Citation helpers (Cambridge author-date, "CambridgeA" style) ──────────────

def _last_name(full_name: str) -> str:
    """'Alice Smith' → 'Smith', 'Smith, Alice' → 'Smith', 'Rubio Marin, X' → 'Rubio Marin'."""
    if ',' in full_name:
        return full_name.split(',')[0].strip()
    parts = full_name.strip().split()
    return parts[-1] if parts else full_name


def _initials(given: str) -> str:
    """'David A' → 'DA', 'Robert' → 'R' (Cambridge initials: no periods/spaces)."""
    return ''.join(t[0].upper() for t in given.replace('.', ' ').split() if t)


def _author_ref_form(full_name: str) -> str:
    """Reference-list form: 'Attfield R', 'Kenny DA'. Corporate names pass through."""
    name = full_name.strip()
    if ',' in name:
        family, given = (p.strip() for p in name.split(',', 1))
    else:
        parts = name.split()
        if len(parts) < 2:
            return name  # single token → corporate/mononym, leave as-is
        family, given = parts[-1], ' '.join(parts[:-1])
    inits = _initials(given)
    return f'{family} {inits}'.strip() if inits else family


def _author_ref_list(authors: list) -> str:
    """'A, B and C' — no serial comma before 'and' (Cambridge)."""
    forms = [_author_ref_form(a) for a in authors if a]
    if not forms:
        return ''
    if len(forms) == 1:
        return forms[0]
    return ', '.join(forms[:-1]) + ' and ' + forms[-1]


def _cite_label(item: dict, display_year: str = None) -> str:
    """Cambridge in-text label: 'Cook 2013', 'Bicchieri and Xiao 1998',
    'Bhatti et al 2018' (note: 'et al' with no period). Uses display_year
    (which may carry an a/b/c suffix) when provided."""
    authors = item.get('authors', [])
    year = display_year if display_year is not None else str(item.get('year', '')).strip()
    if not authors:
        return item.get('citeKey', '')
    if len(authors) == 1:
        name_part = _last_name(authors[0])
    elif len(authors) == 2:
        name_part = f'{_last_name(authors[0])} and {_last_name(authors[1])}'
    else:
        name_part = f'{_last_name(authors[0])} et al'
    return f'{name_part} {year}' if year else name_part


def _prepare_citations(items: list) -> tuple[dict, list]:
    """Sort citation items alphabetically (by first-author surname, then year),
    assign a/b/c suffixes for same author+year, and build the in-text label map.

    Returns (cite_map, ordered_items) where cite_map maps citeKey → in-text label
    and each ordered item carries a '_displayYear' (year + optional suffix).
    """
    def sort_key(it):
        a = it.get('authors') or []
        surname = _last_name(a[0]).lower() if a else it.get('citeKey', '').lower()
        year = str(it.get('year', '') or '')
        return (surname, year, it.get('citeKey', ''))

    ordered = sorted(items, key=sort_key)

    # Assign a/b/c when the same lead surname + year occurs more than once.
    from collections import defaultdict
    groups = defaultdict(list)
    for it in ordered:
        a = it.get('authors') or []
        surname = _last_name(a[0]).lower() if a else it.get('citeKey', '')
        groups[(surname, str(it.get('year', '') or ''))].append(it)

    cite_map: dict[str, str] = {}
    for (surname, year), grp in groups.items():
        multi = len(grp) > 1 and year
        for i, it in enumerate(grp):
            suffix = chr(ord('a') + i) if multi else ''
            disp = f'{year}{suffix}' if year else ''
            it['_displayYear'] = disp
            ck = it.get('citeKey', '')
            if ck:
                cite_map[ck] = _cite_label(it, disp)
    return cite_map, ordered


def render_html(canonical_data: dict, submission=None, revision=None, reviewer_mode: bool = False) -> str:
    """Render the full article HTML from canonical JSON."""
    # Coalesce None → defaults: stored canonical JSON may carry explicit nulls
    # (e.g. metadata: null on some older/WYSIWYG docs), for which .get(key, {})
    # still returns None because the key is present.
    meta = canonical_data.get('metadata') or {}
    contributors = canonical_data.get('contributors') or []
    content = canonical_data.get('content') or []
    assets = {a['assetId']: a for a in (canonical_data.get('assets') or [])}

    # Resolve asset filenames → media URLs from the correct revision's files.
    # Priority: explicit revision arg → submission's current revision → skip.
    # Callers reviewing historical content must pass revision explicitly so that
    # asset URLs come from the version the reviewer annotated, not the latest.
    _revision = revision
    if _revision is None and submission is not None:
        try:
            _revision = submission.get_current_revision()
        except Exception:
            pass
    if _revision is not None:
        url_map: dict[str, str] = {}
        meta_map: dict[str, dict] = {}
        for sa in _revision.assets.all():
            if not sa.file:
                continue
            try:
                url_map[sa.original_filename] = sa.file.url
            except Exception:
                continue  # skip this one broken asset; others still resolve
            # Image sizing metadata (srcset) + protected streaming URLs (video/audio).
            hls_url, stream_url = '', ''
            if sa.kind in ('video', 'audio'):
                try:
                    from apps.production.media_access import signed_stream_url
                    # Protected progressive URL (never the raw file) as a fallback.
                    stream_url = signed_stream_url(sa.file.name)
                    if sa.hls_status == 'ready' and sa.hls_master:
                        hls_url = signed_stream_url(sa.hls_master)
                except Exception:
                    pass
            meta_map[sa.original_filename] = {
                'srcset': sa.srcset,
                'role': sa.role or '',
                'width': sa.intrinsic_width,
                'height': sa.intrinsic_height,
                'hls': hls_url,
                'stream': stream_url,
            }
        url_map_lower: dict[str, str] = {k.lower(): v for k, v in url_map.items()}
        meta_map_lower: dict[str, dict] = {k.lower(): v for k, v in meta_map.items()}
        for asset in assets.values():
            fname = asset.get('originalFilename', '')
            asset_meta = None  # NB: not `meta` — that holds the document metadata
            if fname in url_map:
                asset['resolvedUrl'] = url_map[fname]
                asset_meta = meta_map.get(fname)
            elif fname.lower() in url_map_lower:
                asset['resolvedUrl'] = url_map_lower[fname.lower()]
                asset_meta = meta_map_lower.get(fname.lower())
            if asset_meta:
                asset['resolvedSrcset'] = asset_meta['srcset']
                asset['resolvedRole'] = asset_meta['role']
                asset['resolvedWidth'] = asset_meta['width']
                asset['resolvedHeight'] = asset_meta['height']
                asset['resolvedHlsUrl'] = asset_meta['hls']
                asset['resolvedStreamUrl'] = asset_meta['stream']
            poster_fname = asset.get('posterImageRef', '')
            if poster_fname:
                if poster_fname in url_map:
                    asset['resolvedPosterUrl'] = url_map[poster_fname]
                elif poster_fname.lower() in url_map_lower:
                    asset['resolvedPosterUrl'] = url_map_lower[poster_fname.lower()]

    parts = ['<article class="article-body" data-doc-id="{}">'.format(
        escape(canonical_data.get('documentId', ''))
    )]

    # Authors line
    author_names = [c.get('displayName', '') for c in contributors if c.get('role') == 'author']
    if author_names:
        parts.append(
            '<div class="article-authors">'
            + ', '.join(escape(n) for n in author_names)
            + '</div>'
        )

    # Abstract
    for ab in meta.get('abstract', []):
        parts.append(
            f'<div class="article-abstract" id="abstract">'
            f'<h2>Abstract</h2>'
            f'<p>{escape(ab.get("text", ""))}</p>'
            f'</div>'
        )

    # Keywords
    keywords = meta.get('keywords', [])
    if keywords:
        kw_html = ', '.join(f'<span class="keyword">{escape(k)}</span>' for k in keywords)
        parts.append(f'<div class="article-keywords">{kw_html}</div>')

    # Build cite_map (Cambridge author-date labels, with a/b/c suffixes) and sort
    # the references alphabetically. The same display-year (incl. suffix) is carried
    # onto the bibliography block so in-text citations and the list agree.
    cite_map, _ordered_cites = _prepare_citations(
        (canonical_data.get('citations') or {}).get('items') or []
    )
    _disp_by_key = {it.get('citeKey'): it.get('_displayYear', '') for it in _ordered_cites}
    _order_by_key = {it.get('citeKey'): i for i, it in enumerate(_ordered_cites)}
    for _block in content:
        if _block.get('type') == 'bibliography' and _block.get('items'):
            for _it in _block['items']:
                _it['_displayYear'] = _disp_by_key.get(
                    _it.get('citeKey'), str(_it.get('year', '') or ''))
            _block['items'].sort(key=lambda it: _order_by_key.get(it.get('citeKey'), 10 ** 9))

    # Build label_map: 'fig:label' → figure number (sequential across all figures/media).
    label_map = _build_label_map(content)

    # Content blocks
    for block in content:
        html = _render_block(block, assets, cite_map, label_map, reviewer_mode=reviewer_mode)
        if html:
            parts.append(html)

    parts.append('</article>')
    return '\n'.join(parts)


def _build_label_map(blocks: list) -> dict:
    """Map label keys → sequential numbers for cross-references.

    Figures/media use 'fig:<label>' → int.
    Tables use the full label as stored (e.g. 'tab:daw_ambisonics') → int.
    """
    fig_num = 0
    tbl_num = 0
    label_map: dict[str, int] = {}
    for block in blocks:
        btype = block.get('type', '')
        if btype in ('figure', 'media'):
            label = block.get('label', '')
            if label:
                fig_num += 1
                label_map[f'fig:{label}'] = fig_num
        elif btype == 'table':
            label = block.get('label', '')
            if label:
                tbl_num += 1
                label_map[label] = tbl_num
    return label_map


def _render_table_from_latex(raw_latex: str, caption: str, bid: str) -> str:
    """
    Parse a LaTeX tabular environment into an HTML table.
    Handles \\toprule / \\midrule / \\bottomrule (booktabs) and \\hline,
    splits rows on \\\\ and cells on &.
    Returns an empty string if parsing fails.
    """
    import re as _re

    # Extract the tabular body (between \begin{tabular}{...} and \end{tabular})
    m = _re.search(r'\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}', raw_latex, _re.DOTALL)
    if not m:
        return ''
    body = m.group(1)

    # Remove booktabs rules and \hline — they are layout, not data
    body = _re.sub(r'\\(toprule|midrule|bottomrule|hline)\b', '', body)

    # Split on \\ (row separator); filter blank lines
    raw_rows = [r.strip() for r in _re.split(r'\\\\', body) if r.strip()]

    parsed_rows = []
    for raw_row in raw_rows:
        # Remove trailing LaTeX comments — but not escaped \%
        raw_row = _re.sub(r'(?<!\\)%.*$', '', raw_row, flags=_re.MULTILINE).strip()
        if not raw_row:
            continue
        cells = [c.strip() for c in raw_row.split('&')]
        # Unescape common LaTeX: \% → %, \& → &, \textit{x} → x, \textbf{x} → x
        cleaned = []
        for cell in cells:
            cell = _re.sub(r'\\%', '%', cell)
            cell = _re.sub(r'\\&', '&amp;', cell)
            cell = _re.sub(r'\\text(?:bf|it|rm|sc|sf|tt)\{([^}]*)\}', r'\1', cell)
            cell = _re.sub(r'\{([^}]*)\}', r'\1', cell)  # strip remaining braces
            cleaned.append(escape(cell.strip()))
        parsed_rows.append(cleaned)

    if not parsed_rows:
        return ''

    # First row becomes the header
    header_cells = ''.join(f'<th>{c}</th>' for c in parsed_rows[0])
    body_rows = ''.join(
        '<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>'
        for row in parsed_rows[1:]
    )
    cap_html = f'<caption>{caption}</caption>' if caption else ''
    return (
        f'<figure id="{bid}" class="article-table" data-block-id="{bid}">'
        f'<table>{cap_html}'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{body_rows}</tbody>'
        f'</table></figure>'
    )


def _doi_suffix(doi: str, url: str) -> str:
    """Cambridge DOI/URL suffix. DOI as an https link; else 'Available at <url>'."""
    if doi:
        d = doi.strip()
        if d.lower().startswith('http'):
            href, shown = d, d
        elif d.lower().startswith('doi:'):
            href, shown = f'https://doi.org/{d[4:].strip()}', d
        else:
            href = shown = f'https://doi.org/{d}'
        return f' <a href="{escape(href)}" class="article-cite__doi">{escape(shown)}</a>'
    if url:
        u = escape(url.strip())
        return f' Available at <a href="{u}">{u}</a>'
    return ''


def _format_bib_item(item: dict) -> str:
    """Format one reference in Cambridge author-date ("CambridgeA") style.

    e.g.  Attfield R (2003) *Environmental Ethics*. Cambridge: Polity Press.
          Chétima M (2019) You are where you build… *African Studies Review*
              **62**(3), 40-64. https://doi.org/10.1017/asr.2018.45.
    """
    type_ = (item.get('type') or 'misc').lower()
    authors = item.get('authors') or []
    editors = item.get('editors') or ([item['editor']] if item.get('editor') else [])
    disp_year = item.get('_displayYear') or str(item.get('year', '') or '')
    title = (item.get('title', '') or item.get('citeKey', '') or '').strip()
    journal = item.get('journal', '')
    volume = item.get('volume', '')
    number = item.get('number', '')
    pages = (item.get('pages', '') or '').replace('--', '–')
    publisher = item.get('publisher', '')
    booktitle = item.get('booktitle', '')
    address = item.get('address', '')
    edition = item.get('edition', '')
    series = item.get('series', '')
    school = item.get('school', '')
    institution = item.get('institution', '') or item.get('organization', '')
    howpublished = item.get('howpublished', '')
    note = item.get('note', '')

    # Lead: authors, or editors (with an "(ed)"/"(eds)" marker) when no author.
    editor_lead = not authors and editors
    lead = _author_ref_list(authors or editors)
    if editor_lead:
        lead += ' (ed)' if len(editors) == 1 else ' (eds)'
    lead_html = f'<strong>{escape(lead)}</strong>' if lead else ''
    year_html = f' ({escape(disp_year)})' if disp_year else ''

    def place_pub():
        parts = [p for p in (escape(address), escape(publisher)) if p]
        return ': '.join(parts) if len(parts) == 2 else (parts[0] if parts else '')

    if type_ == 'article':
        vol = ''
        if volume:
            vol = f' <strong>{escape(volume)}</strong>' + (f'({escape(number)})' if number else '')
        elif number:
            vol = f' ({escape(number)})'
        pg = f', {pages}' if pages else ''
        jrn = f' <em>{escape(journal)}</em>' if journal else ''
        body = f'{escape(title)}.{jrn}{vol}{pg}'
    elif type_ in ('incollection', 'inproceedings', 'conference'):
        if editors:
            marker = 'ed' if len(editors) == 1 else 'eds'
            in_clause = f'In {escape(_author_ref_list(editors))} ({marker}), '
        else:
            in_clause = 'In '
        body = f'{escape(title)}. {in_clause}<em>{escape(booktitle)}</em>'
        if series:
            body += f'. {escape(series)}'
        pp = place_pub()
        if pp:
            body += f'. {pp}'
        if pages:
            body += f', {pages}'
    elif type_ in ('phdthesis', 'mastersthesis'):
        kind = 'PhD dissertation' if type_ == 'phdthesis' else "Master's thesis"
        body = f'<em>{escape(title)}</em>. {kind}'
        if school:
            body += f', {escape(school)}'
    elif type_ == 'techreport':
        body = f'<em>{escape(title)}</em>'
        if institution:
            body += f'. {escape(institution)}'
    elif type_ == 'book':
        body = f'<em>{escape(title)}</em>' + (f', {escape(edition)}' if edition else '')
        if series:
            body += f'. {escape(series)}'
        pp = place_pub()
        if pp:
            body += f'. {pp}'
    else:  # misc / online / unpublished / manual / booklet / website
        body = f'<em>{escape(title)}</em>' if title else ''
        extra = escape(howpublished) or escape(institution) or escape(note)
        if extra:
            body = f'{body}. {extra}' if body else extra

    body = body.rstrip()
    if body and not body.endswith('.'):
        body += '.'
    result = f'{lead_html}{year_html} {body}{_doi_suffix(item.get("doi", ""), item.get("url", ""))}'.strip()
    return result if result.endswith('.') else result + '.'


def _render_block(
    block: dict,
    assets: dict,
    cite_map: dict | None = None,
    label_map: dict | None = None,
    reviewer_mode: bool = False,
) -> str:
    btype = block.get('type', 'paragraph')
    bid = escape(block.get('id', ''))
    cm = cite_map or {}
    lm = label_map or {}

    # ── Heading ───────────────────────────────────────────────────────────────
    if btype == 'heading':
        level = block.get('level', 2)
        text = escape(block.get('text', ''))
        return f'<h{level} id="{bid}" class="article-heading" data-block-id="{bid}">{text}</h{level}>'

    # ── Paragraph ─────────────────────────────────────────────────────────────
    if btype == 'paragraph':
        content = block.get('content', [])
        inner = ''.join(_render_inline(c, cm, lm) for c in content)
        anchor = block.get('anchor', {})
        para_num = anchor.get('paragraphNumber', '')
        return (
            f'<p id="{bid}" class="article-paragraph" data-block-id="{bid}" data-para="{para_num}">'
            f'{inner}'
            f'<span class="para-num" aria-hidden="true">{para_num}</span>'
            f'</p>'
        )

    # ── Blockquote (long quotation, 40+ words / 4+ lines) ────────────────────
    if btype == 'blockquote':
        content = block.get('content', [])
        inner = ''.join(_render_inline(c, cm, lm) for c in content)
        return (
            f'<blockquote id="{bid}" class="article-blockquote" data-block-id="{bid}">'
            f'<p>{inner}</p>'
            f'</blockquote>'
        )

    # ── Figure ────────────────────────────────────────────────────────────────
    if btype == 'figure':
        asset_ref = block.get('assetRef', '')
        asset = assets.get(asset_ref, {})
        caption = escape(block.get('caption', ''))
        alt = escape(block.get('altText', ''))
        credit = escape(block.get('credit', ''))
        src = _asset_url(asset)
        fig_label = block.get('label', '')
        anchor_id = f'fig:{fig_label}' if fig_label else bid
        fig_num = lm.get(f'fig:{fig_label}', 0) if fig_label else 0
        caption_prefix = f'Figure {fig_num}. ' if fig_num else ''
        credit_html = (
            f'<figcaption class="figure-credit">{credit}</figcaption>' if credit else ''
        )
        # Explicit \ARJlogo role in the source wins; else the auto-detected role.
        role = block.get('role') or asset.get('resolvedRole', '')
        if src:
            # Responsive srcset from generated derivatives (falls back to plain src).
            srcset = escape(asset.get('resolvedSrcset', ''))
            iw = asset.get('resolvedWidth')
            ih = asset.get('resolvedHeight')
            # Content column is ~820px; tell the browser so it picks the right rendition.
            srcset_attr = (
                f' srcset="{srcset}" sizes="(max-width: 860px) 100vw, 820px"'
                if srcset else ''
            )
            dim_attr = f' width="{iw}" height="{ih}"' if iw and ih else ''
            media_html = (
                f'<img src="{src}"{srcset_attr} alt="{alt}" loading="lazy"{dim_attr}>'
            )
        else:
            fname = escape(asset.get('originalFilename', 'image'))
            media_html = (
                f'<div class="media-placeholder media-placeholder--image">'
                f'<span class="media-placeholder__type">Image</span>'
                f'<span class="media-placeholder__filename">{fname}</span>'
                f'</div>'
            )
        fig_class = 'article-figure'
        if role == 'logo':
            fig_class += ' article-figure--logo'
        elif role == 'hero':
            fig_class += ' article-figure--full'
        return (
            f'<figure id="{escape(anchor_id)}" class="{fig_class}" data-block-id="{bid}">'
            f'{media_html}'
            f'<figcaption class="figure-caption">{caption_prefix}{caption}</figcaption>'
            f'{credit_html}'
            f'</figure>'
        )

    # ── Media (video / audio) ─────────────────────────────────────────────────
    if btype == 'media':
        media_type = block.get('mediaType', 'video')
        asset_ref = block.get('assetRef', '')
        asset = assets.get(asset_ref, {})
        caption = escape(block.get('caption', ''))
        src = _asset_url(asset)
        med_label = block.get('label', '')
        anchor_id = f'fig:{med_label}' if med_label else bid
        fname = escape(asset.get('originalFilename', ''))
        css_class = 'article-video' if media_type == 'video' else 'article-audio'

        if reviewer_mode:
            label = 'Video' if media_type == 'video' else 'Audio'
            ph_class = f'media-placeholder--{media_type}'
            return (
                f'<figure id="{escape(anchor_id)}" class="article-media {css_class}" data-block-id="{bid}">'
                f'<div class="media-placeholder {ph_class}">'
                f'<span class="media-placeholder__type">{label}</span>'
                f'<span class="media-placeholder__filename">{fname}</span>'
                f'</div>'
                f'<figcaption>{caption}</figcaption>'
                f'</figure>'
            )

        # Protected streaming: HLS when transcoded, else a signed progressive URL.
        # Never emit the raw /media/ file, and strip download/PiP affordances.
        hls_url = escape(asset.get('resolvedHlsUrl', ''))
        stream_url = escape(asset.get('resolvedStreamUrl', '')) or src
        deterrents = 'controlsList="nodownload noremoteplayback" disablePictureInPicture oncontextmenu="return false"'
        if media_type == 'video':
            poster = escape(asset.get('resolvedPosterUrl', ''))
            if hls_url:
                inner = (
                    f'<video controls preload="metadata" playsinline poster="{poster}" '
                    f'data-hls="{hls_url}" {deterrents}>'
                    f'Your browser does not support video.'
                    f'</video>'
                )
            else:
                inner = (
                    f'<video controls preload="metadata" playsinline poster="{poster}" '
                    f'data-protected {deterrents}>'
                    f'<source src="{stream_url}">'
                    f'Your browser does not support video.'
                    f'</video>'
                )
            return (
                f'<figure id="{escape(anchor_id)}" class="article-media article-video" data-block-id="{bid}">'
                f'{inner}'
                f'<figcaption>{caption}</figcaption>'
                f'</figure>'
            )
        if media_type == 'audio':
            if hls_url:
                inner = (
                    f'<audio controls preload="metadata" data-hls="{hls_url}" {deterrents}>'
                    f'Your browser does not support audio.'
                    f'</audio>'
                )
            else:
                inner = (
                    f'<audio controls preload="metadata" data-protected {deterrents}>'
                    f'<source src="{stream_url}">'
                    f'Your browser does not support audio.'
                    f'</audio>'
                )
            return (
                f'<figure id="{escape(anchor_id)}" class="article-media article-audio" data-block-id="{bid}">'
                f'{inner}'
                f'<figcaption>{caption}</figcaption>'
                f'</figure>'
            )

    # ── Table ─────────────────────────────────────────────────────────────────
    if btype == 'table':
        caption = escape(block.get('caption', ''))
        columns = block.get('columns', [])
        rows = block.get('rows', [])
        tbl_label = block.get('label', '')
        anchor_id = escape(tbl_label) if tbl_label else bid
        tbl_num = lm.get(tbl_label, 0) if tbl_label else 0
        caption_prefix = f'Table {tbl_num}. ' if tbl_num else ''
        if columns and rows:
            headers = ''.join(f'<th>{escape(c["label"])}</th>' for c in columns)
            body_rows = ''.join(
                '<tr>' + ''.join(f'<td>{escape(str(cell.get("value", "")))}</td>' for cell in row) + '</tr>'
                for row in rows
            )
            return (
                f'<figure id="{anchor_id}" class="article-table" data-block-id="{bid}">'
                f'<table><caption>{caption_prefix}{caption}</caption>'
                f'<thead><tr>{headers}</tr></thead><tbody>{body_rows}</tbody>'
                f'</table></figure>'
            )
        # Fallback: parse rawLatex when structured rows/columns are absent.
        raw = block.get('rawLatex', '')
        if raw:
            table_html = _render_table_from_latex(raw, caption, bid)
            if table_html:
                return table_html
        return (
            f'<figure id="{bid}" class="article-table" data-block-id="{bid}">'
            f'<table><caption>{caption}</caption></table>'
            f'</figure>'
        )

    # ── Verbatim code block ───────────────────────────────────────────────────
    if btype == 'verbatim':
        text = escape(block.get('text', ''))
        return (
            f'<pre id="{bid}" class="article-verbatim" data-block-id="{bid}">'
            f'<code>{text}</code>'
            f'</pre>'
        )

    # ── Description list ──────────────────────────────────────────────────────
    if btype == 'description_list':
        items = block.get('items', [])
        rows = ''.join(
            f'<dt>{escape(item.get("term", ""))}</dt>'
            f'<dd>{"".join(_render_inline(n, cm, lm) for n in item.get("body", []))}</dd>'
            for item in items
        )
        return f'<dl id="{bid}" class="article-dl" data-block-id="{bid}">{rows}</dl>'

    # ── Unordered / ordered list ──────────────────────────────────────────────
    if btype == 'list':
        tag = 'ol' if block.get('ordered') else 'ul'
        items_html = ''.join(
            '<li>' + ''.join(_render_inline(n, cm, lm) for n in nodes) + '</li>'
            for nodes in block.get('items', [])
        )
        return (
            f'<{tag} id="{bid}" class="article-list" data-block-id="{bid}">'
            f'{items_html}'
            f'</{tag}>'
        )

    # ── Equation ──────────────────────────────────────────────────────────────
    if btype == 'equation':
        latex = escape(block.get('latex', ''))
        return f'<div id="{bid}" class="article-equation" data-block-id="{bid}">\\({latex}\\)</div>'

    # ── Footnotes section (narrow-screen fallback / PDF) ──────────────────────
    if btype == 'footnotes_section':
        footnotes = block.get('footnotes', [])
        if not footnotes:
            return ''
        items_html = ''
        for fn in footnotes:
            fn_num = fn.get('number', '')
            fn_content = escape(''.join(c.get('text', '') for c in fn.get('content', [])))
            items_html += (
                f'<li id="fn-{fn_num}" class="article-footnote">'
                f'<span class="fn-note__num" aria-hidden="true">{fn_num}.</span> '
                f'{fn_content}'
                f'<a href="#fnref-{fn_num}" class="fn-back" aria-label="Back to text">&#8617;</a>'
                f'</li>'
            )
        return (
            f'<aside id="{bid}" class="article-footnotes" aria-label="Footnotes">'
            f'<h2 class="article-footnotes__title">Notes</h2>'
            f'<ol class="article-footnotes__list">{items_html}</ol>'
            f'</aside>'
        )

    # ── Bibliography ──────────────────────────────────────────────────────────
    if btype == 'bibliography':
        items = block.get('items', [])
        if not items:
            return (
                f'<section id="{bid}" class="article-bibliography" data-block-id="{bid}">'
                f'<h2>References</h2>'
                f'<p class="article-bibliography__note">'
                f'References are compiled from the submitted BibTeX file during production.'
                f'</p>'
                f'</section>'
            )
        ref_items = ''.join(
            f'<li id="ref-{escape(item.get("citeKey", ""))}" class="bibliography-item">'
            f'{_format_bib_item(item)}'
            f'</li>'
            for item in items
        )
        return (
            f'<section id="{bid}" class="article-bibliography" data-block-id="{bid}">'
            f'<h2>References</h2>'
            f'<ul class="article-bibliography__list">{ref_items}</ul>'
            f'</section>'
        )

    # Fallback
    return f'<div id="{bid}" class="article-block" data-block-id="{bid}"></div>'


def _render_inline(
    node: dict,
    cite_map: dict | None = None,
    label_map: dict | None = None,
) -> str:
    ntype = node.get('type', 'text')
    text = escape(node.get('text', ''))
    lm = label_map or {}

    if ntype == 'code':
        return f'<code>{escape(node.get("text", ""))}</code>'

    if ntype == 'text':
        return text

    if ntype == 'bold':
        return f'<strong>{text}</strong>'

    if ntype == 'italic':
        return f'<em>{text}</em>'

    if ntype == 'link':
        href = escape(node.get('href', '#'))
        return f'<a href="{href}">{text or href}</a>'

    if ntype == 'cite':
        ref_raw = node.get('ref', '')
        ref = escape(ref_raw)
        # Prefer the author-date label from cite_map; fall back to the raw key.
        label = escape((cite_map or {}).get(ref_raw) or node.get('text', ref_raw))
        return (
            f'<a href="#ref-{ref}" class="article-cite" data-ref="{ref}">'
            f'({label})'
            f'</a>'
        )

    if ntype == 'ref':
        # \ref{fig:label} or \ref{tab:label} cross-reference
        raw_target = node.get('target', '')
        target = escape(raw_target)
        num = lm.get(raw_target, 0)
        if num:
            prefix = 'Table' if raw_target.startswith('tab:') else 'Figure'
            link_text = f'{prefix} {num}'
        else:
            link_text = target
        return f'<a href="#{target}" class="article-figref">{link_text}</a>'

    if ntype == 'footnote_ref':
        fn_num = node.get('number', '')
        note_text = escape(node.get('noteText', ''))
        return (
            f'<span class="fn-wrap">'
            f'<sup class="fn-ref-num" id="fnref-{fn_num}" aria-describedby="fn-{fn_num}">'
            f'{fn_num}'
            f'</sup>'
            f'<span class="fn-note" id="fn-{fn_num}" role="note">'
            f'<span class="fn-note__num" aria-hidden="true">{fn_num}.</span> {note_text}'
            f'</span>'
            f'</span>'
        )

    return text


def _asset_url(asset: dict) -> str:
    """Return the resolved media URL for an asset, or '' if not available."""
    if not asset:
        return ''
    return escape(asset.get('resolvedUrl', ''))


def build_toc(canonical_data: dict) -> list[dict]:
    """Build table of contents from heading blocks."""
    return [
        {'id': block['id'], 'text': block.get('text', ''), 'level': block.get('level', 1)}
        for block in canonical_data.get('content', [])
        if block.get('type') == 'heading'
    ]
