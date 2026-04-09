# Artistic Research Academic Journal Platform — Full Production Bundle Technical Specification
Version: 2.0

## 1. Purpose
This specification defines a full-stack online platform for an artistic research academic journal. The platform supports submission, editorial screening, reviewer suggestion, peer review, editorial mediation, multimedia publication, rights-aware streaming, production, publication, and preservation.

The platform is designed for artistic research, where submissions may combine text, images, audio, video, documentation, and other multimodal research artifacts.

## 2. Product Vision
Build a single integrated system where:
- authors submit structured text plus separately managed media;
- editors manage screening, reviewer selection, review moderation, and decisions;
- reviewers assess submissions in a rich HTML review workspace with structured forms and anchored annotations;
- readers access published articles in HTML as the primary format, with on-demand PDF exports;
- the platform preserves a canonical internal document representation independent of authoring format.

## 3. Strategic Principles
1. Canonical structured document model is the source of truth.
2. LaTeX is a structured authoring input, not the canonical record.
3. PDF is an output, not a trusted input source.
4. HTML is the primary review and publication surface.
5. Media files are stored separately and referenced by structured placeholders.
6. Human editorial authority remains central.
7. AI is assistive only unless explicitly authorized for low-risk automation.
8. Double-blind review is supported by default.
9. Every state transition is auditable.
10. Rights, permissions, and media access controls are first-class concerns.

## 4. End-to-End Workflow
### 4.1 Manuscript Preparation
Authors prepare submissions using:
- provided LaTeX template; or
- supported DOCX workflow, converted internally into the canonical structure.

Required components:
- title
- abstract
- keywords
- article type
- author metadata
- conflict of interest declaration
- rights declarations
- references
- figures and media placeholders

### 4.2 Submission
Authors submit:
- `.tex` source file or `.docx`
- bibliography files if applicable
- images, audio, video, appendices, datasets as separate assets
- structured metadata through platform forms

Submission result:
- ingestion job created
- document parsed into canonical JSON structure
- HTML review draft rendered
- validation report produced
- editorial screening queue entry created

### 4.3 Editorial Screening
Editorial office or handling editor performs:
- scope fit check
- completeness check
- metadata quality check
- identity leakage check for blind review
- ethics and rights review
- plagiarism / similarity check if enabled
- technical render validation

Possible outcomes:
- desk reject
- return to author for technical corrections
- send to reviewer suggestion stage

### 4.4 Reviewer Suggestion
System automatically proposes 3 reviewers based on:
- topic similarity
- discipline fit
- keywords
- stated interests
- prior publications / expertise metadata
- conflicts of interest
- institutions
- workload balancing
- diversity / fairness constraints
- past review quality metrics

Important:
The manuscript is not sent automatically.
Editorial team reviews suggestions and manually selects / adjusts reviewers before invitations are sent.

### 4.5 Review Invitation
Invited reviewers receive:
- secure invitation link
- title, abstract, keywords
- deadline
- conflict of interest reminder
- accept / decline interface

### 4.6 Review
Reviewer works in a hybrid interface:
- primary: HTML review edition
- optional: PDF download
- structured review form
- anchored inline annotations
- confidential comments to editor
- recommendation field

### 4.7 Review Moderation and Editorial Mediation
Before reviews are released to authors:
- editor checks tone, professionalism, relevance
- editor may redact unethical or inappropriate language while preserving meaning
- system flags conflicting recommendations
- editor writes a decision letter and synthesis note
- moderated review package is assembled

### 4.8 Revision Cycle
Authors receive:
- decision letter
- moderated reviewer comments
- anchor-linked comments
- structured response form

Authors submit revised files and response letter.
System versions each revision.

### 4.9 Acceptance and Production
After acceptance:
- copyediting
- metadata normalization
- DOI registration workflow
- public HTML build
- final PDF generation
- rights / access checks
- issue assignment or continuous publication scheduling

### 4.10 Publication
Published outputs:
- HTML article page as primary
- optional flat PDF
- optional interactive PDF where supported
- media streaming for audio/video
- landing metadata for indexing and discovery

### 4.11 Preservation
Preserve:
- original submission files
- canonical JSON document
- final publication HTML snapshot
- final publication PDF
- media masters and preservation derivatives
- audit history

## 5. Peer Review Models Supported
- double blind
- single blind
- open review
- editorial review
- post-publication commentary (optional future module)

Default recommendation: double blind.

## 6. Reviewer Recommendation Algorithm
### 6.1 Objective
Suggest 3 reviewers for editorial approval.

### 6.2 Inputs
- manuscript title, abstract, keywords
- author-declared disciplines
- subject taxonomy terms
- author-declared excluded reviewers (optional policy-based)
- reviewer profile metadata
- reviewer institutions
- reviewer interests
- reviewer conflict declarations
- reviewer historical performance
- active workload
- previous assignments

### 6.3 Scoring Model
Score each candidate using weighted components:
- topic similarity: 0.30
- discipline alignment: 0.20
- keyword overlap: 0.10
- declared interests fit: 0.10
- conflict penalty: -1.00 hard exclusion or strong negative
- same institution penalty: hard exclusion unless policy override
- recent coauthorship penalty: hard exclusion unless policy override
- workload penalty: -0.10 to -0.30
- responsiveness score: 0.05
- review quality score: 0.10
- diversity / fairness balancing: 0.05

Formula example:
candidate_score =
  0.30*topic_similarity +
  0.20*discipline_alignment +
  0.10*keyword_overlap +
  0.10*interest_alignment +
  0.05*responsiveness +
  0.10*review_quality +
  0.05*diversity_bonus -
  workload_penalty -
  conflict_penalty

### 6.4 Rules
- return 3 primary suggestions plus 3 alternates
- exclude conflicted reviewers
- editor sees explanation for each suggestion
- editor can override and choose manually
- every suggestion event logged

### 6.5 Explainability Output
Each suggestion must include:
- why matched
- conflict checks passed / failed
- workload status
- last invited date
- confidence score

## 7. Review Interface Best Practice
Best-practice reviewer experience is a hybrid model:
1. online HTML manuscript reader
2. structured review form
3. optional anchored inline annotations
4. access to original PDF and source package where allowed

### 7.1 Review Form Structure
- conflict confirmation
- expertise self-rating
- concise manuscript summary
- strengths
- major issues
- minor issues
- ethical / rights concerns
- comments to editor
- recommendation

### 7.2 Anchored Review
Reviewers can comment on:
- paragraph
- figure
- table
- equation
- footnote
- audio time range
- video time range
- image region (future-ready)

### 7.3 Why This Is Best
It combines precision, formal evaluation, and usability.
It avoids the weaknesses of:
- PDF-only review
- Word-only review
- published-look HTML without structured form
- blank text box only

## 8. Conflicting Reviews
Conflicting reviews are normal.
System behavior:
- detect recommendation divergence
- flag to editor
- optionally suggest additional reviewer
- require editorial synthesis before author release

Editor does not average scores mechanically.
Editor interprets the arguments and makes the decision.

## 9. Editorial Mediation Policy
Editors should not rewrite reviewer meaning, but should:
- remove insults and unprofessional tone
- remove biased or unethical remarks
- redact confidential material mistakenly placed in author-visible comments
- structure comments into major / minor issues if needed
- add decision context and synthesis

Three-layer model:
- raw review: internal only
- moderated review: author-visible
- editorial decision letter: required

## 10. Multimedia + LaTeX Strategy
### 10.1 Principle
The solution for rich media insertion while using `.tex` is:
- provide authors with a structured `.tex` template;
- authors upload images, audio, and video separately;
- the `.tex` file contains placeholders / macros that reference those assets;
- platform parser converts them into canonical content blocks;
- HTML renders the live media;
- PDF renders either flat placeholders or experimental embedded media.

### 10.2 PDF Options
Two PDF modes:
1. flat PDF
   - images included
   - audio/video shown as poster / thumbnail, caption, asset note, link / QR code
2. interactive PDF
   - generated where supported
   - may include embedded media references or attachments

Rule:
Generated PDFs are ephemeral.
Downloader is given the option to request a generated file.
Generated files are discarded after download or expiry.

## 11. Functional Modules
### 11.1 Authentication and Access
- email/password and SSO
- role-based access control
- optional ORCID login
- optional reviewer magic links with session hardening

### 11.2 User Roles
- author
- corresponding author
- reviewer
- editorial assistant
- handling editor
- editor-in-chief
- production editor
- copyeditor
- administrator
- publisher / platform admin
- guest reader / subscriber / institution user

### 11.3 Submission Management
- new submission wizard
- asset upload
- validation
- version history
- status dashboard
- author notifications

### 11.4 Editorial Dashboard
- screening queue
- reviewer suggestions
- invitation management
- review monitoring
- conflict flags
- decision builder
- issue planning

### 11.5 Reviewer Workspace
- invitation response
- manuscript reader
- annotation panel
- structured review form
- save draft
- submit review

### 11.6 Production and Publication
- metadata enrichment
- DOI deposit integration
- HTML publishing
- PDF generation
- indexing exports
- embargo handling

### 11.7 Notifications
- submission received
- corrections requested
- reviewer invited / reminded
- review overdue
- decision sent
- proof ready
- publication live

## 12. Non-Functional Requirements
- responsive UI
- accessibility baseline WCAG-aware
- secure file storage
- audit logging
- background job processing
- scalable media streaming
- internationalization ready
- API-first design
- preservation-minded exports

## 13. Suggested Technical Stack
This is a recommendation, not a requirement.

Frontend:
- React / Next.js

Backend:
- Python FastAPI or Node.js NestJS
- background jobs via Celery / RQ / BullMQ

Database:
- PostgreSQL

Search:
- OpenSearch / Elasticsearch / PostgreSQL full text

Object storage:
- S3-compatible storage

Media processing:
- FFmpeg
- HLS generation

Document processing:
- LaTeX parser + TeX build service
- DOCX parser
- canonical JSON transformation pipeline

Authentication:
- Keycloak / Auth0 / custom RBAC

Infrastructure:
- containerized deployment
- CI/CD
- observability

## 14. Data Model Summary
Main entities:
- users
- profiles
- manuscripts
- revisions
- canonical_documents
- assets
- reviewer_profiles
- invitations
- reviews
- annotations
- editorial_decisions
- exports
- issues
- notifications
- audit_events

## 15. Timeline and Launch Plan
### Phase 1 — Discovery and Governance (4 weeks)
- define policy
- define editorial workflow
- taxonomy and metadata model
- rights policy
- anonymization policy

### Phase 2 — Core Platform Build (10–14 weeks)
- auth and roles
- submission
- asset management
- canonical parser
- HTML review view
- reviewer suggestion engine
- review forms
- editorial dashboards

### Phase 3 — Production and Publication (6–8 weeks)
- DOI and metadata export
- publication frontend
- PDF generation
- issue management
- indexing support

### Phase 4 — Pilot (4–6 weeks)
- pilot with selected editors and authors
- gather feedback
- tune reviewer suggestions
- refine moderation workflow

### Phase 5 — Launch (2 weeks)
- training
- content migration if any
- production go-live

## 16. Roles and Responsibilities
### Editorial Team
- editor-in-chief: policy, final decisions, journal direction
- handling editors: screening, reviewer selection, decisions
- editorial assistants: completeness checks, correspondence, metadata support

### Technical Team
- product owner
- technical lead / architect
- backend developer
- frontend developer
- DevOps engineer
- UX designer
- QA engineer
- media engineer

### Production Team
- copyeditor
- production editor
- metadata / indexing specialist

## 17. Procedures and Protocols
- reviewer conflicts must be checked before invitation
- identity leakage must be checked before review
- reviews must be moderated before author release
- every decision must include editorial rationale
- media rights must be verified before publication
- generated review PDFs expire automatically
- canonical document and audit log must never be overwritten destructively

## 18. Acceptance Criteria
The platform is launch-ready when:
- authors can submit text + media
- system builds canonical document and HTML render
- editor can screen and select reviewers from suggested set
- reviewer can complete structured review with annotations
- conflicting reviews are flagged
- moderated review package can be sent to authors
- revised submissions are versioned correctly
- accepted article can publish in HTML and PDF
- video and audio stream with access controls
- audit trail covers all core workflow steps

## 19. Key Takeaways
- peer review is editorially governed, not a vote
- structured source is better than PDF extraction
- LaTeX is excellent for structured text but not for multimedia delivery
- media should be uploaded separately and referenced from text
- HTML should be the primary review and publication medium
- PDF should be generated from canonical structure and treated as ephemeral unless specifically archived
- AI should support editors, not replace them
- a single integrated platform is strategically stronger for artistic research than stitching together unrelated tools

## 20. ScholarOne Manuscripts Context
ScholarOne Manuscripts is used in conventional publishing as a submission and peer review workflow system: manuscript intake, editorial assignment, reviewer invitation, review collection, and decision tracking.

For this new journal, an integrated system is preferable if the journal requires:
- rich media support
- streaming access control
- media-aware review
- custom reviewer recommendation
- artistic research-specific workflows
- unified author-to-publication pipeline

The tradeoff is that the journal must own long-term maintenance and governance.
