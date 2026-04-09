# Artistic Research Academic Journal Platform — Technical Specification

Version: 1.1  
Date: 2026-04-08  
Purpose: This document specifies the functional, workflow, governance, data, and technical requirements for building an integrated online platform for an artistic research academic journal. The platform must support the full lifecycle from author onboarding and submission through editorial triage, reviewer suggestion, peer review, moderation of reviews, revision, acceptance, production, publication, access control, post-publication governance, and analytics.

---

## 1. Product Goal

Build a single integrated journal platform optimized for artistic research, able to handle text-based scholarship together with rich media objects such as images, audio, video, and supplementary materials. The platform must support rigorous peer review, editorial governance, ethical compliance, flexible publication workflows, and long-term preservation.

The system should be modular enough to evolve, but integrated enough that authors, editors, reviewers, production staff, and administrators work inside one coherent environment rather than across disconnected tools.

---

## 2. Guiding Principles

1. Editorial rigor first.
2. Human editorial authority remains final.
3. AI assistance may support but not replace accountable editorial decisions.
4. Accessibility, transparency, privacy, and auditability are mandatory.
5. Artistic research requires support for multimodal outputs, not only PDFs.
6. Open standards and interoperability are preferred over vendor lock-in.
7. The system must be usable by small editorial teams and scalable for growth.
8. Reviews sent to authors may be moderated for tone, ethics, and clarity, but never altered in substantive meaning.
9. Conflicting reviews resolved through editorial mediation, not score averaging.
10. Reviewer suggestion must remain explainable and editor-controlled.

---

## 3. Scope

The platform must cover the following 18 areas of journal operations, plus platform-specific extensions.

### 3.1 Manuscript Preparation
- Journal information pages and author guidelines.
- Structured submission instructions.
- Downloadable author templates.
- LaTeX template support.
- Word processor template support as optional future extension.
- Required metadata validation before submission.

### 3.2 Submission System
- User registration, login, password reset, ORCID linking.
- Author dashboard.
- New submission wizard.
- Upload of manuscript files, media, supplementary files, data appendices, cover letter.
- Metadata entry: title, abstract, keywords, discipline, sub-discipline, artistic medium, affiliations, funding, ethics, copyright status, accessibility notes.

### 3.3 Editorial Screening / Desk Review
- Initial technical completeness check.
- Scope fit assessment.
- Ethics and compliance screening.
- Similarity / plagiarism integration. (LMTA has a Turnitin institutional account)
- Desk reject / send to editor / request technical corrections.

### 3.4 Reviewer Selection
- Reviewer database.
- Reviewer profile management.
- Automated reviewer suggestion engine proposing 3 reviewers.
- Conflict detection.
- Editorial review and approval of reviewer selection.
- Invitation dispatch only after editorial approval.

### 3.5 Peer Review Models
- Single-anonymized.
- Double-anonymized.
- Open review.
- Optional post-publication commentary in later phase.
- Journal-configurable model per section or issue.

### 3.6 Review Process
- Reviewer invitation, acceptance, decline.
- Review deadline tracking.
- Structured review forms.
- Confidential comments to editor.
- Comments to author.
- Scoring rubric and narrative review.
- Attachment of annotated files when allowed.
- Reviewers' reviews log/history.

### 3.7 Revision Cycles
- Major revision.
- Minor revision.
- Reject and resubmit as new submission.
- Revision comparison and version history.
- Response-to-reviewers document upload.

### 3.8 Decision Aggregation
- Editor dashboard summarizing reviews.
- Recommendation aggregation with weighted review visibility.
- Tie-breaking / conflicting review workflow.
- Senior editor escalation.

### 3.9 Acceptance and Production
- Acceptance letter generation.
- Copyediting workflow.
- Layout/typesetting workflow.
- Verifification and upload of support material, images, media files, etc. in the format specified by editorial team.
- Proof generation.
- Author proof corrections.
- Final publication package assembly.

### 3.10 Fees and Business Models
- No-fee model support.
- APC support if enabled.
- Waiver and discount support.
- Invoice tracking.
- Payment gateway integration as optional module.

### 3.11 Reviewer Compensation
- Default unpaid reviewer workflow.
- Optional honorarium support.
- Reviewer contribution certificates.
- Reviewer recognition logs.
- Reviewer invoice upload option.

### 3.12 Publication and Access
- Online publication.
- Public article landing page.
- HTML reading view.
- Rich media streaming for audio and video.
- Embedding of image galleries, audio players, and video players.
- Downloadable PDF. FLAT or RICH option given.
- Access modes: open, embargoed, subscriber-only, registered-user-only, set by editors.

### 3.13 Copyright and Licensing. List options when standard/common cases.
- Author agreements.
- Copyright transfer or license-to-publish workflows.
- Creative Commons license selection.
- Media rights declarations.
- Third-party rights documentation.

### 3.14 Royalties
- Default no-author-royalty academic model.
- Optional commissioned-content payment support.
- Contract metadata storage.

### 3.15 Notifications and Tracking
- System email notifications.
- In-platform notifications.
- Status history.
- Deadline reminders.
- Escalation alerts for overdue actions.

### 3.16 Ethics and Integrity Standards
- Conflict-of-interest declarations.
- Human/animal ethics documentation.
- Misconduct flags.
- Retraction, correction, and expression-of-concern workflows.
- Audit logs.

### 3.17 Emerging / Advanced Practices
- Open peer review options.
- Preprint linking.
- Data/code deposit linkage.
- AI-use disclosure by authors and reviewers. Provide LLM projects; delcare/calculate percentage of use.
- Registered reports support as future module. Statistics.

### 3.18 Platform Architecture for Journal Operations
- Submission portal.
- Editorial dashboard.
- Reviewer-matching engine.
- Reviewer dashboard and manuscript view.
- Blind review support.
- Decision engine.
- Communication service.
- Publishing pipeline.
- DOI and metadata integration.
- Analytics and reporting.

---

## 4. Core User Roles

### 4.1 Public Reader / Researcher
- Browse journal site.
- Search published articles.
- View article metadata.
- Access allowed files and streaming media.

### 4.2 Author
- Register and manage profile.
- Link ORCID.
- Submit manuscripts and media.
- Track status.
- Revise submissions.
- Review proofs.
- Sign agreements.

### 4.3 Reviewer
- Maintain expertise profile.
- Accept or decline invitations.
- Perform and submit structured reviews.
- Declare conflicts.
- Download review files when permitted.
- Receive certificates.
- Receive honoraria if enabled.

### 4.4 Section Editor / Handling Editor
- Triage submissions.
- Review reviewer recommendations.
- Invite reviewers.
- Monitor review progress.
- Moderate reviews before relese to author .
- Draft decision recommendations.
- Communicate with authors.
- Release moderated reviews to author along decision letter.

### 4.5 Editor-in-Chief / Senior Editor
- Final decision authority.
- Escalation handling.
- Policy configuration.
- Oversight of ethics, appeals, and conflicting-review cases.

### 4.6 Managing Editor
- Workflow administration.
- Compliance checks.
- Communication templates.
- Issue scheduling.
- Timeline monitoring.

### 4.7 Copyeditor / Production Editor
- Copyediting.
- Proofing.
- Layout prep.
- Publication-ready asset checks.

### 4.8 Journal Administrator
- User management.
- Taxonomy management.
- Settings and integrations.
- Reporting.

### 4.9 Finance / Publisher Admin
- APC invoices.
- Waivers.
- Payment tracking.

### 4.10 System Administrator / DevOps
- Infrastructure.
- Security.
- Backups.
- Monitoring.
- Deployment.

---

## 5. End-to-End Workflow

### 5.1 Author Submission Workflow
1. Author registers or logs in.
2. Author completes profile including ORCID, affiliation, biography, keywords, declared interests, discipline areas, and accessibility contact details.
3. Author starts submission and selects article type.
4. System presents submission checklist.
5. Author uploads manuscript and media assets.
6. System extracts basic metadata where possible.
7. Author completes structured metadata.
8. Author confirms declarations: originality, ethics, conflicts, AI-use statement, copyright.
9. System validates required fields.
10. Submission enters `Submitted - Awaiting Technical Check` state.

### 5.2 Technical Check Workflow
1. Managing editor checks completeness.
2. System runs file validation, virus scan, media transcode queue check, similarity check if enabled.
3. Outcome:
   - return to author for corrections,
   - advance to desk review,
   - reject if clearly out of scope or invalid.

### 5.3 Desk Review Workflow
1. Editor examines fit, relevance, originality, quality threshold.
2. Editor can desk reject, request clarification, or move to reviewer recommendation.
3. Submission state changes accordingly.

### 5.4 Reviewer Suggestion Workflow
1. System proposes exactly 3 reviewer candidates plus optional alternates.
2. Each suggestion includes rationale, similarity indicators, workload, timeliness, and conflict flags.
3. Editor reviews suggestions.
4. Editor accepts, replaces, or supplements candidates.
5. Only after editor approval may reviewer invitations be sent.
6. Editor is notified in every step. 

### 5.5 Review Workflow
1. Invitations sent to approved reviewers.
2. Reviewers accept or decline.
3. Replacement suggestions appear if invitation fails.
4. Reviewer completes review.
5. System stores scores, recommendation, author comments, editor comments, attachments.
6. Completed reviews enter `Moderation Required` state before author release.

### 5.6 Review Moderation and Conflict Workflow
1. Editor or designated editorial staff inspects each completed review.
2. System flags tone, identity leaks, bias markers, policy risks, and recommendation divergence.
3. Editor moderates author-visible comments where needed without changing substantive meaning.
4. Editor classifies comments into major issues, minor issues, suggestions, or questions.
5. If conflict threshold is met, system opens a conflict-resolution panel.
6. Editor may request an additional reviewer, proceed with mediated decision, or escalate to senior editor.
7. Editor drafts decision letter synthesizing all reviews.

### 5.7 Decision Workflow
1. Editor reviews moderated reports and conflict summary if any.
2. Editor recommendation goes to senior editor if configured.
3. Final decision sent: accept, minor revision, major revision, reject, reject-resubmit.
4. Authors receive moderated reviewer comments plus editorial decision letter.
5. Notifications are recorded.

### 5.8 Revision Workflow
1. Author uploads revised files and response letter.
2. System links revisions to prior round.
3. Author must respond point-by-point to all major issues.
4. Editor decides whether to send to original reviewers, a subset, a new reviewer, or decide directly.
5. Repeat until final decision.

### 5.9 Production Workflow
1. Acceptance package created.
2. Agreements and licensing finalized.
3. Copyediting and typesetting begin.
4. Proofs generated.
5. Author proof corrections submitted.
6. Final assets approved.
7. DOI minted and metadata deposited.
8. Article published.

### 5.10 Post-Publication Workflow
- Corrections.
- Retractions.
- Metrics updates.
- Media replacement only under policy.
- Cross-linking to issue and indexing feeds.
- Citation count.

---

## 6. Reviewer Suggestion Engine (Required Feature 1.1)

### 6.1 Objective
Provide a light but smart recommendation engine that suggests 3 reviewers for each submission using journal metadata and reviewer profiles. This feature assists editors but never automatically sends the manuscript.

### 6.2 Inputs
Submission metadata:
- title
- abstract
- keywords
- discipline
- sub-discipline
- artistic medium
- methodology
- language
- references or cited-author list when extractable
- author affiliations
- author ORCID and declared interests
- funding declarations
- conflict declarations
- geographic focus if relevant
- issue or section assignment

Reviewer profile metadata:
- expertise keywords
- discipline and sub-discipline tags
- methodological interests
- artistic medium tags
- language proficiency
- institution
- prior review history
- responsiveness score
- average turnaround time
- conflict exclusions
- co-authorship / institutional relationships if data available
- declared unavailable dates
- current workload
- preferred review models
- prior editorial quality rating
- availability by language and media type

### 6.3 Functional Rules
- Recommend exactly 3 primary reviewer candidates.
- Produce a ranked list plus optional alternates.
- Never auto-invite reviewers.
- Surface human-readable justification for each recommendation.
- Flag conflict risks clearly.
- Exclude reviewers who violate hard conflict rules.
- Allow editor to accept, reject, replace, or search manually.
- Preserve explainability for every score component.
- Bias-check the final list for over-concentration by institution, geography, or repeated reviewer reuse when policy requires.
- Dont always invite the same reviewer. Use a "temperature" probability choosing.

### 6.4 Hard Exclusions
- same person as author
- same current institution as any author if policy marks this as disqualifying
- declared conflict between author and reviewer
- reviewer at maximum workload
- reviewer inactive or suspended
- reviewer unavailable during decision window
- reviewer opted out of the topic, issue, article type, or language
- reviewer previously declined the same manuscript or earlier version
- reviewer was an acknowledged collaborator or contributor on the submission

### 6.5 Soft Penalties
- recent co-authorship with an author
- prior affiliation overlap within configurable cooling-off period
- repeated use by same editor within configurable period
- heavy recent workload
- slow turnaround history
- low editorial quality rating on past reviews
- prior no-response pattern
- overrepresentation of one institution, region, or disciplinary cluster

### 6.6 Scoring Model
The initial engine must use deterministic weighted scoring with explainable factors.

Base score:

`reviewer_score = expertise_similarity * 0.26 + discipline_match * 0.14 + keyword_overlap * 0.10 + methodology_match * 0.08 + artistic_medium_match * 0.06 + semantic_abstract_similarity * 0.10 + language_match * 0.04 + availability_score * 0.06 + timeliness_score * 0.05 + workload_balance * 0.04 + editor_quality_score * 0.03 + diversity_balance_score * 0.04`

Final score:

`final_score = reviewer_score - conflict_risk_penalty - reuse_penalty - overload_penalty - recency_penalty`

All scores must be normalized to a 0-100 scale for UI display.

### 6.7 Matching Logic by Factor
- `expertise_similarity`: overlap between reviewer expertise profile and submission abstract/title/keywords.
- `discipline_match`: exact or close match on discipline and sub-discipline taxonomy.
- `keyword_overlap`: token overlap and synonym-aware overlap of journal-controlled vocabulary.
- `methodology_match`: alignment on methods such as practice-based research, ethnography, archival method, performance studies, critical making, etc.
- `artistic_medium_match`: alignment on media such as image, moving image, sound, installation, performance, digital art.
- `semantic_abstract_similarity`: vector similarity between submission abstract and reviewer expertise statement if embeddings are enabled.
- `language_match`: fluency alignment with submission language.
- `availability_score`: inverse of current commitments and declared unavailable periods.
- `timeliness_score`: based on prior average review turnaround and reminder burden.
- `workload_balance`: favors capable reviewers with sustainable load rather than repeatedly selecting the same few people.
- `editor_quality_score`: based on internal editorial feedback about past review usefulness.
- `diversity_balance_score`: increases score where it helps produce a balanced review pool.

### 6.8 Ranking Pipeline
1. Collect all active reviewer profiles.
2. Apply hard exclusions.
3. Compute deterministic factor scores.
4. Apply soft penalties.
5. Sort by final score.
6. Run diversity and duplication checks.
7. Select top 3 candidates, ensuring no policy violation in final trio. Use a "temperature" probability choosing.
8. Generate 3-5 alternates.
9. Present results to editor with rationale.

### 6.9 Explainability Output
For each suggested reviewer, display:
- overall score
- top matching reasons
- discipline and method overlap
- keyword and semantic similarity indicators
- conflict status
- workload status
- average turnaround estimate
- number of reviews completed in past 12 months
- last time used by this journal
- penalties applied

Example rationale:

`Suggested because the reviewer matches performance studies + sound art, has high alignment with practice-based methodology, no conflict detected, moderate workload, and average turnaround of 16 days.`

### 6.10 Editorial Controls
- Editor approval required before invitation.
- Editor may override ranking.
- Editor may request one-click reranking with adjusted priorities, such as stronger methodological match or faster turnaround.
- All overrides logged.
- System may learn from approved actions later, but only with explicit opt-in and auditability.

### 6.11 Bias and Fairness Controls
- Track reviewer selection distribution by institution, region, gender if voluntarily provided, and discipline cluster where lawful.
- Prevent repetitive concentration on the same reviewers.
- Log override patterns that may reveal hidden editorial bias!
- Surface a fairness warning if all top suggestions come from one institutional or disciplinary cluster.

### 6.12 Implementation Approach
Phase 1:
- metadata-based ranking using deterministic weighted scoring
- controlled vocabulary and synonym dictionary
- no black-box AI requirement

Phase 2 optional:
- semantic similarity embedding service for abstract-to-expertise matching
- reviewer-network graph risk detection
- adaptive ranking based on editor approvals
- explainability layer remains mandatory

---

## 7. Review Moderation, Conflict Resolution, and Editorial Mediation Module

### 7.1 Purpose
Ensure professional, ethical, and useful communication to authors while preserving reviewer intent and editorial authority.

### 7.2 Review Lifecycle States
Each review must pass through these states:

`SUBMITTED -> MODERATION_REQUIRED -> MODERATED -> INCLUDED_IN_DECISION -> RELEASED_TO_AUTHOR`

Rules:
- Reviews are not visible to authors before moderation.
- Editor or delegated editorial staff approval is mandatory.
- Original submitted review text is immutable.
- Moderated author-facing copy is versioned separately.

### 7.3 Moderation Principles
Editors may:
- correct grammar or typos when meaning is unchanged
- remove insults, discriminatory language, and policy violations
- redact accidental identity disclosure in blind-review settings
- move confidential comments out of author-visible channels
- tag comments by significance and actionability

Editors may not:
- alter substantive judgment
- change a recommendation without preserving the raw original review record
- invent reviewer opinions
- merge multiple reviews into a fake unified review voice

### 7.4 Moderation Interface Requirements
The editor dashboard must provide:
- side-by-side raw and moderated review views
- separate panes for author-visible and editor-confidential sections
- phrase-level diff view
- comment tagging controls
- policy-warning panel
- approval action with reason log

### 7.5 Comment Classification
Each moderated comment may be tagged as:
- `MAJOR_ISSUE`
- `MINOR_ISSUE`
- `SUGGESTION`
- `QUESTION`
- `POLICY_NOTE`

### 7.6 AI Assistance Boundaries for Moderation
Allowed AI assistance:
- harsh-tone detection
- clarity rewrite suggestions
- identity leak detection
- citation manipulation warning
- contradiction extraction
- summary drafting for editor review

Not allowed:
- automatic publication of rewritten review
- auto-sending to author without human approval
- automatic alteration of recommendation

### 7.7 Conflict Detection Rules
The system must flag conflict when one or more conditions are met:
- recommendation divergence exceeds threshold, such as `ACCEPT` vs `REJECT`
- score spread exceeds configurable limit
- one review praises originality while another identifies fatal validity flaws
- one review requests minor revision while another requests major conceptual reframing
- semantic contradiction detection identifies directly opposing evaluations

Conflict types:
- recommendation conflict
- severity conflict
- conceptual conflict
- methodological conflict
- scope-fit conflict

### 7.8 Conflict Resolution Paths
When conflict is flagged, the editor may:
1. issue an editorially mediated decision without extra review
2. request an additional reviewer
3. escalate to senior editor or editorial board
4. return to author with major revision framed around the contested issues
5. reject with editorial rationale despite disagreement

### 7.9 Editorial Decision Builder
The system must require completion of a structured decision package before author notification.

Required fields:
- `decision_type`
- `editor_summary`
- `priority_issues[]`
- `conflict_resolution_note`
- `instructions_to_author`
- `internal_reasoning_note` for staff-only visibility

### 7.10 Author Communication Package
Authors receive:
1. editorial decision letter
2. moderated reviewer comments
3. structured list of priority issues
4. revision response template when revision is invited

### 7.11 Audit and Transparency
System must store:
- original review
- moderated review
- moderation log
- AI suggestions and whether they were accepted or rejected
- editor approval identity and timestamp
- conflict flags and resolution path

### 7.12 Revision Enforcement
When a revised manuscript is submitted:
- response to all `MAJOR_ISSUE` items is required
- editor must mark whether each issue is resolved, partially resolved, or unresolved
- unresolved major issues should be surfaced if manuscript is re-sent to reviewers

---

## 8. LaTeX Template Support (Required Feature 1.2)

### 8.1 Purpose
Authors must be able to prepare submissions using an official LaTeX template appropriate for artistic research articles.

### 8.2 Requirements
- Provide downloadable `.tex` template package, including `.bib` file.
- Include support for figures, tables, footnotes, captions, appendices.
- Include multimedia reference placeholders.
- Include metadata fields for title, authors, affiliations, ORCID, abstract, keywords, funding, acknowledgements.
- Include accessibility notes section for media descriptions.
- Include rights statement placeholder for third-party artistic material.
- Include sample guidance for linking supplementary media hosted by the platform.

### 8.3 Platform Behavior
- Submission form accepts ZIP package containing `.tex`, `.bib`, media assets, and ancillary files.
- Optional PDF compilation validation service can preflight the template package.
- Production staff may convert LaTeX source into final HTML, PDF and structured XML/HTML where feasible.
- Journal site must host the template and version it uses.
- Template version used by the submission must be stored in metadata.

### 8.4 Minimal Template Sections
- Title page
- Abstract
- Keywords
- Main body
- Figures / image plates
- Audio/video references
- Acknowledgements
- Funding
- Conflict of interest
- AI-use disclosure
- References
- Appendices

### 8.5 Suggested Template Package Contents
- `journal-template.tex`
- `journal-template.cls` or `sty` file
- `references.bib`
- `sample-article.tex`
- `README.md`
- `media-guidelines.pdf` or markdown equivalent
- `license-notes.md`

---

## 9. Functional Requirements by Module

### 9.1 Authentication and Identity
- Email/password authentication.
- Password reset.
- Optional SSO for staff.
- ORCID OAuth linking.
- MFA for admin and editorial roles.
- Role-based access control.

### 9.2 Profiles
- Public and private profile fields separated.
- Author profile.
- Reviewer expertise profile.
- Editorial role permissions.

### 9.3 Submission Management
- Submission wizard with autosave.
- Draft submissions.
- File upload with progress indicator.
- Chunked uploads for large media.
- Validation rules by article type.
- Submission cloning for resubmissions.

### 9.4 Media Asset Handling
- Support images, audio, video, PDF, ZIP, .maxpat, .json, svg, captions, transcripts.
- Generate derivatives where policy allows.
- Streaming delivery for audio and video.
- Access controls on non-public media.
- Fixity and checksum validation.

### 9.5 Editorial Dashboard
- Queue views by status.
- Filters by section, editor, age, article type.
- Reviewer suggestion panel.
- Conflict warnings.
- Review moderation panel.
- Decision controls.

### 9.6 Review Management
- Invitation templates.
- Reminder rules.
- Review forms configurable per article type.
- Review attachments.
- Anonymization support.
- Moderation workflow before author release.

### 9.7 Production and Publishing
- Copyediting tasks.
- Proof approval.
- Publication scheduling.
- DOI assignment.
- Issue assembly and continuous publication modes.

### 9.8 Billing (Optional)
- Invoice generation.
- Waiver tracking.
- Payment status.

### 9.9 Notifications
- Event-triggered email templates.
- In-app notifications.
- Daily digest option for editors.

### 9.10 Reporting and Analytics
- Submission counts.
- Desk reject rates.
- Time to first decision.
- Reviewer acceptance rates.
- Publication latency.
- Article usage metrics.
- reviewer diversity and reuse metrics
- moderation and conflict-resolution statistics

---

## 10. Non-Functional Requirements

### 10.1 Performance
- Page responses under 2 seconds for most dashboard actions.
- Large file uploads resilient to interruption.
- Background jobs for transcode, similarity checks, metadata deposits.

### 10.2 Security
- TLS everywhere.
- Encrypted secrets.
- RBAC, Role Based Access Control. 
- MFA for sensitive roles, user opts in.
- Audit log for all editorial decisions and permission changes.
- Malware scanning on uploads.

### 10.3 Privacy and Compliance
- GDPR-compliant consent and privacy notices.
- Data retention policies.
- Review confidentiality enforcement.
- Right-to-access and deletion workflows where legally applicable.

### 10.4 Accessibility
- WCAG 2.2 AA target.
- Keyboard navigation.
- Screen-reader compatible forms.
- Caption and transcript support for time-based media.

### 10.5 Reliability
- Automated backups.
- Disaster recovery runbook.
- Infrastructure monitoring and alerting.
- Transaction-safe workflow state changes.

### 10.6 Maintainability
- Modular architecture.
- API-first design.
- Test automation.
- Versioned configuration.

---

## 11. Suggested System Architecture

### 11.1 Architecture Style
A modular monolith is recommended for phase 1, with well-defined internal service boundaries and APIs. This reduces early complexity while preserving a path to future service extraction.

### 11.2 Major Components
1. Web frontend
2. API backend
3. Workflow engine
4. Relational database
5. Object storage for files/media
6. Search index
7. Background job queue
8. Notification service
9. Transcoding service
10. DOI / metadata integration service
11. Analytics service
12. Authentication / identity integration
13. Review moderation service
14. Reviewer suggestion and scoring service
15. Transcoding libraries. 
16. AI tools or connectiosn where needed. 

### 11.3 Suggested Stack
Frontend:
- Next.js or equivalent modern web framework
- TypeScript
- Accessible component library

Backend:
- Python with Django/FastAPI
- REST API with optional GraphQL read layer
- Env variables in a .env file (i.e. mailing service keys, etc).

Database:
- PostgreSQL

Object Storage:
- S3-compatible storage

Search:
- PostgreSQL full-text for smaller scale

Queue:
- Redis + worker framework or RabbitMQ

Media:
- FFmpeg-based transcode pipeline

Documents:
- Pandoc and LaTeX build tools for conversion/preflight

Deployment:
- Self deployment to managed VPS.
- Docker containers in a future vertion.
- CI/CD pipeline
- Reverse proxy and CDN

---

## 12. Data Model Overview

Core entities:
- User
- Role
- Profile
- Institution
- Submission
- SubmissionVersion
- SubmissionFile
- MediaAsset
- ArticleType
- Keyword
- Discipline
- ReviewModel
- ReviewerProfile
- ReviewerSuggestion
- ReviewerSuggestionFactor
- ReviewerInvitation
- Review
- ReviewModeration
- ReviewForm
- Decision
- EditorialAssignment
- ConflictDeclaration
- ConflictAnalysis
- EthicsDeclaration
- LicenseAgreement
- PaymentRecord
- DOIRecord
- Publication
- Issue
- Notification
- AuditLog
- RetractionOrCorrection

### 12.1 Example Relationships
- A Submission has many SubmissionVersions.
- A SubmissionVersion has many SubmissionFiles.
- A Submission has many ReviewerSuggestions.
- A ReviewerSuggestion belongs to a ReviewerProfile and a Submission.
- A ReviewerSuggestion has many ReviewerSuggestionFactors.
- A Submission has many ReviewerInvitations.
- A ReviewerInvitation may produce one Review.
- A Review may have one ReviewModeration record.
- A Submission may have one or more ConflictAnalysis records.
- A Submission has many Decisions.
- A Publication belongs to a Submission.

---

## 13. Workflow States

Possible submission states:
- Draft
- Submitted - Awaiting Technical Check
- Incomplete - Returned to Author
- Under Desk Review
- Desk Rejected
- Reviewer Suggestions Ready
- Awaiting Editor Reviewer Approval
- Reviewer Invitations Sent
- Under Review
- Reviews Completed
- Moderation Required
- Conflict Review Required
- Awaiting Editorial Decision
- Minor Revision
- Major Revision
- Revision Submitted
- Accepted
- In Production
- Proofs with Author
- Ready for Publication
- Published
- Rejected
- Withdrawn
- Retracted
- Corrected

State transitions must be logged and permission-guarded.

---

## 14. Review Forms and Evaluation Criteria

The platform must support configurable review forms. A default artistic research review rubric should include:
- originality and contribution
- methodological rigor
- artistic/research integration
- relevance to journal scope
- clarity of argument or exposition
- media quality and documentation adequacy
- ethical and rights compliance
- citation and contextualization quality
- accessibility and usability of submitted media
- publication recommendation

Form types:
- numeric score
- Likert scale
- yes/no compliance checks
- free text
- confidential editor notes

Aggregation rule:
- Editor sees all review components.
- Authors do not see confidential editor notes.
- No automatic accept/reject solely by score.
- Conflicting recommendations trigger an editorial mediation requirement.

---

## 15. Notifications and SLA (Service Level Agreements) Defaults

Suggested default timelines:
- technical check: 3 business days
- desk review: 7 business days
- reviewer invitation response: 5 business days
- review completion: 21 days
- review moderation: 5 business days after final review receipt. Reviewers are notified when other reviewers submit.
- conflict escalation response: 5 business days
- minor revision by author: 14 days
- major revision by author: 30 days
- proof correction: 5 business days

Notification events:
- registration confirmation
- submission received
- submission returned for corrections
- desk decision
- reviewer invitation
- reviewer reminder
- overdue review notice
- moderation pending alert
- conflict detected alert
- editorial decision
- revision reminder
- acceptance
- proof available
- publication live

---

## 16. Ethics, Integrity, and Governance Protocols

The system must support:
- COI declarations by authors, reviewers, editors
- ethics approval upload where applicable
- AI-use disclosure
- similarity report attachment
- reviewer identity protection according to review model
- appeals workflow
- misconduct investigation case records
- correction and retraction notices linked to original articles
- review moderation audit trail
- bias and discrimination flagging in reviewer comments

Every decision affecting publication integrity must be auditable.

---

## 17. Rights, Licensing, and Access Control

Per submission/publication, store:
- copyright owner
- license type
- license text version
- embargo rules
- rights restrictions on media
- streaming-only flag for sensitive media
- download permissions by file

Access control must support:
- fully open article with downloadable files
- open metadata but restricted media files
- streaming-only audio/video
- embargo until publication date or later date

---

## 18. Publication Layer

### 18.1 Article Landing Page
- title
- subtitle
- authors and affiliations
- abstract
- keywords
- DOI
- citation format
- publication date
- issue/volume mapping
- article files
- media embeds
- rights/license display
- related materials

### 18.2 Indexing and Metadata Export
Support export or deposit to:
- Crossref DOI metadata
- OAI-PMH endpoint
- Dublin Core export
- JATS XML in future phase
- sitemap and structured metadata for discovery

### 18.3 Media Presentation
- image zoom/gallery
- audio streaming player
- video streaming player
- captions and transcript display
- poster images / thumbnails

---

## 19. APIs and Integrations

Required or recommended integrations:
- ORCID
- DOI provider such as Crossref
- email delivery provider
- similarity provider
- payment gateway if APC enabled
- cloud object storage
- analytics service
- optional institutional SSO

Internal API requirements:
- authenticated REST endpoints for all dashboard actions
- webhook/event system for workflow transitions
- admin configuration endpoints
- reviewer scoring explanation endpoints
- moderation diff and audit endpoints

---

## 20. Admin Configuration Requirements

Admin UI must allow configuration of:
- article types
- review model by section
- review forms
- editorial roles and permissions
- notification templates
- deadlines and reminders
- reviewer scoring weights
- conflict rules
- moderation rules and flags
- payment settings
- issue structure
- issue and volume creation, calls. 
- license options
- public site theme settings

---

## 21. AI Assistance Boundaries

Allowed AI assistance:
- reviewer suggestion ranking support
- metadata extraction from submissions
- language quality hints for staff review
- similarity anomaly flagging
- production metadata enrichment
- harsh-tone detection in reviews
- contradiction extraction across reviews
- draft editorial summaries for staff approval

Not allowed as fully autonomous action:
- final editorial decision
- automatic reviewer invitation without editor approval
- acceptance or rejection without accountable human review
- legal rights determination without staff confirmation
- automatic release of reviews to authors without moderation approval

All AI-assisted outputs must be explainable, reviewable, and overrideable.

---

## 22. Acceptance Criteria for MVP

The MVP is acceptable when it supports:
1. user registration and login
2. author submission with file uploads and metadata
3. editorial technical check and desk review
4. automated suggestion of 3 reviewers with editor approval required
5. reviewer invitation, acceptance, and structured review submission
6. moderation of reviews before author release
7. conflict detection and editorial mediation workflow
8. editorial decisions and revision rounds
9. acceptance, proofing, and publication workflow
10. article pages with PDF and media support
11. audit logging and role-based permissions
12. LaTeX template distribution and submission acceptance
13. full frontend and backend. 
14. eidtorial management dashboard to assemble, creaate and design issues and volumes. 

---

## 23. Recommended Delivery Phases

### Phase 1 — MVP
- authentication
- profiles
- submission workflow
- editorial dashboard
- reviewer suggestion engine v1
- reviewer workflow
- review moderation workflow
- conflict detection v1
- decisions and revisions
- publication pages
- DOI metadata prep
- full frontend and backend. 
- eidtorial management dashboard to assemble, creaate and design issues and volumes. 

### Phase 2 — Production and Media Enhancement
- copyediting module
- proofing workflows
- media transcoding and streaming optimization
- richer analytics
- APC module if needed
- semantic similarity for reviewer suggestions

### Phase 3 — Advanced Scholarly Features
- open peer review options
- preprint linking
- registered reports
- JATS XML
- advanced fairness monitoring
- adaptive reviewer matching with audit controls

---

## 25. Testing Requirements

Testing must include:
- unit tests for workflow logic
- integration tests for submission/review/decision transitions
- permission tests for every role
- upload and large-file handling tests
- accessibility testing
- email template tests
- reviewer suggestion rule tests
- moderation diff tests
- conflict-detection tests
- security testing and audit log verification

---

## 26. Takeaways Embedded as Product Rules

1. The platform is editor-led and reviewer-informed, not automated voting.
2. Reviewer compensation is optional and configurable, but the default model assumes unpaid scholarly contribution.
3. Double-anonymized review should be available as a first-class configuration option.
4. The entire workflow should be digitized in one coherent platform.
5. Revenue, if any, should come from journal policy choices such as Article Publication Charges (APC), not author royalties.
6. Conflicting reviews are expected and should trigger editorial mediation rather than automatic averaging.
7. Reviews may be moderated for professionalism and policy compliance, but reviewer meaning must remain intact.
8. AI should strengthen editorial work, not replace editorial accountability.



---

## 28. Final Recommendation

Build one integrated platform with a modular architecture. Use a workflow-centered journal management core, a publication and media presentation layer, a reviewer suggestion engine that supports but does not replace editorial judgment, and a moderation layer that ensures authors receive professional and well-mediated feedback. Prioritize strong governance, auditability, multimodal publication support, and open integrations.

This is the best fit for an artistic research journal whose identity depends not only on peer review, but also on how research objects, media, rights, editorial mediation, and public presentation are handled as part of the scholarly record.



## 28. Media + LaTeX Hybrid Architecture

### Core Principle
LaTeX is used as a structured authoring format, not as a multimedia container.

---

### Author Submission Model
Authors submit:
- `.tex` file (structured template provided by platform)
- `.bib` file (structured template provided by platform)
- Media files uploaded separately:
  - images
  - video
  - audio
  - other

---

### Structured Media Placeholders (LaTeX)

Example:

\begin{media}
\mediatype{video}
\mediafile{performance1.mp4}
\caption{Performance documentation}
\end{media}

or

\begin{figure}
\includegraphics{image1.jpg}
\caption{Artwork}
\end{figure}

---

### Parsing Pipeline

INPUT:
- .tex
- media assets

PROCESS:
- Parse LaTeX into structured Abstract Syntax Tree,AST (JSON)
- Detect media placeholders
- Link placeholders to uploaded assets

OUTPUT:
- HTML (primary rendering)
- PDF (generated on demand)

---

### Rendering Strategy

#### HTML (Primary)
- Fully interactive
- Embedded video/audio players
- Streaming enabled (no forced downloads)
- Timeline annotations supported

#### PDF (Secondary, Generated On Demand)

Two options:

1. Flat PDF
   - Images only
   - Media represented as:
     - thumbnail
     - caption
     - link or QR code

2. Interactive PDF (experimental)
   - Embedded media where supported
   - Fallback-safe

#### Important Rule:
- PDFs are generated on demand
- Files are discarded after download

---

### Reviewer Experience Update

Reviewers access:
- HTML interactive version (primary)
- Optional PDF download
- Media playable inline

---

### Media Handling

- Stored separately from manuscript
- Access-controlled streaming
- Adaptive bitrate for performance
- Rights management layer

---

### Key Design Principle

Structured text + external media = flexible, future-proof publishing

---

Generated: 2026-04-08T20:12:04.923075 UTC
