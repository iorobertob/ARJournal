# Trans/Act Journal — Site Map

## Public Site

| URL | Page | Description |
|-----|------|-------------|
| `/` | Home | Journal landing page with featured articles and current issue highlights |
| `/issues/<number>/` | Issue Detail | Table of contents for a single journal issue with article listings |
| `/articles/<slug>/` | Article | Full published article in HTML with multimedia, metadata, and citation info |
| `/archive/` | Archive | Chronological list of all published issues and volumes |
| `/about/` | About | Journal information, mission statement, and editorial board |
| `/submit/` | Submit Info | Author guidelines and instructions for submitting a manuscript |
| `/authors/<pk>/` | Author Page | Public profile page for a specific author with their published works |
| `/download/template/` | Download Template | Download the LaTeX submission template file |

---

## Authentication (django-allauth)

| URL | Page | Description |
|-----|------|-------------|
| `/accounts/login/` | Login | Email/password sign-in form |
| `/accounts/logout/` | Logout | Sign-out confirmation and redirect |
| `/accounts/signup/` | Sign Up | New user registration form |
| `/accounts/email/` | Email Management | Add, verify, and set primary email address |
| `/accounts/email/<key>/confirm/` | Email Confirmation | Confirm email address via link sent to inbox |
| `/accounts/password/reset/` | Password Reset | Request a password reset email |
| `/accounts/password/reset/done/` | Password Reset Sent | Confirmation that reset email has been sent |
| `/accounts/password/reset/key/<key>/` | Set New Password | Enter and save a new password via reset token |
| `/accounts/password/reset/key/done/` | Password Reset Done | Confirmation that password was successfully changed |
| `/accounts/confirm-email/` | Verification Sent | Notification that a verification email has been dispatched |
| `/accounts/social/login/cancelled/` | Social Login Cancelled | Shown when a social (ORCID) OAuth flow is cancelled |

---

## Author Portal

| URL | Page | Description |
|-----|------|-------------|
| `/author/dashboard/` | Author Dashboard | Overview of all the user's submissions and their current statuses |
| `/author/profile/` | Profile | View the author's public-facing profile details |
| `/author/profile/edit/` | Edit Profile | Form to update bio, affiliation, ORCID, and profile photo |
| `/author/submission/<pk>/` | Submission Detail | Full status view of a single submission including decisions and history |

### New Submission Wizard

| URL | Page | Description |
|-----|------|-------------|
| `/author/submit/step1/` | Submit — Step 1 | Enter manuscript title, abstract, keywords, and co-author information |
| `/author/submit/<pk>/step2/` | Submit — Step 2 | Upload the primary LaTeX source file and any supplementary assets |
| `/author/submit/<pk>/step3/<rev>/` | Submit — Step 3 | Review the auto-generated HTML preview of the parsed manuscript |
| `/author/submit/<pk>/step4/<rev>/` | Submit — Step 4 | Confirm submission, accept policies, and finalize |

### Revision Wizard (after editorial decision)

| URL | Page | Description |
|-----|------|-------------|
| `/author/submit/<pk>/revise/step1/` | Revise — Step 1 | Author response to editor comments and revision notes |
| `/author/submit/<pk>/revise/<rev>/step2/` | Revise — Step 2 | Upload revised LaTeX file and updated supplementary assets |
| `/author/submit/<pk>/revise/<rev>/step3/` | Revise — Step 3 | Review HTML preview of the revised manuscript before resubmitting |

### Asset Management

| URL | Action | Description |
|-----|--------|-------------|
| `/author/submit/<pk>/revision/<rev>/asset/<asset_pk>/delete/` | Delete Asset | Remove a specific supplementary asset from a draft revision (POST) |

---

## Editorial Dashboard

| URL | Page | Description |
|-----|------|-------------|
| `/editorial/` | Editorial Dashboard | Queue of all active submissions with status filters for editors |
| `/editorial/submission/<pk>/` | Editorial Submission Detail | Full detail view of a submission including reviews, history, and action controls |
| `/editorial/submission/<pk>/screen/` | Record Screening | Record initial desk-review screening outcome (accept/reject for review) |
| `/editorial/submission/<pk>/decide/` | Record Decision | Record a formal editorial decision (accept, revise, reject) |
| `/editorial/submission/<pk>/assign/` | Assign Editor | Assign or reassign a handling editor to a submission |
| `/editorial/submission/<pk>/editors/search/` | Editor Search | HTMX JSON endpoint for live search of eligible editors (autocomplete) |

---

## Reviewer Workflow

### Reviewer Dashboard & Workspace

| URL | Page | Description |
|-----|------|-------------|
| `/review/my-reviews/` | Reviewer Dashboard | List of all review invitations assigned to the reviewer with status and deadlines |
| `/review/workspace/<invitation_pk>/` | Review Workspace | Split-pane review interface showing the manuscript alongside the review form |
| `/review/<review_pk>/moderate/` | Moderate Review | Editorial view to moderate, flag, or release a completed review |

### Review Actions (HTMX / AJAX)

| URL | Action | Description |
|-----|--------|-------------|
| `/review/<review_pk>/draft/` | Save Draft | Autosave the in-progress review form (POST) |
| `/review/<review_pk>/submit/` | Submit Review | Finalize and submit the completed review (POST) |
| `/review/<review_pk>/annotate/` | Add Annotation | Attach an inline annotation to a specific part of the manuscript (POST) |

### Reviewer Invitation (Magic Link)

| URL | Page | Description |
|-----|------|-------------|
| `/review/invitation/<token>/` | Invitation Response | Reviewer accepts or declines a review invitation via emailed magic link |

### Reviewer Suggestion (Editorial Actions — HTMX)

| URL | Action | Description |
|-----|--------|-------------|
| `/review/suggest/<submission_pk>/` | Generate Suggestions | Trigger AI-powered reviewer scoring and show ranked suggestions |
| `/review/suggest/<submission_pk>/search/` | Reviewer Search | Live JSON search for reviewers by name or expertise (autocomplete) |
| `/review/suggest/<submission_pk>/add/` | Add Suggestion | Manually add a reviewer to the candidate list |
| `/review/approve/<suggestion_pk>/` | Approve Reviewer | Mark a suggested reviewer as approved to receive an invitation |
| `/review/remove/<suggestion_pk>/` | Remove Suggestion | Remove a reviewer from the candidate list |
| `/review/invite/<submission_pk>/` | Send Invitations | Dispatch invitation emails to all approved reviewer candidates |

---

## Production

| URL | Page / Action | Description |
|-----|---------------|-------------|
| `/production/build/<document_pk>/` | Build HTML | Trigger (re)build of the HTML article from the canonical document (POST) |
| `/production/publish/<document_pk>/` | Publish Article | Publish the HTML build and make the article publicly accessible (POST) |
| `/production/pdf/request/<document_pk>/` | Request PDF | Enqueue a PDF export job for the article |
| `/production/pdf/download/<token>/` | Download PDF | Download a previously generated PDF via secure token |
| `/production/admin/preview/<document_pk>/` | Admin Preview | Internal staff preview of the HTML build before publication |
| `/production/admin/pdf/<document_pk>/` | Admin PDF | Staff-initiated PDF generation for editorial/archiving use |

---

## Notifications

| URL | Page / Action | Description |
|-----|---------------|-------------|
| `/notifications/` | Notification List | Inbox of all in-app notifications for the current user |
| `/notifications/mark-read/` | Mark All Read | Mark all unread notifications as read (POST) |

---

## Documents (Internal)

| URL | Action | Description |
|-----|--------|-------------|
| `/documents/<pk>/json/` | Canonical Document JSON | Return the raw canonical JSON representation of a parsed document (debug/API use) |

---

## Journal Admin (Platform Admin — not Django Admin)

| URL | Page | Description |
|-----|------|-------------|
| `/journal-admin/` | Admin Dashboard | Platform overview with aggregate stats for editors-in-chief and managers |
| `/journal-admin/users/` | User List | Browse and search all registered users with role filters |
| `/journal-admin/users/<pk>/edit/` | Edit User | Edit a user's roles, permissions, and profile fields |
| `/journal-admin/settings/` | Journal Settings | Edit the JournalConfig singleton: name, ISSN, description, policies |
| `/journal-admin/issues/` | Issue List | List all volumes and issues |
| `/journal-admin/issues/new/` | Create Issue | Create a new journal issue/volume |
| `/journal-admin/issues/<pk>/` | Edit Issue | Edit issue metadata and arrange article sections and ordering |
| `/journal-admin/articles/` | Article List | Browse all articles in the production pipeline |
| `/journal-admin/articles/<pk>/` | Article Detail (Admin) | Full production view of an article: HTML build, PDF, DOI, and publish controls |

---

## REST API (`/api/v1/`)

| URL | Method | Description |
|-----|--------|-------------|
| `/api/v1/submissions/` | GET, POST | List or create submissions (JWT auth) |
| `/api/v1/submissions/<pk>/` | GET, PUT, PATCH, DELETE | Retrieve or update a specific submission |
| `/api/v1/editor/reviewer-suggestions/<submission_id>/` | GET | Fetch ranked reviewer suggestions for a submission |
| `/api/v1/editor/reviewer-invitations/` | GET, POST | List or create reviewer invitations |
| `/api/v1/editor/decisions/` | GET, POST | List or record editorial decisions |
| `/api/v1/reviews/<review_id>/` | GET | Retrieve a specific review |
| `/api/v1/reviews/<review_id>/annotations/` | GET, POST | List or add annotations on a review |
| `/api/v1/documents/<document_id>/exports/pdf/` | POST | Request a PDF export for a document |
| `/api/v1/public/articles/<document_id>/` | GET | Publicly accessible article metadata and content (no auth) |
| `/api/v1/public/issues/` | GET | Publicly accessible list of all published issues (no auth) |

---

## Django Admin

| URL | Description |
|-----|-------------|
| `/admin/` | Django's built-in admin interface for direct database management (superusers only) |

---

## Debug (Development Only)

| URL | Description |
|-----|-------------|
| `/__debug__/` | Django Debug Toolbar panel (only active when `DEBUG=True`) |



