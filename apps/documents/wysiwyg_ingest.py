"""
Build a full canonical document dict from a WYSIWYG revision.

The editor stores `revision.wysiwyg_data` as:
  { "content": [...canonical blocks...], "bibliography": [...citation items...] }

This function merges that with submission metadata and contributor info from
the author's User profile to produce a complete canonical dict that matches
the schema produced by the LaTeX parser.
"""
import uuid
from django.utils import timezone


def _collect_cited_keys(content_blocks):
    """Return the set of citeKey values actually referenced in the content."""
    keys = set()

    def _walk_inline(nodes):
        for node in (nodes or []):
            if node.get('type') == 'cite':
                key = node.get('ref', '')
                if key:
                    keys.add(key)

    for block in content_blocks:
        btype = block.get('type', '')
        if btype in ('paragraph', 'blockquote', 'heading'):
            _walk_inline(block.get('content', []))
        elif btype == 'list':
            for item_nodes in block.get('items', []):
                _walk_inline(item_nodes)

    return keys


def build_canonical_from_wysiwyg(revision):
    """Return a full canonical document dict for a WYSIWYG revision."""
    submission = revision.submission
    author = submission.author
    data = revision.wysiwyg_data or {}

    content_blocks = data.get('content', [])
    bib_items = data.get('bibliography', [])

    # Only include bibliography entries whose citeKey is actually cited in the text
    cited_keys = _collect_cited_keys(content_blocks)

    # Normalise bibliography items to match the canonical citation schema
    citations_items = []
    for item in bib_items:
        cite_key = item.get('citeKey') or item.get('citekey') or ''
        if not cite_key or cite_key not in cited_keys:
            continue
        citations_items.append({
            'id': f'cit_{cite_key}',
            'citeKey': cite_key,
            'type': item.get('type', 'misc'),
            'title': item.get('title', ''),
            'authors': item.get('authors', []),
            'year': item.get('year', ''),
            'journal': item.get('journal', ''),
            'volume': item.get('volume', ''),
            'number': item.get('number', ''),
            'pages': item.get('pages', ''),
            'publisher': item.get('publisher', ''),
            'booktitle': item.get('booktitle', ''),
            'editor': item.get('editor', ''),
            'school': item.get('school', ''),
            'doi': item.get('doi', ''),
            'url': item.get('url', ''),
        })

    # Add a bibliography block at the end of content if there are citations
    if citations_items:
        bib_block = {
            'id': 'blk_bibliography',
            'type': 'bibliography',
            'items': [
                {'id': c['id'], 'citeKey': c['citeKey'], **c}
                for c in citations_items
            ],
        }
        # Only append if there isn't already one
        if not any(b.get('type') == 'bibliography' for b in content_blocks):
            content_blocks = list(content_blocks) + [bib_block]

    # Collect assets referenced in the content blocks
    assets = _build_assets_list(revision, content_blocks)

    # Contributor from submission author
    profile = getattr(author, 'profile', None)
    contributor = {
        'personId': f'person_{author.pk}',
        'role': 'author',
        'displayName': author.display_name if hasattr(author, 'display_name') else str(author),
        'orcid': getattr(profile, 'orcid', '') if profile else '',
        'email': author.email,
        'institution': getattr(profile, 'institution', '') if profile else '',
        'department': getattr(profile, 'department', '') if profile else '',
        'country': getattr(profile, 'country', '') if profile else '',
        'bio': getattr(profile, 'bio', '') if profile else '',
        'interests': getattr(profile, 'research_interests', []) if profile else [],
        'isCorresponding': True,
        'redactionProfile': {
            'blindVisible': False,
            'publicVisible': True,
        },
    }

    now = timezone.now().isoformat()

    canonical = {
        'schemaVersion': '1.0',
        'documentId': f'doc_{uuid.uuid4().hex[:12]}',
        'submissionId': str(submission.pk),
        'revisionId': str(revision.pk),
        'status': submission.status,
        'workflowStage': submission.status,
        'createdAt': now,
        'updatedAt': now,
        'canonicalLanguage': submission.language or 'en',
        'blindReviewMode': 'double_blind',
        'source': 'wysiwyg',
        'journalContext': {},
        'contributors': [contributor],
        'metadata': {
            'title': {
                'main': submission.title,
                'subtitle': submission.subtitle or '',
            },
            'abstract': [{'lang': submission.language or 'en', 'text': submission.abstract}],
            'keywords': submission.keywords or [],
            'disciplines': submission.disciplines or [],
            'articleType': submission.article_type,
            'language': submission.language or 'en',
            'licensePreference': submission.license_preference or 'CC-BY',
            'ethicsDeclarations': submission.ethics_declaration or {},
            'funding': [submission.funding_statement] if submission.funding_statement else [],
            'conflictOfInterest': submission.conflict_of_interest or 'None declared.',
            'acknowledgements': '',
        },
        'content': content_blocks,
        'assets': assets,
        'citations': {
            'citationStyle': 'chicago-author-date',
            'items': citations_items,
        },
        'reviewAnchors': [],
        'reviews': [],
        'rights': {
            'license': submission.license_preference or 'CC-BY',
        },
        'quality': {},
        'production': {},
        'history': [],
    }

    return canonical


def _build_assets_list(revision, content_blocks):
    """
    Build the canonical assets array from SubmissionAssets attached to this revision.
    Also resolve assetRefs in content blocks to match uploaded asset ids.
    """
    from apps.submissions.models import SubmissionAsset

    submission_assets = list(revision.assets.exclude(file=''))
    assets = []

    for sa in submission_assets:
        kind_map = {
            'image': 'image',
            'video': 'video',
            'audio': 'audio',
            'transcript': 'transcript',
            'poster': 'image',
            'data': 'data',
            'supplementary': 'supplementary',
        }
        asset_id = f'asset_{sa.kind}_{sa.pk:03d}'
        assets.append({
            'assetId': asset_id,
            'kind': kind_map.get(sa.kind, 'supplementary'),
            'originalFilename': sa.original_filename,
            'mimeType': sa.mime_type or '',
            'storageKey': sa.file.name if sa.file else '',
            'sizeBytes': sa.size_bytes or 0,
            'rights': {
                'publicAccess': True,
                'reviewAccess': True,
                'downloadAllowed': True,
            },
            'preservation': {'masterRetained': True},
        })

    return assets
