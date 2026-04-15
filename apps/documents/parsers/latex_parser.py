"""
LaTeX → Canonical JSON parser.

Handles the arjournal.cls custom macros:
  \\ARJfigure{file}{caption}{alttext}
  \\ARJvideo{file}{caption}{poster}{transcript}
  \\ARJaudio{file}{caption}{transcript}
  \\ARJblindreview  (blind mode flag)

Inline markup handled:
  \\textbf{} \\textit{} \\emph{} → bold / italic
  \\enquote{} \\ARJquote{} → "curly-quoted" text
  \\cite{} \\citep{} \\citet{} → citation references
  \\footnote{} → sidenote refs + footnotes_section block
  \\url{} \\href{}{} → hyperlinks

Block environments handled:
  \\begin{ARJblockquote} / \\begin{quote} / \\begin{quotation}

Returns a canonical JSON dict matching canonical_document_schema_spec.md.
"""
import re
import uuid
from typing import Any


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uid(prefix: str, counters: dict) -> str:
    counters[prefix] = counters.get(prefix, 0) + 1
    return f'{prefix}_{counters[prefix]:03d}'


def _strip_comments(text: str) -> str:
    """Remove LaTeX line comments (% … end-of-line) but not escaped \\%."""
    return re.sub(r'(?<!\\)%[^\n]*', '', text).strip()


def _extract_macro(text: str, macro: str) -> str | None:
    """Extract the first {…} argument of a \\macro{arg} call."""
    pattern = rf'\\{re.escape(macro)}\{{([^}}]*)\}}'
    m = re.search(pattern, text)
    return _strip_comments(m.group(1)) if m else None


def _extract_balanced_arg(text: str, pos: int) -> tuple[str, int]:
    """
    Extract content inside balanced braces starting at pos (must be '{').
    Returns (content_string, index_after_closing_brace).
    Handles nested braces and escaped characters.
    """
    depth = 0
    buf: list[str] = []
    i = pos
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '\\' and i + 1 < n:
            buf.append(ch)
            buf.append(text[i + 1])
            i += 2
            continue
        if ch == '{':
            depth += 1
            if depth > 1:
                buf.append(ch)
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return ''.join(buf), i + 1
            buf.append(ch)
        else:
            buf.append(ch)
        i += 1
    return ''.join(buf), i  # unmatched brace — return what we have


# ── Inline command registry ───────────────────────────────────────────────────

_INLINE_CMDS = frozenset({
    'textbf', 'textit', 'textsl', 'emph',
    'enquote', 'ARJquote',
    'cite', 'citep', 'citet', 'citealp', 'citealt',
    'footnote',
    'texttt', 'textrm', 'textsc', 'textup', 'underline',
    'url', 'href',
    'verb',
})

# Commands whose output is stripped but don't raise an error
_STRIP_CMDS = re.compile(
    r'\\(?:bibliographystyle|bibliography|label|vspace|hspace|noindent|medskip'
    r'|bigskip|smallskip|clearpage|newpage|pagebreak|newline)\*?\{[^}]*\}'
    r'|\\(?:makearjtitle|ARJprintdeclarations|clearpage|newpage|pagebreak|newline)\b'
)


# ── Inline parser ─────────────────────────────────────────────────────────────

def _parse_inline_content(
    text: str,
    footnote_list: list,
    cite_keys: set,
    counters: dict,
    sec_id: str,
) -> list[dict]:
    """
    Parse paragraph / blockquote text into a list of inline node dicts.
    Accumulates footnote blocks into footnote_list and cite keys into cite_keys.
    """
    nodes: list[dict] = []
    buf: list[str] = []
    i = 0
    n = len(text)

    def flush_buf() -> None:
        nonlocal buf
        raw = re.sub(r'[ \t]+', ' ', ''.join(buf)).strip('\n')
        if raw:
            nodes.append({'type': 'text', 'text': raw})
        buf = []

    while i < n:
        ch = text[i]

        # LaTeX comment — skip to end of line
        if ch == '%':
            while i < n and text[i] != '\n':
                i += 1
            continue

        # Possible backslash command
        if ch == '\\':
            j = i + 1
            if j >= n:
                buf.append(ch)
                i += 1
                continue
            nxt = text[j]
            # Non-alpha special escapes
            if not nxt.isalpha():
                if nxt == '\\':
                    buf.append('\n')
                elif nxt in ('{', '}', '%', '&', '$', '#', '_', '^', '~'):
                    buf.append(nxt)
                # else: unknown — skip silently
                i += 2
                continue
            # Extract command name
            k = j
            while k < n and text[k].isalpha():
                k += 1
            cmd = text[j:k]

            if cmd not in _INLINE_CMDS:
                i = k  # skip unknown command name
                continue

            # Skip whitespace between command name and first brace
            p = k
            while p < n and text[p] in ' \t':
                p += 1

            # Optional argument [page] for \\cite variants
            opt_arg = ''
            if cmd in ('cite', 'citep', 'citet', 'citealp', 'citealt') and p < n and text[p] == '[':
                bracket_end = text.find(']', p + 1)
                if bracket_end != -1:
                    opt_arg = text[p + 1:bracket_end]
                    p = bracket_end + 1
                    while p < n and text[p] in ' \t':
                        p += 1

            # \\verb|content| — delimiter is the char immediately after command name
            if cmd == 'verb':
                if k < n:
                    delim = text[k]
                    end_pos = text.find(delim, k + 1)
                    if end_pos == -1:
                        end_pos = text.find('\n', k + 1)
                        if end_pos == -1:
                            end_pos = n
                    verb_content = text[k + 1:end_pos]
                    flush_buf()
                    nodes.append({'type': 'code', 'text': verb_content})
                    i = end_pos + 1
                else:
                    i = k
                continue

            # \\href{url}{text} needs two brace args
            if cmd == 'href':
                if p < n and text[p] == '{':
                    href_val, p2 = _extract_balanced_arg(text, p)
                    while p2 < n and text[p2] in ' \t':
                        p2 += 1
                    if p2 < n and text[p2] == '{':
                        link_text, end = _extract_balanced_arg(text, p2)
                    else:
                        link_text, end = href_val, p2
                    flush_buf()
                    nodes.append({'type': 'link', 'href': href_val.strip(), 'text': link_text.strip()})
                    i = end
                else:
                    i = p
                continue

            if p < n and text[p] == '{':
                arg, end = _extract_balanced_arg(text, p)
                flush_buf()

                if cmd == 'textbf':
                    nodes.append({'type': 'bold', 'text': arg})
                elif cmd in ('textit', 'textsl', 'emph'):
                    nodes.append({'type': 'italic', 'text': arg})
                elif cmd in ('enquote', 'ARJquote'):
                    # Curly typographic quotation marks
                    nodes.append({'type': 'text', 'text': f'\u201c{arg}\u201d'})
                elif cmd in ('cite', 'citep', 'citet', 'citealp', 'citealt'):
                    keys = [ck.strip() for ck in arg.split(',')]
                    cite_keys.update(keys)
                    label = opt_arg if opt_arg else arg
                    nodes.append({'type': 'cite', 'ref': keys[0], 'keys': keys, 'text': label})
                elif cmd == 'footnote':
                    fn_num = counters.get('fn', 0) + 1
                    counters['fn'] = fn_num
                    fn_id = _uid('blk_fn', counters)
                    note_text = re.sub(r'%[^\n]*', '', arg).strip()
                    footnote_list.append({
                        'id': fn_id,
                        'type': 'footnote',
                        'number': fn_num,
                        'content': [{'type': 'text', 'text': note_text}],
                        'sectionId': sec_id,
                    })
                    nodes.append({
                        'type': 'footnote_ref',
                        'footnoteId': fn_id,
                        'number': fn_num,
                        'noteText': note_text,
                    })
                elif cmd == 'texttt':
                    nodes.append({'type': 'code', 'text': arg})
                elif cmd in ('textrm', 'textsc', 'textup', 'underline'):
                    nodes.append({'type': 'text', 'text': arg})
                elif cmd == 'url':
                    url = arg.strip()
                    nodes.append({'type': 'link', 'href': url, 'text': url})

                i = end
            else:
                i = p  # no {arg} found — skip
            continue

        buf.append(ch)
        i += 1

    flush_buf()
    # Drop empty text nodes that crept in
    return [nd for nd in nodes if nd['type'] != 'text' or nd.get('text', '').strip()]


# ── Section content processor ─────────────────────────────────────────────────

def _parse_section_content(
    content: str,
    sec_id: str,
    blocks: list,
    assets: list,
    counters: dict,
    footnote_list: list,
    cite_keys: set,
) -> None:
    """
    Process section content in document order, preserving element sequence.
    Handles: blockquotes, figures, video, audio, tables, inline markup.
    """
    segments: list[tuple[int, int, str, Any]] = []

    # ── Verbatim environments (must be added first so inner LaTeX is not parsed) ─
    for m in re.finditer(r'\\begin\{verbatim\}(.*?)\\end\{verbatim\}', content, re.DOTALL):
        segments.append((m.start(), m.end(), 'verbatim', m.group(1)))

    # ── Description lists ─────────────────────────────────────────────────────
    for m in re.finditer(r'\\begin\{description\}(.*?)\\end\{description\}', content, re.DOTALL):
        segments.append((m.start(), m.end(), 'description', m.group(1)))

    # ── Unordered and ordered lists ───────────────────────────────────────────
    for list_env in ('itemize', 'enumerate'):
        for m in re.finditer(
            rf'\\begin\{{{list_env}\}}(.*?)\\end\{{{list_env}\}}', content, re.DOTALL
        ):
            segments.append((m.start(), m.end(), f'list_{list_env}', m.group(1)))

    # ── Blockquote environments ───────────────────────────────────────────────
    for env in ('ARJblockquote', 'quotation', 'quote'):
        pat = re.compile(
            rf'\\begin\{{{re.escape(env)}\}}(.*?)\\end\{{{re.escape(env)}\}}',
            re.DOTALL,
        )
        for m in pat.finditer(content):
            segments.append((m.start(), m.end(), 'blockquote', m.group(1)))

    # ── \ARJfigure{file}{caption}{alt} ───────────────────────────────────────
    for m in re.finditer(r'\\ARJfigure\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}', content):
        segments.append((m.start(), m.end(), 'figure', (m.group(1), m.group(2), m.group(3))))

    # ── \ARJvideo{file}{caption}{poster}{transcript} ──────────────────────────
    for m in re.finditer(r'\\ARJvideo\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}', content):
        segments.append((m.start(), m.end(), 'video',
                         (m.group(1), m.group(2), m.group(3), m.group(4))))

    # ── \ARJaudio{file}{caption}{transcript} ─────────────────────────────────
    for m in re.finditer(r'\\ARJaudio\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}', content):
        segments.append((m.start(), m.end(), 'audio',
                         (m.group(1), m.group(2), m.group(3))))

    # ── table environments ────────────────────────────────────────────────────
    tbl_pat = re.compile(
        r'\\begin\{table\}(?:\[[^\]]*\])?.*?\\caption\{([^}]*)\}.*?'
        r'\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}.*?\\end\{table\}',
        re.DOTALL,
    )
    for m in tbl_pat.finditer(content):
        segments.append((m.start(), m.end(), 'table', (m.group(1).strip(), m.group(0))))

    # Sort by start; drop overlapping segments (invalid LaTeX, shouldn't happen)
    segments.sort(key=lambda s: s[0])
    clean_segs: list[tuple[int, int, str, Any]] = []
    fence = 0
    for seg in segments:
        if seg[0] >= fence:
            clean_segs.append(seg)
            fence = seg[1]
    segments = clean_segs

    # ── Process in document order ─────────────────────────────────────────────
    cursor = 0
    para_num = counters.setdefault(f'_p_{sec_id}', 0)

    for (start, end, kind, data) in segments:
        # Paragraphs in the text before this structural element
        para_num = _add_paragraphs(
            content[cursor:start], sec_id, blocks, counters, footnote_list, cite_keys, para_num
        )

        if kind == 'verbatim':
            pre_id = _uid('blk_pre', counters)
            blocks.append({
                'id': pre_id,
                'type': 'verbatim',
                'text': data.strip('\n'),
                'sectionId': sec_id,
            })

        elif kind == 'description':
            dl_id = _uid('blk_dl', counters)
            items = []
            for im in re.finditer(
                r'\\item\[([^\]]*)\](.*?)(?=\\item\[|\Z)', data.strip(), re.DOTALL
            ):
                term = im.group(1).strip()
                body_nodes = _parse_inline_content(
                    _strip_comments(im.group(2).strip()),
                    footnote_list, cite_keys, counters, sec_id,
                )
                items.append({'term': term, 'body': body_nodes})
            blocks.append({
                'id': dl_id,
                'type': 'description_list',
                'items': items,
                'sectionId': sec_id,
            })

        elif kind in ('list_itemize', 'list_enumerate'):
            list_id = _uid('blk_list', counters)
            ordered = kind == 'list_enumerate'
            items = []
            # Split on \item; first chunk is pre-first-item (empty/whitespace)
            for chunk in re.split(r'\\item\b\s*', data)[1:]:
                chunk = _strip_comments(chunk.strip())
                if not chunk:
                    continue
                item_nodes = _parse_inline_content(
                    chunk, footnote_list, cite_keys, counters, sec_id
                )
                if item_nodes:
                    items.append(item_nodes)
            blocks.append({
                'id': list_id,
                'type': 'list',
                'ordered': ordered,
                'items': items,
                'sectionId': sec_id,
            })

        elif kind == 'blockquote':
            bq_id = _uid('blk_bq', counters)
            inner_nodes = _parse_inline_content(
                data.strip(), footnote_list, cite_keys, counters, sec_id
            )
            blocks.append({
                'id': bq_id,
                'type': 'blockquote',
                'content': inner_nodes,
                'sectionId': sec_id,
            })

        elif kind == 'figure':
            fname, caption, alt = data
            asset_id = _uid('asset_img', counters)
            fig_id = _uid('blk_fig', counters)
            assets.append({
                'assetId': asset_id,
                'kind': 'image',
                'originalFilename': fname.strip(),
                'rights': {'publicAccess': True, 'reviewAccess': True, 'downloadAllowed': True},
            })
            blocks.append({
                'id': fig_id,
                'type': 'figure',
                'assetRef': asset_id,
                'caption': caption.strip(),
                'altText': alt.strip(),
                'sectionId': sec_id,
            })

        elif kind == 'video':
            fname, caption, poster, transcript = data
            asset_id = _uid('asset_vid', counters)
            med_id = _uid('blk_med', counters)
            assets.append({
                'assetId': asset_id,
                'kind': 'video',
                'originalFilename': fname.strip(),
                'posterImageRef': poster.strip(),
                'transcriptRef': transcript.strip(),
                'rights': {'publicAccess': True, 'reviewAccess': True, 'downloadAllowed': False},
                'streamingPolicy': 'authenticated_stream_only',
            })
            blocks.append({
                'id': med_id,
                'type': 'media',
                'mediaType': 'video',
                'assetRef': asset_id,
                'caption': caption.strip(),
                'timecodeAnchors': True,
                'sectionId': sec_id,
            })

        elif kind == 'audio':
            fname, caption, transcript = data
            asset_id = _uid('asset_aud', counters)
            med_id = _uid('blk_med', counters)
            assets.append({
                'assetId': asset_id,
                'kind': 'audio',
                'originalFilename': fname.strip(),
                'transcriptRef': transcript.strip(),
                'rights': {'publicAccess': True, 'reviewAccess': True, 'downloadAllowed': False},
            })
            blocks.append({
                'id': med_id,
                'type': 'media',
                'mediaType': 'audio',
                'assetRef': asset_id,
                'caption': caption.strip(),
                'sectionId': sec_id,
            })

        elif kind == 'table':
            caption, raw_latex = data
            tbl_id = _uid('blk_tbl', counters)
            columns, rows = _parse_tabular(raw_latex)
            blocks.append({
                'id': tbl_id,
                'type': 'table',
                'caption': caption,
                'columns': columns,
                'rows': rows,
                'rawLatex': raw_latex,
                'sectionId': sec_id,
            })

        cursor = end
        counters[f'_p_{sec_id}'] = para_num

    # Paragraphs after the last structural element
    _add_paragraphs(
        content[cursor:], sec_id, blocks, counters, footnote_list, cite_keys, para_num
    )


def _add_paragraphs(
    text: str,
    sec_id: str,
    blocks: list,
    counters: dict,
    footnote_list: list,
    cite_keys: set,
    para_num: int,
) -> int:
    """Split raw text into paragraphs, parse inline content, append to blocks."""
    # Remove known non-content commands
    text = _STRIP_CMDS.sub('', text)
    # Strip any residual environment tags that weren't captured as segments
    text = re.sub(r'\\begin\{(?:itemize|enumerate|description|verbatim)\}', '', text)
    text = re.sub(r'\\end\{(?:itemize|enumerate|description|verbatim)\}', '', text)
    text = re.sub(r'\\item(?:\[[^\]]*\])?\b[ \t]*', '\n\n', text)

    for para in re.split(r'\n{2,}', text):
        para = para.strip()
        if not para or len(para) < 3:
            continue
        inline = _parse_inline_content(para, footnote_list, cite_keys, counters, sec_id)
        if not inline:
            continue
        if not any(nd['type'] != 'text' or bool(nd.get('text', '').strip()) for nd in inline):
            continue
        para_num += 1
        p_id = _uid('blk_p', counters)
        blocks.append({
            'id': p_id,
            'type': 'paragraph',
            'content': inline,
            'anchor': {'sectionId': sec_id, 'paragraphNumber': para_num},
        })
    return para_num


# ── Table parser ─────────────────────────────────────────────────────────────

def _parse_tabular(raw_latex: str) -> tuple[list[dict], list[list[dict]]]:
    """
    Parse a \\begin{tabular}…\\end{tabular} block into (columns, rows).

    Returns:
        columns — list of {'label': str} dicts derived from the first data row.
        rows    — list of rows; each row is a list of {'value': str} dicts.

    The first row is treated as a header row (column labels).
    \\hline and leading/trailing whitespace are stripped.
    """
    body_m = re.search(
        r'\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}',
        raw_latex, re.DOTALL,
    )
    if not body_m:
        return [], []

    body = body_m.group(1)
    # Remove booktabs / horizontal rule commands
    body = re.sub(r'\\(?:toprule|midrule|bottomrule|hline|cline\{[^}]*\})\s*', '', body)
    # Convert escaped percent \% back to a plain % for display
    body = body.replace(r'\%', '%')

    # Split on \\ (row separator); ignore empty fragments
    row_strings = [r.strip() for r in re.split(r'\\\\', body) if r.strip()]

    columns: list[dict] = []
    rows: list[list[dict]] = []

    for i, row_str in enumerate(row_strings):
        # Strip inline LaTeX formatting (bold/italic) from cell text for readability
        cell_str = re.sub(r'\\textbf\{([^}]*)\}', r'\1', row_str)
        cell_str = re.sub(r'\\textit\{([^}]*)\}', r'\1', cell_str)
        cell_str = re.sub(r'\\emph\{([^}]*)\}',   r'\1', cell_str)
        cells = [c.strip() for c in cell_str.split('&')]
        if i == 0:
            columns = [{'label': c} for c in cells]
        else:
            rows.append([{'value': c} for c in cells])

    return columns, rows


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_latex(tex_source: str, submission_metadata: dict | None = None) -> dict:
    """
    Parse a .tex source string into canonical JSON.
    submission_metadata: dict with keys title, abstract, keywords, author_name, etc.
    """
    meta = submission_metadata or {}
    counters: dict[str, int] = {}
    content_blocks: list[dict] = []
    assets: list[dict] = []
    footnote_list: list[dict] = []
    cite_keys: set[str] = set()
    blind_mode = bool(re.search(r'\\ARJblindreview', tex_source))

    # ── Extract top-level metadata ────────────────────────────────────────────
    title = _extract_macro(tex_source, 'ARJtitle') or meta.get('title', '')
    subtitle = _extract_macro(tex_source, 'ARJsubtitle') or meta.get('subtitle', '')
    abstract = _extract_macro(tex_source, 'ARJabstract') or meta.get('abstract', '')
    author_name = _extract_macro(tex_source, 'ARJauthor') or meta.get('author_name', '')
    affiliation = _extract_macro(tex_source, 'ARJaffiliation') or ''
    email = _extract_macro(tex_source, 'ARJemail') or ''
    orcid = _extract_macro(tex_source, 'ARJORCID') or ''
    article_type = _extract_macro(tex_source, 'ARJarticleType') or meta.get('article_type', '')
    raw_keywords = _extract_macro(tex_source, 'ARJkeywords') or ''
    keywords = [k.strip() for k in raw_keywords.split(';') if k.strip()]
    funding = _extract_macro(tex_source, 'ARJfunding') or ''
    conflicts = _extract_macro(tex_source, 'ARJconflicts') or 'None declared.'
    license_pref = _extract_macro(tex_source, 'ARJlicense') or 'CC-BY'
    acknowledgements = _extract_macro(tex_source, 'ARJacknowledgements') or ''

    # ── Isolate document body ─────────────────────────────────────────────────
    # Strip line comments before extracting the body so that comment text like
    # "%% Write between \begin{document} and \end{document}" does not confuse
    # the regex and cause it to match the comment tokens instead of the real ones.
    tex_no_comments = re.sub(r'(?<!\\)%[^\n]*', '', tex_source)
    body_match = re.search(r'\\begin\{document\}(.*?)(?:\\end\{document\}|$)', tex_no_comments, re.DOTALL)
    body = body_match.group(1) if body_match else tex_source
    body = re.sub(r'\\makearjtitle|\\ARJprintdeclarations', '', body)

    # ── Parse sections ────────────────────────────────────────────────────────
    # The lookahead uses \n before \section so that \verb|\section{...}| inside
    # paragraph text is not mistaken for a section boundary.
    section_pattern = re.compile(
        r'(?P<cmd>\\(?:sub)*section)\*?\{(?P<title>[^}]+)\}(?P<content>.*?)(?=\n[ \t]*\\(?:sub)*section|\Z)',
        re.DOTALL,
    )
    section_num = 0
    for sec_match in section_pattern.finditer(body):
        cmd = sec_match.group('cmd')
        sec_title = sec_match.group('title').strip()
        sec_content = sec_match.group('content').strip()
        level = cmd.count('sub') + 1
        section_num += 1
        sec_id = f'sec_{section_num}'

        h_id = _uid('blk_h', counters)
        content_blocks.append({
            'id': h_id,
            'type': 'heading',
            'level': level,
            'text': sec_title,
            'numbering': str(section_num),
            'sectionId': sec_id,
        })

        _parse_section_content(
            sec_content, sec_id, content_blocks, assets, counters, footnote_list, cite_keys
        )

    if section_num == 0:
        _parse_section_content(
            body, 'sec_1', content_blocks, assets, counters, footnote_list, cite_keys
        )

    # ── Footnotes section block (bottom fallback for narrow screens) ──────────
    if footnote_list:
        content_blocks.append({
            'id': 'blk_footnotes',
            'type': 'footnotes_section',
            'footnotes': footnote_list,
        })

    # ── Citations ─────────────────────────────────────────────────────────────
    citation_items: list[dict] = [
        {'id': f'cit_{ck}', 'citeKey': ck, 'type': 'unknown', 'title': '', 'authors': [], 'year': ''}
        for ck in sorted(cite_keys)
    ]

    # ── Bibliography block ────────────────────────────────────────────────────
    if re.search(r'\\bibliography\{', body) or citation_items:
        content_blocks.append({
            'id': 'blk_bibliography',
            'type': 'bibliography',
            'items': citation_items,
        })

    # ── Assemble canonical document ───────────────────────────────────────────
    from django.utils.timezone import now
    doc_id = f'doc_{uuid.uuid4().hex[:8]}'

    return {
        'schemaVersion': '1.0',
        'documentId': doc_id,
        'blindReviewMode': 'double_blind' if blind_mode else 'open',
        'createdAt': now().isoformat(),
        'canonicalLanguage': meta.get('language', 'en'),
        'contributors': [
            {
                'personId': 'per_author_1',
                'role': 'author',
                'displayName': author_name,
                'orcid': orcid,
                'email': email,
                'institution': affiliation,
                'isCorresponding': True,
                'redactionProfile': {'blindVisible': False, 'publicVisible': True},
            }
        ],
        'metadata': {
            'title': {'main': title, 'subtitle': subtitle},
            'abstract': [{'lang': meta.get('language', 'en'), 'text': abstract}],
            'keywords': keywords,
            'disciplines': meta.get('disciplines', []),
            'articleType': article_type,
            'language': meta.get('language', 'en'),
            'licensePreference': license_pref,
            'funding': [funding] if funding else [],
            'conflictOfInterest': conflicts,
            'acknowledgements': acknowledgements,
        },
        'content': content_blocks,
        'assets': assets,
        'citations': {
            'citationStyle': 'chicago-author-date',
            'items': citation_items,
        },
        'reviewAnchors': [],
        'reviews': [],
        'rights': {'license': license_pref, 'copyrightHolder': 'Author', 'embargo': None},
        'quality': {
            'parserWarnings': [],
            'missingAssets': [],
            'brokenReferences': [],
            'accessibilityChecks': {'missingAltText': [], 'missingCaptions': []},
            'renderChecks': {'pdfBuildOk': False, 'htmlBuildOk': False},
        },
        'production': {
            'htmlBuild': None,
            'pdfBuild': {'mode': 'ephemeral', 'interactiveEnabled': False},
            'publicIdentifier': {'doi': None},
        },
        'history': [],
    }
