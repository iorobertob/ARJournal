"""
Management command to create dummy data for development:
- 3 Reviewers with ReviewerProfiles
- 1 Author with a submission under review
- 1 pending review for the editor-in-chief to process
"""
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create dummy data: 3 reviewers, 1 author, 1 submission with pending review'

    def handle(self, *args, **options):
        from apps.accounts.models import User, UserRole, UserProfile
        from apps.journal.models import JournalConfig, Issue, Section
        from apps.submissions.models import Submission, SubmissionStatus, SubmissionRevision
        from apps.reviewers.models import ReviewerProfile, ReviewerInvitation, InvitationStatus
        from apps.reviews.models import Review, ReviewStatus, Recommendation
        from apps.editorial.models import EditorialAssignment

        # Ensure JournalConfig exists
        journal = JournalConfig.get()
        if not journal.name or journal.name == 'Trans/Act':
            journal.name = 'Trans/Act'
            journal.tagline = 'A Journal for Artistic Research'
            journal.description = (
                'Trans/Act publishes critical essays, visual projects, multimedia research, '
                'and experimental contributions across artistic research practices.'
            )
            journal.contact_email = 'editorial@trans-act-journal.org'
            journal.editorial_email = 'editorial@trans-act-journal.org'
            journal.institution = 'Lithuanian Academy of Music and Theatre'
            journal.country = 'Lithuania'
            journal.about_text = (
                'Trans/Act is a peer-reviewed, open-access journal dedicated to artistic research. '
                'We publish twice yearly, featuring essays, visual projects, multimedia research, '
                'and experimental contributions that explore how knowledge can be made public '
                'through artistic practice.\n\n'
                'The journal welcomes contributions from artists, writers, and researchers '
                'working across critical, visual, and practice-based forms of artistic research.'
            )
            journal.mission_text = (
                'Our mission is to advance the discourse of artistic research by providing a '
                'rigorous yet open platform for experimental forms of knowledge production. '
                'We believe that artistic practice generates unique insights that complement '
                'and challenge traditional academic inquiry.'
            )
            journal.submission_guidelines = (
                'Trans/Act accepts submissions in the following categories:\n\n'
                '- Research Articles (4,000-8,000 words)\n'
                '- Critical Essays (3,000-6,000 words)\n'
                '- Reflective Papers (2,000-5,000 words)\n'
                '- Hybrid Media Contributions\n'
                '- Practice Documentation\n\n'
                'All submissions must be prepared using the Trans/Act LaTeX template. '
                'Manuscripts are evaluated through double-blind peer review.'
            )
            journal.save()
            self.stdout.write(self.style.SUCCESS('Updated JournalConfig.'))

        # ── Editor-in-Chief ──────────────────────────────────────
        editor, created = User.objects.get_or_create(
            email='editor@trans-act-journal.org',
            defaults={
                'first_name': 'Elena',
                'last_name': 'Voronova',
                'role': UserRole.EDITOR_IN_CHIEF,
                'is_staff': True,
            }
        )
        if created:
            editor.set_password('devpassword')
            editor.save()
            UserProfile.objects.get_or_create(
                user=editor,
                defaults={
                    'institution': 'Lithuanian Academy of Music and Theatre',
                    'department': 'Department of Artistic Research',
                    'country': 'Lithuania',
                    'bio': 'Editor-in-Chief of Trans/Act. Research interests: performance studies, embodied knowledge, artistic methodology.',
                }
            )
            self.stdout.write(self.style.SUCCESS(f'Created editor: {editor.email}'))

        # ── 3 Reviewers ─────────────────────────────────────────
        reviewers_data = [
            {
                'email': 'reviewer1@university.edu',
                'first_name': 'Dr. Marcus',
                'last_name': 'Feldmann',
                'profile': {
                    'institution': 'Universitat der Kunste Berlin',
                    'department': 'Institute for Art in Context',
                    'country': 'Germany',
                    'bio': 'Research focuses on the intersection of visual arts and critical theory, with particular emphasis on post-conceptual practices.',
                },
                'reviewer_profile': {
                    'expertise_keywords': ['visual arts', 'critical theory', 'post-conceptualism', 'installation art', 'contemporary aesthetics'],
                    'disciplines': ['Fine Arts', 'Art Theory', 'Cultural Studies'],
                    'methodologies': ['practice-based research', 'phenomenological analysis', 'visual ethnography'],
                    'artistic_mediums': ['installation', 'video', 'photography'],
                    'languages': ['en', 'de'],
                    'expertise_statement': 'I specialize in practice-based research methodologies within visual arts, with 15 years of experience reviewing for international art research journals.',
                    'quality_score': 0.92,
                    'responsiveness_score': 0.85,
                    'total_reviews_completed': 12,
                },
            },
            {
                'email': 'reviewer2@arts.ac.uk',
                'first_name': 'Prof. Amara',
                'last_name': 'Osei',
                'profile': {
                    'institution': 'Royal College of Art',
                    'department': 'School of Arts & Humanities',
                    'country': 'United Kingdom',
                    'bio': 'Sound artist and researcher exploring the politics of listening, acoustic ecologies, and decolonial sound practices.',
                },
                'reviewer_profile': {
                    'expertise_keywords': ['sound art', 'acoustic ecology', 'decolonial practice', 'performance', 'listening'],
                    'disciplines': ['Sound Studies', 'Performance Studies', 'Postcolonial Theory'],
                    'methodologies': ['artistic research', 'autoethnography', 'sonic mapping'],
                    'artistic_mediums': ['sound', 'performance', 'multimedia'],
                    'languages': ['en', 'fr'],
                    'expertise_statement': 'My reviewing practice is grounded in sound studies and performance research. I bring particular attention to methodological rigour in practice-based submissions.',
                    'quality_score': 0.88,
                    'responsiveness_score': 0.90,
                    'total_reviews_completed': 8,
                },
            },
            {
                'email': 'reviewer3@aalto.fi',
                'first_name': 'Dr. Kai',
                'last_name': 'Nieminen',
                'profile': {
                    'institution': 'Aalto University',
                    'department': 'Department of Art',
                    'country': 'Finland',
                    'bio': 'Researches embodied cognition in dance and choreographic practices, bridging neuroscience and artistic research.',
                },
                'reviewer_profile': {
                    'expertise_keywords': ['dance', 'choreography', 'embodied cognition', 'somatics', 'movement analysis'],
                    'disciplines': ['Dance Studies', 'Cognitive Science', 'Artistic Research'],
                    'methodologies': ['embodied research', 'practice-as-research', 'mixed methods'],
                    'artistic_mediums': ['dance', 'video', 'writing'],
                    'languages': ['en', 'fi', 'sv'],
                    'expertise_statement': 'I review at the intersection of cognitive science and choreographic research, focusing on how bodily knowledge translates into written academic discourse.',
                    'quality_score': 0.85,
                    'responsiveness_score': 0.78,
                    'total_reviews_completed': 5,
                },
            },
        ]

        reviewer_users = []
        for rdata in reviewers_data:
            user, created = User.objects.get_or_create(
                email=rdata['email'],
                defaults={
                    'first_name': rdata['first_name'],
                    'last_name': rdata['last_name'],
                    'role': UserRole.REVIEWER,
                }
            )
            if created:
                user.set_password('devpassword')
                user.save()
                UserProfile.objects.get_or_create(user=user, defaults=rdata['profile'])
                ReviewerProfile.objects.get_or_create(user=user, defaults=rdata['reviewer_profile'])
                self.stdout.write(self.style.SUCCESS(f'Created reviewer: {user.email}'))
            reviewer_users.append(user)

        # ── Author with Submission ───────────────────────────────
        author, created = User.objects.get_or_create(
            email='author@researcher.org',
            defaults={
                'first_name': 'Sofia',
                'last_name': 'Bergstrom',
                'role': UserRole.AUTHOR,
            }
        )
        if created:
            author.set_password('devpassword')
            author.save()
            UserProfile.objects.get_or_create(
                user=author,
                defaults={
                    'institution': 'Stockholm University of the Arts',
                    'department': 'Department of Performing Arts',
                    'country': 'Sweden',
                    'bio': 'Choreographer and researcher working on the relationship between movement, memory, and spatial narrative.',
                    'interests': ['choreography', 'spatial narrative', 'embodied memory', 'site-specific art'],
                }
            )
            self.stdout.write(self.style.SUCCESS(f'Created author: {author.email}'))

        # Create an Issue (draft) for context
        issue, _ = Issue.objects.get_or_create(
            number=1,
            defaults={
                'volume': 1,
                'year': 2026,
                'title': 'Bodies in Practice: Embodied Knowledge and Artistic Research',
                'editorial_note': (
                    'This inaugural issue of Trans/Act explores how embodied knowledge '
                    'emerges through artistic practice. The contributions gathered here '
                    'examine the body as a site of research, investigating how physical '
                    'experience generates insights that resist conventional academic framing.'
                ),
                'is_current': True,
            }
        )

        # Create submission
        submission, created = Submission.objects.get_or_create(
            author=author,
            title='Choreographic Scores as Research Instruments: Mapping Embodied Knowledge Through Movement Notation',
            defaults={
                'subtitle': 'A Practice-Based Investigation into Dance Documentation',
                'article_type': 'research_article',
                'abstract': (
                    'This article investigates the potential of choreographic scores as instruments '
                    'of artistic research. Drawing on a two-year practice-based study, the author '
                    'develops a framework for understanding how movement notation systems can capture '
                    'and transmit embodied knowledge that resists verbal articulation. Through an '
                    'analysis of three original choreographic works, the study demonstrates how scores '
                    'function not merely as documentation but as generative research tools that reveal '
                    'hidden dimensions of corporeal experience. The findings suggest that choreographic '
                    'notation, when reconceived as a research methodology, opens new pathways for '
                    'understanding the relationship between bodily practice and knowledge production '
                    'in artistic research.'
                ),
                'keywords': ['choreographic score', 'embodied knowledge', 'movement notation', 'practice-based research', 'dance documentation'],
                'disciplines': ['Dance Studies', 'Artistic Research', 'Performance Studies'],
                'artistic_mediums': ['dance', 'notation', 'video'],
                'status': SubmissionStatus.UNDER_REVIEW,
                'submission_date': timezone.now() - datetime.timedelta(days=14),
                'cover_letter': (
                    'Dear Editors,\n\n'
                    'I am pleased to submit this article for consideration in Trans/Act. '
                    'This work emerges from my ongoing research into choreographic documentation '
                    'at Stockholm University of the Arts. I believe it aligns well with the '
                    'journal\'s focus on practice-based artistic research.\n\n'
                    'Best regards,\nSofia Bergstrom'
                ),
                'originality_confirmed': True,
                'issue': issue,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created submission: {submission.title[:50]}...'))

        # Create editorial assignment
        EditorialAssignment.objects.get_or_create(
            submission=submission,
            editor=editor,
            defaults={'role': 'editor_in_chief'}
        )

        # Create invitation for reviewer 1 (accepted, review submitted for moderation)
        inv1, created = ReviewerInvitation.objects.get_or_create(
            submission=submission,
            reviewer=reviewer_users[0],
            defaults={
                'deadline': (timezone.now() + datetime.timedelta(days=7)).date(),
                'status': InvitationStatus.ACCEPTED,
            }
        )
        if created:
            Review.objects.create(
                invitation=inv1,
                status=ReviewStatus.SUBMITTED,
                recommendation=Recommendation.MINOR_REVISION,
                scores={'originality': 8, 'methodology': 7, 'clarity': 8, 'significance': 7, 'references': 8},
                expertise_self_rating=4,
                summary=(
                    'This is a thoughtful and methodologically rigorous contribution that '
                    'advances our understanding of choreographic scores as research instruments. '
                    'The three case studies are compelling and well-documented.'
                ),
                strengths=(
                    '- Original framework for understanding scores as research tools\n'
                    '- Excellent integration of practice and theory\n'
                    '- Clear articulation of the embodied knowledge concept\n'
                    '- Rich documentation of the choreographic works'
                ),
                major_issues=(
                    '- The theoretical framing in section 2 could engage more deeply with '
                    'existing movement analysis literature (Laban, Forsythe)\n'
                    '- The third case study feels underdeveloped compared to the first two'
                ),
                minor_issues=(
                    '- Some terminological inconsistency between "score" and "notation"\n'
                    '- Figure 3 caption needs clarification\n'
                    '- A few citations are incomplete (see specific notes)'
                ),
                comments_to_author=(
                    'This is a strong submission that makes a genuine contribution to the field. '
                    'I recommend minor revisions, primarily to strengthen the theoretical engagement '
                    'in section 2 and to develop the third case study more fully. The core argument '
                    'is convincing and well-supported by the practice-based evidence.'
                ),
                comments_to_editor=(
                    'A solid piece of artistic research writing. The author demonstrates genuine '
                    'expertise in both the practice and its theoretical framing. With the suggested '
                    'revisions, this will be a valuable addition to the journal.'
                ),
                submitted_at=timezone.now() - datetime.timedelta(days=2),
            )
            self.stdout.write(self.style.SUCCESS('Created submitted review from reviewer 1.'))

        # Create invitation for reviewer 2 (accepted, review in draft — still working)
        inv2, created = ReviewerInvitation.objects.get_or_create(
            submission=submission,
            reviewer=reviewer_users[1],
            defaults={
                'deadline': (timezone.now() + datetime.timedelta(days=10)).date(),
                'status': InvitationStatus.ACCEPTED,
            }
        )
        if created:
            Review.objects.create(
                invitation=inv2,
                status=ReviewStatus.DRAFT,
                recommendation='',
                scores={},
                summary='Interesting approach to...',
                draft_saved_at=timezone.now() - datetime.timedelta(hours=6),
            )
            self.stdout.write(self.style.SUCCESS('Created draft review from reviewer 2.'))

        # Reviewer 3 invitation pending
        ReviewerInvitation.objects.get_or_create(
            submission=submission,
            reviewer=reviewer_users[2],
            defaults={
                'deadline': (timezone.now() + datetime.timedelta(days=14)).date(),
                'status': InvitationStatus.PENDING,
            }
        )
        self.stdout.write(self.style.SUCCESS('Created pending invitation for reviewer 3.'))

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Dummy data created successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write('Login credentials (all passwords: devpassword):')
        self.stdout.write(f'  Editor-in-Chief:  editor@trans-act-journal.org')
        self.stdout.write(f'  Author:           author@researcher.org')
        self.stdout.write(f'  Reviewer 1:       reviewer1@university.edu')
        self.stdout.write(f'  Reviewer 2:       reviewer2@arts.ac.uk')
        self.stdout.write(f'  Reviewer 3:       reviewer3@aalto.fi')
        self.stdout.write('')
        self.stdout.write('Submission: "Choreographic Scores as Research Instruments..."')
        self.stdout.write('  Status: Under Review')
        self.stdout.write('  Review 1: Submitted (Minor Revision) — needs editor moderation')
        self.stdout.write('  Review 2: Draft (reviewer still working)')
        self.stdout.write('  Review 3: Invitation pending')
        self.stdout.write('')
