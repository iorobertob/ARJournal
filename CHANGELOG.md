# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-10-04

### Added
- **Pinned news card on homepage.** A single news post can be pinned via the
  admin Homepage settings; it appears below the mission bar as a large featured
  card (text left, image right, orange title, bordered date badge, "Find out
  more" CTA). When no post is pinned the section is hidden, supporting the
  pre-launch empty-homepage state.
- `NewsPost.is_pinned` boolean field with single-pin constraint enforced in
  `save()`. Migration `0016_newspost_featured_image_is_pinned` applies it.
- `NewsPost.featured_image` field (renamed from `thumbnail`) — serves as both
  the card thumbnail and the detail-page hero image.
- Pin selector dropdown on the admin Homepage page.
- Featured image upload/remove on the news-post admin form, now correctly wired
  to the renamed field.
- Thumbnail shown in the admin news-post list.
- `summary` field capped at 500 characters in the form (`maxlength` attribute +
  server-side slice) to prevent a database `DataError`.

### Changed
- **Type scale** — all raw pixel/rem font-size values in `article.css`,
  `editor.css`, `dashboard.css`, and `wysiwyg.css` replaced with design-token
  variables matching the Figma Desktop-18 scale.
- **News card layout** — image is now on the RIGHT, text (title → date badge →
  excerpt → CTA) on the LEFT, via CSS `grid-template-areas`. Both the homepage
  featured card and the `/news/` list cards share the same layout.
- News card title is always orange (`--color-accent`). Date badge has a grey
  border and muted text. "Find out more →" is a compact outlined button.
- Featured card uses double-class selector `.news-card.news-card--featured` to
  correctly override base `.news-card` styles (border, hover transform, etc.).
  Image fills the full right column height (`aspect-ratio: unset`,
  `object-fit: cover`).
- `home-news` section removed its `max-width: 1000px` cap — now spans the full
  1300px container width, matching other homepage sections.
- **Headings in all rich-text areas are orange and non-bold** — applies in the
  WYSIWYG admin editor (`.wysiwyg__area`), the article ProseMirror editor
  (`.editor-canvas .ProseMirror`), and public prose (`.prose`).

### Fixed
- `news_list.html` was still referencing `post.thumbnail` after the field was
  renamed to `featured_image`, preventing thumbnails from appearing in the list.
- `news_edit()` admin view was still reading `request.FILES['thumbnail']` and
  writing to `post.thumbnail`, causing uploaded images to silently not save.
- WYSIWYG orange colour bleed: Chrome's `contenteditable` injected
  `<span style="color: orange">` when converting heading → paragraph. Fixed by:
  (1) running `stripColorSpans()` after every `formatBlock→P` call in
  `wysiwyg.js`; (2) intercepting `paste` to strip inline colour styles before
  insertion; (3) adding `.wysiwyg__area p, .wysiwyg__area p span { color: … !important }` as a CSS safety net.

### Changed
- Footer section headings ("Explore", "Information", "Contact") are no longer
  uppercased and no longer have a divider line between them and their links,
  and are now orange (`#FF4500`) along with the copyright block, matching the logo.
- All body text is left-aligned instead of justified.
- Buttons use much tighter internal padding and line-height to match the Figma
  "Directorial link" spec (base `3px 7px`, line-height 1.2).
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
