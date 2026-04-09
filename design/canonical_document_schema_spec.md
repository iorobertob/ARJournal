# Canonical Document Schema Specification
Version: 1.0

## 1. Purpose
This schema defines the canonical internal representation of all manuscripts, reviews, projections, and publication outputs. It is the source of truth for the platform.

## 2. Design Rules
- One canonical document per revision
- Stable block IDs for annotations
- Media stored as separate assets and linked by references
- Role-aware projections derive from one canonical record
- No destructive overwrite of prior revisions

## 3. Top-Level JSON Shape
```json
{
  "schemaVersion": "1.0",
  "documentId": "doc_123",
  "submissionId": "sub_456",
  "revisionId": "rev_001",
  "status": "under_review",
  "workflowStage": "peer_review",
  "createdAt": "2026-04-09T10:00:00Z",
  "updatedAt": "2026-04-09T10:00:00Z",
  "canonicalLanguage": "en",
  "blindReviewMode": "double_blind",
  "journalContext": {},
  "contributors": [],
  "metadata": {},
  "content": [],
  "assets": [],
  "citations": {},
  "reviewAnchors": [],
  "reviews": [],
  "rights": {},
  "quality": {},
  "production": {},
  "history": []
}
```

## 4. journalContext
```json
{
  "journalId": "arj",
  "journalTitle": "Artistic Research Journal",
  "section": "Articles",
  "specialIssue": null,
  "issueId": null,
  "callId": null
}
```

## 5. contributors
```json
[
  {
    "personId": "per_author_1",
    "role": "author",
    "displayName": "Jane Doe",
    "orcid": "0000-0000-0000-0000",
    "email": "jane@example.org",
    "institution": "Example University",
    "department": "Media Arts",
    "country": "LT",
    "bio": "Short biography",
    "interests": ["performance", "sound", "practice research"],
    "isCorresponding": true,
    "redactionProfile": {
      "blindVisible": false,
      "publicVisible": true
    }
  }
]
```

## 6. metadata
```json
{
  "title": {
    "main": "Example Main Title",
    "subtitle": "Optional Subtitle"
  },
  "abstract": [
    {
      "lang": "en",
      "text": "Abstract text"
    }
  ],
  "keywords": ["artistic research", "video essay"],
  "disciplines": ["media arts", "performance studies"],
  "articleType": "research_article",
  "language": "en",
  "licensePreference": "CC-BY",
  "ethicsDeclarations": {
    "humanSubjects": false,
    "animalSubjects": false,
    "consentObtained": null
  },
  "funding": [],
  "conflictOfInterest": "None declared",
  "acknowledgements": "Optional notes"
}
```

## 7. content block model
Every block must include:
- `id`
- `type`

Supported types:
- heading
- paragraph
- quote
- list
- table
- figure
- media
- equation
- code
- footnote
- appendix
- bibliography
- thematicBreak
- customEmbed

### heading example
```json
{
  "id": "blk_h_001",
  "type": "heading",
  "level": 1,
  "text": "Introduction",
  "numbering": "1",
  "sectionId": "sec_1"
}
```

### paragraph example
```json
{
  "id": "blk_p_001",
  "type": "paragraph",
  "content": [
    {"type": "text", "text": "This article explores multimodal research."}
  ],
  "anchor": {
    "sectionId": "sec_1",
    "paragraphNumber": 1,
    "lineMapRef": "ln_1"
  }
}
```

### table example
```json
{
  "id": "tbl_001",
  "type": "table",
  "caption": "Comparison of review models",
  "columns": [
    {"id": "c1", "label": "Model"},
    {"id": "c2", "label": "Blindness"},
    {"id": "c3", "label": "Notes"}
  ],
  "rows": [
    [
      {"columnId": "c1", "value": "Single blind"},
      {"columnId": "c2", "value": "Reviewers know authors"},
      {"columnId": "c3", "value": "Common in many fields"}
    ]
  ],
  "footnotes": []
}
```

### figure example
```json
{
  "id": "fig_001",
  "type": "figure",
  "assetRef": "asset_img_001",
  "caption": "Still from the installation",
  "credit": "Author",
  "altText": "A projected image in a dark room",
  "placementHint": "inline",
  "anchor": {
    "sectionId": "sec_2",
    "paragraphNumber": 4
  }
}
```

### media example
```json
{
  "id": "med_001",
  "type": "media",
  "mediaType": "video",
  "assetRef": "asset_vid_001",
  "caption": "Performance documentation",
  "transcriptRef": "asset_txt_003",
  "posterImageRef": "asset_img_010",
  "durationMs": 185000,
  "streamingPolicy": "authenticated_stream_only",
  "timecodeAnchors": true,
  "anchor": {
    "sectionId": "sec_3",
    "paragraphNumber": 2
  }
}
```

## 8. assets
```json
[
  {
    "assetId": "asset_vid_001",
    "kind": "video",
    "originalFilename": "performance1.mp4",
    "mimeType": "video/mp4",
    "storageKey": "s3://bucket/path/performance1.mp4",
    "checksumSha256": "abc123",
    "sizeBytes": 12345678,
    "variants": [
      {
        "variantId": "v1",
        "use": "stream_720p",
        "mimeType": "application/x-mpegURL"
      }
    ],
    "rights": {
      "publicAccess": false,
      "reviewAccess": true,
      "downloadAllowed": false
    },
    "preservation": {
      "masterRetained": true
    }
  }
]
```

## 9. citations
```json
{
  "citationStyle": "chicago-author-date",
  "items": [
    {
      "id": "ref_001",
      "citeKey": "Smith2024",
      "type": "book",
      "title": "Example Book",
      "authors": ["Smith, A."],
      "year": 2024,
      "doi": null
    }
  ]
}
```

## 10. reviewAnchors
```json
[
  {
    "anchorId": "anc_001",
    "blockId": "blk_p_001",
    "selector": {
      "type": "text_quote_selector",
      "exact": "This article explores multimodal research.",
      "prefix": "",
      "suffix": ""
    },
    "lineRange": {
      "from": 14,
      "to": 18
    }
  }
]
```

## 11. reviews
```json
[
  {
    "reviewId": "revw_001",
    "reviewerId": "reviewer_1",
    "recommendation": "major_revision",
    "scores": {
      "originality": 4,
      "rigor": 3,
      "clarity": 3,
      "artisticResearchFit": 5
    },
    "commentsToAuthor": [
      "The project is compelling but method needs clarification."
    ],
    "commentsToEditor": [
      "Strong fit, but needs revision."
    ],
    "anchorComments": [
      {
        "anchorId": "anc_001",
        "comment": "Clarify this claim."
      }
    ],
    "moderation": {
      "status": "moderation_required",
      "editorSummaryAttached": false
    }
  }
]
```

## 12. rights
```json
{
  "license": "CC-BY",
  "copyrightHolder": "Author",
  "embargo": null,
  "mediaPermissions": [
    {
      "assetId": "asset_vid_001",
      "permissionStatus": "cleared",
      "territory": "world",
      "expiry": null
    }
  ]
}
```

## 13. quality
```json
{
  "parserWarnings": [],
  "missingAssets": [],
  "brokenReferences": [],
  "accessibilityChecks": {
    "missingAltText": [],
    "missingCaptions": []
  },
  "renderChecks": {
    "pdfBuildOk": true,
    "htmlBuildOk": true
  }
}
```

## 14. production
```json
{
  "htmlBuild": {
    "lastBuiltAt": "2026-04-09T10:00:00Z",
    "buildHash": "hash123"
  },
  "pdfBuild": {
    "mode": "ephemeral",
    "interactiveEnabled": true
  },
  "publicIdentifier": {
    "doi": null
  }
}
```

## 15. history
```json
[
  {
    "eventId": "evt_001",
    "type": "submission_created",
    "actorRole": "author",
    "timestamp": "2026-04-09T10:00:00Z",
    "payload": {}
  }
]
```

## 16. Projections
The platform must derive:
- author canonical view
- blinded reviewer view
- internal editorial view
- public publication view

## 17. Ingestion Rules
### From LaTeX
- parse sections, figures, tables, equations, references
- parse custom media macros
- validate referenced assets
- produce stable block and anchor IDs

### From DOCX
- normalize headings, tables, footnotes, figures
- flag ambiguous structures for review

## 18. Rendering Rules
### HTML
- primary format
- semantic output
- stable anchor IDs
- inline media players
- rights-aware rendering

### PDF
- generated on demand
- flat and interactive modes
- export discarded after download or TTL expiry

## 19. API Examples
### Get canonical document
`GET /api/documents/{documentId}`

### Get projection
`GET /api/documents/{documentId}/projection?view=reviewer_blind`

### Request PDF export
`POST /api/documents/{documentId}/exports/pdf`
```json
{
  "mode": "flat",
  "ttlMinutes": 15
}
```

### Add annotation
`POST /api/reviews/{reviewId}/annotations`
```json
{
  "anchorId": "anc_001",
  "comment": "Clarify the method."
}
```
