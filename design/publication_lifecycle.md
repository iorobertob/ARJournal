# Publication Lifecycle

## Three Independent "Published" Concepts

The platform has three distinct publication states that must all be understood together:

| State | Field | Meaning |
|---|---|---|
| **Manuscript status** | `Submission.status` | Where the article sits in the editorial pipeline |
| **HTML live** | `HTMLBuild.is_published` | Whether the rendered HTML is publicly accessible |
| **Issue page live** | `Issue.is_published` | Whether the issue index page is visible on the site |

These are set independently. A published issue page does not publish its articles. A published HTML build does not automatically update the manuscript status (though the `publish_article` view syncs both atomically — see below).

---

## Manuscript Status Flow

```
draft
  ↓  author submits (submissions/views.py :: new_submission_step4)
submitted
  ↓  editor screens (editorial/views.py :: record_screening)
desk_review
  ↓  editor opens review round (reviewers/views.py :: send_invitations)
under_review
  ↓  editorial decision (editorial/views.py :: record_decision)
  ├── REJECT        → rejected
  ├── DESK_REJECT   → desk_rejected
  ├── MINOR/MAJOR REVISION → revision_requested
  │         ↓  author resubmits (submissions/views.py :: resubmit_step3)
  │       revised
  │         ↓  (re-reviewed, accept decision)
  └── ACCEPT        → accepted
                         ↓  editor builds HTML (production/views.py :: build_html)
                       in_production
                         ↓  editor publishes (production/views.py :: publish_article)
                       published  ←─ HTMLBuild.is_published = True set here too
                         ↓  editor unpublishes (production/views.py :: unpublish_article)
                       in_production  ←─ HTMLBuild.is_published = False set here too
```

**Key rule:** `Submission.status == 'published'` and `HTMLBuild.is_published == True` must always match. The `publish_article` and `unpublish_article` views enforce this by setting both in the same request.

---

## State Transition Rules & Guards

### `record_decision()` — `apps/editorial/views.py`
- Can transition a submission to any status via the `status_map`.
- **Guard:** If a revision decision is issued on a `published` submission, the HTMLBuild is automatically unpublished first before the status changes. This prevents the article from remaining live while under revision.

### `send_invitations()` — `apps/reviewers/views.py`
- Sets status to `under_review` when reviewer invitations are sent.
- **Guard:** Does not overwrite `accepted`, `in_production`, or `published`. Reviewer invitations can be sent (for information) without disrupting a late-stage submission.

### `publish_article()` — `apps/production/views.py`
- Sets `HTMLBuild.is_published = True` and `HTMLBuild.published_at`.
- Sets `Submission.status = 'published'`.
- Both happen in the same view — they are always kept in sync.

### `unpublish_article()` — `apps/production/views.py`
- Sets `HTMLBuild.is_published = False`, clears `published_at`.
- Sets `Submission.status = 'in_production'`.

### `resubmit_step3()` — `apps/submissions/views.py`
- Only allowed when `Submission.status == 'revision_requested'`.
- Does not touch HTMLBuild.

---

## Issue Publication vs. Article Publication

Publishing an issue (`Issue.is_published = True`) makes the **issue index page** visible on the public site. It does not publish any individual articles.

Articles appear as **clickable links** on the issue page only when:
1. `Issue.is_published = True`, AND
2. `HTMLBuild.is_published = True` for that article.

Articles in an issue with `Submission.status = 'accepted'` or `'in_production'` may appear as non-linked entries on the issue page (depending on the public template), but are not readable until their HTML is published.

---

## Production Steps for a Single Article

1. **Accept** — editorial decision sets `status = accepted`
2. **Ingest** — editor clicks "Parse & Ingest Manuscript" → creates `CanonicalDocument` from `.tex`
3. **Build HTML** — `build_html` view renders HTML → creates/updates `HTMLBuild` (not yet live)
4. **Preview** — editor reviews at `/production/admin/preview/<doc_pk>/`
5. **Publish** — `publish_article` view → `HTMLBuild.is_published = True` + `status = published`
6. *(Optional)* **Generate PDF** — flat or interactive, via `admin_request_pdf`
7. *(Optional)* **Deposit DOI** — creates `DOIDeposit` record linked to `CanonicalDocument`

---

## Detecting Conflicts

A **state conflict** exists when `HTMLBuild.is_published = True` but `Submission.status != 'published'`. This should not occur in normal operation due to the guards above.

The Issue editor (`/admin/issues/<pk>/`) shows a `⚠ State conflict` indicator on any article in this condition, linking directly to the Editorial view for resolution.

To detect and fix conflicts from the shell:

```python
from apps.production.models import HTMLBuild
from apps.submissions.models import SubmissionStatus
from apps.editorial.models import DecisionType

REVISION_DECISIONS = {DecisionType.MINOR_REVISION, DecisionType.MAJOR_REVISION, DecisionType.REJECT_RESUBMIT}

for build in HTMLBuild.objects.filter(is_published=True):
    sub = build.document.revision.submission
    if sub.status == SubmissionStatus.PUBLISHED:
        continue
    # If the last editorial decision was a revision request, the article
    # should not be live — unpublish it and honour the revision state.
    last_decision = sub.editorial_decisions.order_by('-round').first()
    if last_decision and last_decision.decision_type in REVISION_DECISIONS:
        print(f'Unpublishing "{sub.title}" (last decision: {last_decision.decision_type})')
        build.is_published = False
        build.published_at = None
        build.save(update_fields=['is_published', 'published_at'])
        sub.status = SubmissionStatus.REVISION_REQUESTED
    else:
        print(f'Syncing "{sub.title}" status → published')
        sub.status = SubmissionStatus.PUBLISHED
    sub.save(update_fields=['status'])
```

---

## Where Each State is Shown in the UI

| Location | What is shown |
|---|---|
| Issue editor header | `Issue.is_published` — "Issue live since [date]" or "Publish Issue Page" button |
| Issue editor article row | `Submission.status` badge + HTML build indicator (live / built / no build / conflict) |
| Editorial submission detail — header | `Submission.status` badge |
| Editorial submission detail — Production section | `HTMLBuild.is_published` with publish/unpublish actions |
| Public issue page | Articles appear as links only if `HTMLBuild.is_published = True` |
