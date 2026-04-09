# Artistic Research Journal Platform — Full Production Bundle

## Included Files
- `technical_spec_full.md` — complete product and workflow specification
- `canonical_document_schema_spec.md` — canonical JSON document model
- `openapi.yaml` — starter API contract
- `reviewer_ui_spec.md` — reviewer interface best-practice spec
- `review_moderation_spec.md` — editorial mediation and moderation rules
- `arjournal.cls` — LaTeX class
- `arjournal_template.tex` — author template

## Core Principle
The platform's source of truth is the canonical JSON document, not the PDF and not the raw LaTeX file.

## Rich Media Strategy
Authors upload text and media separately.
The `.tex` file contains placeholders for images, video, and audio.
The platform parses these placeholders and renders:
- HTML as the primary review and publication format
- flat or interactive PDF on demand
Generated PDFs are ephemeral and should be discarded after download or TTL expiry.

## Recommended Next Step
Use this bundle as the starting contract for AI-assisted development, then tailor:
- your metadata taxonomy
- institutional roles
- review criteria
- rights and access policy
- integration choices
