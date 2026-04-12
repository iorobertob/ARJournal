"""
Canonical JSON → semantic HTML renderer.

Produces stable anchor IDs for reviewer annotation targeting.

Block types supported:
  heading, paragraph, blockquote, figure, media (video/audio),
  table, equation, footnotes_section, bibliography

Inline types supported:
  text, bold, italic, link, cite, footnote_ref

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


def render_html(canonical_data: dict, submission=None) -> str:
    """Render the full article HTML from canonical JSON."""
    meta = canonical_data.get('metadata', {})
    contributors = canonical_data.get('contributors', [])
    content = canonical_data.get('content', [])
    assets = {a['assetId']: a for a in canonical_data.get('assets', [])}

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

    # Content blocks
    for block in content:
        html = _render_block(block, assets)
        if html:
            parts.append(html)

    parts.append('</article>')
    return '\n'.join(parts)


def _render_block(block: dict, assets: dict) -> str:
    btype = block.get('type', 'paragraph')
    bid = escape(block.get('id', ''))

    # ── Heading ───────────────────────────────────────────────────────────────
    if btype == 'heading':
        level = block.get('level', 2)
        text = escape(block.get('text', ''))
        return f'<h{level} id="{bid}" class="article-heading" data-block-id="{bid}">{text}</h{level}>'

    # ── Paragraph ─────────────────────────────────────────────────────────────
    if btype == 'paragraph':
        content = block.get('content', [])
        inner = ''.join(_render_inline(c) for c in content)
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
        inner = ''.join(_render_inline(c) for c in content)
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
        credit_html = (
            f'<figcaption class="figure-credit">{credit}</figcaption>' if credit else ''
        )
        return (
            f'<figure id="{bid}" class="article-figure" data-block-id="{bid}">'
            f'<img src="{src}" alt="{alt}" loading="lazy">'
            f'<figcaption class="figure-caption">{caption}</figcaption>'
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

        if media_type == 'video':
            poster = escape(asset.get('posterImageRef', ''))
            return (
                f'<figure id="{bid}" class="article-media article-video" data-block-id="{bid}">'
                f'<video controls preload="metadata" poster="{poster}">'
                f'<source src="{src}">'
                f'Your browser does not support video.'
                f'</video>'
                f'<figcaption>{caption}</figcaption>'
                f'</figure>'
            )
        if media_type == 'audio':
            return (
                f'<figure id="{bid}" class="article-media article-audio" data-block-id="{bid}">'
                f'<audio controls preload="metadata">'
                f'<source src="{src}">'
                f'Your browser does not support audio.'
                f'</audio>'
                f'<figcaption>{caption}</figcaption>'
                f'</figure>'
            )

    # ── Table ─────────────────────────────────────────────────────────────────
    if btype == 'table':
        caption = escape(block.get('caption', ''))
        columns = block.get('columns', [])
        rows = block.get('rows', [])
        if columns and rows:
            headers = ''.join(f'<th>{escape(c["label"])}</th>' for c in columns)
            body_rows = ''.join(
                '<tr>' + ''.join(f'<td>{escape(str(cell.get("value", "")))}</td>' for cell in row) + '</tr>'
                for row in rows
            )
            return (
                f'<figure id="{bid}" class="article-table" data-block-id="{bid}">'
                f'<table><caption>{caption}</caption>'
                f'<thead><tr>{headers}</tr></thead><tbody>{body_rows}</tbody>'
                f'</table></figure>'
            )
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
            f'<dd>{"".join(_render_inline(n) for n in item.get("body", []))}</dd>'
            for item in items
        )
        return f'<dl id="{bid}" class="article-dl" data-block-id="{bid}">{rows}</dl>'

    # ── Unordered / ordered list ──────────────────────────────────────────────
    if btype == 'list':
        tag = 'ol' if block.get('ordered') else 'ul'
        items_html = ''.join(
            '<li>' + ''.join(_render_inline(n) for n in nodes) + '</li>'
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
        ref_items = ''
        for item in items:
            ck = escape(item.get('citeKey', ''))
            title = escape(item.get('title', '') or ck)
            authors_list = item.get('authors', [])
            authors_str = escape(', '.join(authors_list)) if authors_list else ''
            year = escape(str(item.get('year', '')))
            doi = item.get('doi', '')
            doi_html = (
                f' <a href="https://doi.org/{escape(doi)}" class="article-cite__doi">'
                f'doi:{escape(doi)}</a>'
            ) if doi else ''
            ref_items += (
                f'<li id="ref-{ck}" class="bibliography-item">'
                f'{authors_str}{(" (" + year + "). ") if year else " "}'
                f'<span class="bib-title">{title}</span>'
                f'{doi_html}'
                f'</li>'
            )
        return (
            f'<section id="{bid}" class="article-bibliography" data-block-id="{bid}">'
            f'<h2>References</h2>'
            f'<ol class="article-bibliography__list">{ref_items}</ol>'
            f'</section>'
        )

    # Fallback
    return f'<div id="{bid}" class="article-block" data-block-id="{bid}"></div>'


def _render_inline(node: dict) -> str:
    ntype = node.get('type', 'text')
    text = escape(node.get('text', ''))

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
        ref = escape(node.get('ref', ''))
        label = escape(node.get('text', ref))
        return (
            f'<a href="#ref-{ref}" class="article-cite" data-ref="{ref}">'
            f'({label})'
            f'</a>'
        )

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
    """Build a URL for an asset. Actual URL resolution happens at template level."""
    if not asset:
        return ''
    return ''


def build_toc(canonical_data: dict) -> list[dict]:
    """Build table of contents from heading blocks."""
    return [
        {'id': block['id'], 'text': block.get('text', ''), 'level': block.get('level', 1)}
        for block in canonical_data.get('content', [])
        if block.get('type') == 'heading'
    ]
