# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Footer section headings ("Explore", "Information", "Contact") are no longer
  uppercased and no longer have a divider line between them and their links.
- All body text is left-aligned instead of justified.
- Buttons use tighter internal padding (~5pt).
- Journal descriptor wording changed from "Journal of […]" to "Journal on […]"
  across the site, emails, PDF, and the stored journal description text.

## [1.0.0] - 2026-10-03

First tagged release. Highlights of the most recent work:

### Added
- inACT logo asset set in `static/img/brand/` (full wordmark and acronym, each
  in black, orange, and white) plus the brand source masters under
  `design/inACT_RGB/`.

### Changed
- **Rebrand to inACT.** Renamed the journal brand (from "inAct" / "Trans-Act")
  to **inACT** across templates, emails, the PDF generator, docs, deploy/seed
  scripts, nginx configs, `.env.example`, and the LaTeX author template pack.
  Also updated the brand text stored in the database (JournalConfig content
  fields, Issue editorial note, Site name).
- Footer background changed from orange to Silver (`#E4E2E7`), with dark text,
  clay section labels, and an orange link-hover for contrast on the lighter
  surface.
- Logos swapped site-wide to the new inACT set: header (full black), footer
  (full orange), emails (embedded PNG via absolute URL), and the PDF cover
  (orange logo embedded as a self-contained base64 data URI).

### Fixed
- **WYSIWYG editor footnotes.** Footnote numbers now renumber by document order
  on insert, delete, reorder, and on load, instead of relying on a session
  counter that only ever increased (which caused numbers to keep climbing after
  deletions and reset on reload).
- **WYSIWYG editor nested lists.** Nested bullet/numbered list levels now
  persist through save and reload. The serializer, deserializer, and the
  HTML/PDF renderer all handle arbitrary list nesting.

[Unreleased]: https://github.com/iorobertob/ARJournal/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/iorobertob/ARJournal/releases/tag/v1.0.0
