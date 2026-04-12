from django.db import models


class JournalConfig(models.Model):
    """Singleton model — journal-wide configuration, editable from admin dashboard."""
    name = models.CharField(max_length=255, default='Trans/Act')
    tagline = models.CharField(max_length=500, blank=True, default='')
    description = models.TextField(blank=True, default='')
    issn_print = models.CharField(max_length=20, blank=True, default='')
    issn_online = models.CharField(max_length=20, blank=True, default='')
    contact_email = models.EmailField(blank=True, default='')
    editorial_email = models.EmailField(blank=True, default='')
    logo = models.ImageField(upload_to='journal/', blank=True, null=True)
    favicon = models.ImageField(upload_to='journal/', blank=True, null=True)
    review_model = models.CharField(
        max_length=30,
        choices=[
            ('double_blind', 'Double Blind'),
            ('single_blind', 'Single Blind'),
            ('open', 'Open Review'),
            ('editorial', 'Editorial Review'),
        ],
        default='double_blind',
    )
    submission_open = models.BooleanField(default=True)
    institution = models.CharField(max_length=255, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')
    publisher = models.CharField(max_length=255, blank=True, default='')
    imprint = models.TextField(blank=True, default='')
    instagram_url = models.URLField(blank=True, default='')
    footer_partners = models.TextField(blank=True, default='')
    submission_guidelines = models.TextField(blank=True, default='')
    about_text = models.TextField(blank=True, default='')
    mission_text = models.TextField(blank=True, default='')
    methodology_text = models.TextField(blank=True, default='')

    # ── Email ──────────────────────────────────────────────────
    email_from_name = models.CharField(max_length=255, blank=True, default='')
    email_from_address = models.EmailField(blank=True, default='')
    mailersend_api_token = models.CharField(max_length=500, blank=True, default='')

    # ── ORCID OAuth ────────────────────────────────────────────
    orcid_enabled = models.BooleanField(default=False)
    orcid_client_id = models.CharField(max_length=255, blank=True, default='')
    orcid_client_secret = models.CharField(max_length=255, blank=True, default='')

    # ── Crossref / DOI ─────────────────────────────────────────
    doi_enabled = models.BooleanField(default=False)
    doi_prefix = models.CharField(max_length=50, blank=True, default='', help_text='e.g. 10.12345')
    crossref_login = models.CharField(max_length=255, blank=True, default='')
    crossref_password = models.CharField(max_length=255, blank=True, default='')
    crossref_depositor_name = models.CharField(max_length=255, blank=True, default='')
    crossref_depositor_email = models.EmailField(blank=True, default='')

    # ── Turnitin ───────────────────────────────────────────────
    turnitin_enabled = models.BooleanField(default=False)
    turnitin_api_key = models.CharField(max_length=500, blank=True, default='')
    turnitin_base_url = models.CharField(max_length=255, blank=True, default='https://api.turnitin.com')

    # ── AI / OpenAI ────────────────────────────────────────────
    ai_features_enabled = models.BooleanField(default=False)
    openai_api_key = models.CharField(max_length=255, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Journal Configuration'
        verbose_name_plural = 'Journal Configuration'

    def __str__(self):
        return self.name

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class ArticleType(models.TextChoices):
    RESEARCH_ARTICLE = 'research_article', 'Research Article'
    CRITICAL_ESSAY = 'critical_essay', 'Critical Essay'
    REFLECTIVE_PAPER = 'reflective_paper', 'Reflective Paper'
    HYBRID_MEDIA = 'hybrid_media', 'Hybrid Media Contribution'
    EDITORIAL = 'editorial', 'Editorial'
    BOOK_REVIEW = 'book_review', 'Book Review'
    PRACTICE_DOCUMENTATION = 'practice_documentation', 'Practice Documentation'


class Issue(models.Model):
    number = models.PositiveIntegerField()
    volume = models.PositiveIntegerField(default=1)
    year = models.PositiveIntegerField()
    title = models.CharField(max_length=500, blank=True, default='')
    cover_image = models.ImageField(upload_to='issues/', blank=True, null=True)
    editorial_note = models.TextField(blank=True, default='')
    published_at = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    call_for_submissions = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-year', '-number']

    def __str__(self):
        return f'Issue #{self.number} ({self.year})'

    def save(self, *args, **kwargs):
        if self.is_current:
            Issue.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class Section(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='sections', null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.name}'


class EditorialBoardMember(models.Model):
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    institution = models.CharField(max_length=255, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    photo = models.ImageField(upload_to='board/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.name} — {self.role}'
