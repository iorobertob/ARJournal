"""
LaTeX → Canonical JSON parser.

Handles the arjournal.cls custom macros:
  \\ARJfigure{file}{caption}{alttext}
  \\ARJvideo{file}{caption}{poster}{transcript}
  \\ARJaudio{file}{caption}{transcript}
  \\ARJblindreview  (blind mode flag)

Returns a canonical JSON dict matching canonical_document_schema_spec.md.
"""
import re
import uuid
from typing import Any


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uid(prefix: str, counters: dict) -> str:
    counters[prefix] = counters.get(prefix, 0) + 1
    return f'{prefix}_{counters[prefix]:03d}'


def _extract_macro(text: str, macro: str) -> str | None:
    """Extract the first {…} argument of a \\macro{arg} call."""
    pattern = rf'\\{re.escape(macro)}\{{([^}}]*)\}}'
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


def _extract_all_macro_args(text: str, macro: str, n_args: int) -> list[list[str]]:
    """Extract all calls to \\macro{a1}{a2}...{aN}."""
    arg_pattern = r'\{([^}]*)\}' * n_args
    pattern = rf'\\{re.escape(macro)}' + arg_pattern
    return [list(m) for m in re.findall(pattern, text)]


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
    blind_mode = bool(re.search(r'\\ARJblindreview', tex_source))

    # ── Extract top-level metadata from macros ────────────────────────────────
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

    # ── Strip preamble; work on document body ─────────────────────────────────
    body_match = re.search(r'\\begin\{document\}(.*?)(?:\\end\{document\}|$)', tex_source, re.DOTALL)
    body = body_match.group(1) if body_match else tex_source

    # Remove \makearjtitle and \ARJprintdeclarations
    body = re.sub(r'\\makearjtitle|\\ARJprintdeclarations', '', body)

    # ── Parse sections ────────────────────────────────────────────────────────
    section_pattern = re.compile(
        r'(?P<cmd>\\(?:sub)*section)\*?\{(?P<title>[^}]+)\}(?P<content>.*?)(?=\\(?:sub)*section|\Z)',
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

        # Heading block
        h_id = _uid('blk_h', counters)
        content_blocks.append({
            'id': h_id,
            'type': 'heading',
            'level': level,
            'text': sec_title,
            'numbering': str(section_num),
            'sectionId': sec_id,
        })

        # Process content within the section
        _parse_section_content(sec_content, sec_id, content_blocks, assets, counters)

    # If no sections found, treat whole body as paragraphs
    if section_num == 0:
        _parse_section_content(body, 'sec_1', content_blocks, assets, counters)

    # ── Parse bibliography ────────────────────────────────────────────────────
    citations: dict[str, Any] = {
        'citationStyle': 'chicago-author-date',
        'items': [],
    }
    bib_match = re.search(r'\\bibliography\{([^}]+)\}', body)
    bib_file = bib_match.group(1) if bib_match else ''

    # ── Build canonical document ──────────────────────────────────────────────
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
                'personId': f'per_author_1',
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
        'citations': citations,
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


def _parse_section_content(content: str, sec_id: str, blocks: list, assets: list, counters: dict):
    """Parse paragraphs, figures, video, audio, and tables within a section."""
    # Handle ARJfigure
    for args in _extract_all_macro_args(content, 'ARJfigure', 3):
        fname, caption, alt = args
        asset_id = _uid('asset_img', counters)
        fig_id = _uid('fig', counters)
        assets.append({
            'assetId': asset_id,
            'kind': 'image',
            'originalFilename': fname,
            'rights': {'publicAccess': True, 'reviewAccess': True, 'downloadAllowed': True},
        })
        blocks.append({
            'id': fig_id,
            'type': 'figure',
            'assetRef': asset_id,
            'caption': caption,
            'altText': alt,
            'sectionId': sec_id,
        })
        content = content.replace(f'\\ARJfigure{{{fname}}}{{{caption}}}{{{alt}}}', '')

    # Handle ARJvideo
    for args in _extract_all_macro_args(content, 'ARJvideo', 4):
        fname, caption, poster, transcript = args
        asset_id = _uid('asset_vid', counters)
        med_id = _uid('med', counters)
        assets.append({
            'assetId': asset_id,
            'kind': 'video',
            'originalFilename': fname,
            'posterImageRef': poster,
            'transcriptRef': transcript,
            'rights': {'publicAccess': True, 'reviewAccess': True, 'downloadAllowed': False},
            'streamingPolicy': 'authenticated_stream_only',
        })
        blocks.append({
            'id': med_id,
            'type': 'media',
            'mediaType': 'video',
            'assetRef': asset_id,
            'caption': caption,
            'timecodeAnchors': True,
            'sectionId': sec_id,
        })
        content = re.sub(r'\\ARJvideo\{[^}]*\}\{[^}]*\}\{[^}]*\}\{[^}]*\}', '', content, count=1)

    # Handle ARJaudio
    for args in _extract_all_macro_args(content, 'ARJaudio', 3):
        fname, caption, transcript = args
        asset_id = _uid('asset_aud', counters)
        med_id = _uid('med', counters)
        assets.append({
            'assetId': asset_id,
            'kind': 'audio',
            'originalFilename': fname,
            'transcriptRef': transcript,
            'rights': {'publicAccess': True, 'reviewAccess': True, 'downloadAllowed': False},
        })
        blocks.append({
            'id': med_id,
            'type': 'media',
            'mediaType': 'audio',
            'assetRef': asset_id,
            'caption': caption,
            'sectionId': sec_id,
        })
        content = re.sub(r'\\ARJaudio\{[^}]*\}\{[^}]*\}\{[^}]*\}', '', content, count=1)

    # Handle tables
    table_pattern = re.compile(
        r'\\begin\{table\}.*?\\caption\{([^}]*)\}.*?\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}.*?\\end\{table\}',
        re.DOTALL,
    )
    for tm in table_pattern.finditer(content):
        tbl_id = _uid('tbl', counters)
        blocks.append({
            'id': tbl_id,
            'type': 'table',
            'caption': tm.group(1).strip(),
            'rawLatex': tm.group(0),
            'sectionId': sec_id,
        })
        content = content.replace(tm.group(0), '')

    # Remaining text: split into paragraphs
    # Remove leftover LaTeX commands
    clean = re.sub(r'\\[a-zA-Z]+\*?\{[^}]*\}', '', content)
    clean = re.sub(r'\\[a-zA-Z]+', '', clean)
    clean = re.sub(r'%[^\n]*', '', clean)  # comments

    para_num = 0
    for para in re.split(r'\n{2,}', clean):
        para = para.strip()
        if not para or len(para) < 3:
            continue
        para_num += 1
        p_id = _uid('blk_p', counters)
        blocks.append({
            'id': p_id,
            'type': 'paragraph',
            'content': [{'type': 'text', 'text': para}],
            'anchor': {
                'sectionId': sec_id,
                'paragraphNumber': para_num,
            },
        })
