# Review Moderation and Editorial Mediation Specification

## Purpose
Ensure review integrity, professionalism, and clarity before author release.

## Review States
- submitted
- moderation_required
- moderated
- included_in_decision
- released_to_author

## Editorial Actions
Editors may:
- correct obvious typos
- remove abusive or discriminatory language
- redact confidential notes misplaced into author comments
- classify comments as major / minor / suggestion / question
- add editorial synthesis

Editors may not:
- change reviewer recommendation without explicit editorial layer separation
- rewrite substantive meaning of reviewer critique
- fabricate comments

## Conflict Detection
Flag when:
- recommendations diverge sharply
- score spread exceeds threshold
- review content contains contradictory claims

## AI Assistance
Allowed:
- tone analysis
- inconsistency highlighting
- draft synthesis suggestions
- missing-topic detection

Not allowed automatically:
- final decision
- autonomous review rewriting
- autonomous release to author

## Decision Letter Fields
- decision type
- editor summary
- priority issues
- conflict resolution note
- instructions to author
