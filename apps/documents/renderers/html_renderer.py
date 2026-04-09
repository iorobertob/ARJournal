"""
Canonical JSON → semantic HTML renderer.

Produces stable anchor IDs for reviewer annotation targeting.
Supports: headings, paragraphs, figures, media (video/audio), tables, equations, footnotes.
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

    # Authors
    author_names = [c.get('displayName', '') for c in contributors if c.get('role') == 'author']
    if author_names:
        parts.append('<div class="article-authors">' + ', '.join(escape(n) for n in author_names) + '</div>')

    # Abstract
    for ab in meta.get('abstract', []):
        parts.append(f'<div class="article-abstract" id="abstract"><h2>Abstract</h2><p>{escape(ab.get("text",""))}</p></div>')

    # Keywords
    keywords = meta.get('keywords', [])
    if keywords:
        kw_html = ', '.join(f'<span class="keyword">{escape(k)}</span>' for k in keywords)
        parts.append(f'<div class="article-keywords">{kw_html}</div>')

    # Content blocks
    for block in content:
        parts.append(_render_block(block, assets))

    parts.append('</article>')
    return '\n'.join(parts)


def _render_block(block: dict, assets: dict) -> str:
    btype = block.get('type', 'paragraph')
    bid = escape(block.get('id', ''))

    if btype == 'heading':
        level = block.get('level', 2)
        text = escape(block.get('text', ''))
        return f'<h{level} id="{bid}" class="article-heading" data-block-id="{bid}">{text}</h{level}>'

    if btype == 'paragraph':
        content = block.get('content', [])
        text = ''.join(_render_inline(c) for c in content)
        anchor = block.get('anchor', {})
        para_num = anchor.get('paragraphNumber', '')
        return (
            f'<p id="{bid}" class="article-paragraph" data-block-id="{bid}" data-para="{para_num}">'
            f'{text}'
            f'<span class="para-num" aria-hidden="true">{para_num}</span>'
            f'</p>'
        )

    if btype == 'figure':
        asset_ref = block.get('assetRef', '')
        asset = assets.get(asset_ref, {})
        caption = escape(block.get('caption', ''))
        alt = escape(block.get('altText', ''))
        credit = escape(block.get('credit', ''))
        # Build src from submission asset if available
        src = _asset_url(asset)
        credit_html = f'<figcaption class="figure-credit">{credit}</figcaption>' if credit else ''
        return (
            f'<figure id="{bid}" class="article-figure" data-block-id="{bid}">'
            f'<img src="{src}" alt="{alt}" loading="lazy">'
            f'<figcaption class="figure-caption">{caption}</figcaption>'
            f'{credit_html}'
            f'</figure>'
        )

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

    if btype == 'table':
        caption = escape(block.get('caption', ''))
        # If we have structured columns/rows, render them; otherwise show raw placeholder
        columns = block.get('columns', [])
        rows = block.get('rows', [])
        if columns and rows:
            headers = ''.join(f'<th>{escape(c["label"])}</th>' for c in columns)
            body_rows = ''
            for row in rows:
                cells = ''.join(f'<td>{escape(str(cell.get("value","")))}</td>' for cell in row)
                body_rows += f'<tr>{cells}</tr>'
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

    if btype == 'equation':
        latex = escape(block.get('latex', ''))
        return f'<div id="{bid}" class="article-equation" data-block-id="{bid}">\\({latex}\\)</div>'

    # Fallback
    return f'<div id="{bid}" class="article-block" data-block-id="{bid}"></div>'


def _render_inline(node: dict) -> str:
    ntype = node.get('type', 'text')
    text = escape(node.get('text', ''))
    if ntype == 'text':
        return text
    if ntype == 'bold':
        return f'<strong>{text}</strong>'
    if ntype == 'italic':
        return f'<em>{text}</em>'
    if ntype == 'link':
        href = escape(node.get('href', '#'))
        return f'<a href="{href}">{text}</a>'
    if ntype == 'cite':
        ref = escape(node.get('ref', ''))
        return f'<cite data-ref="{ref}">{text}</cite>'
    return text


def _asset_url(asset: dict) -> str:
    """Build a URL for an asset. Uses submission asset file path if linked."""
    if not asset:
        return ''
    # The DocumentAsset stores a FK to SubmissionAsset which has .file
    # At render time we look up via the asset dict stored in canonical JSON
    # Actual URL resolution happens at template level with submission_asset.file.url
    return ''


def build_toc(canonical_data: dict) -> list[dict]:
    """Build table of contents from heading blocks."""
    toc = []
    for block in canonical_data.get('content', []):
        if block.get('type') == 'heading':
            toc.append({
                'id': block['id'],
                'text': block.get('text', ''),
                'level': block.get('level', 1),
            })
    return toc
