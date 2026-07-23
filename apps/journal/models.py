import random

from django.db import models
from django.utils import timezone


class JournalConfig(models.Model):
    """Singleton model — journal-wide configuration, editable from admin dashboard."""
    name = models.CharField(max_length=255, default='inAct')
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
    footer_text = models.TextField(blank=True, default='')
    instagram_url = models.URLField(blank=True, default='')
    footer_partners = models.TextField(blank=True, default='')
    submission_guidelines = models.TextField(blank=True, default='')
    about_text = models.TextField(blank=True, default='')
    mission_text = models.TextField(blank=True, default='')
    methodology_text = models.TextField(blank=True, default='')
    news_text = models.TextField(blank=True, default='', help_text='Content of the public News page')

    # ── Homepage (admin-managed content) ───────────────────────
    home_hero_image = models.ImageField(
        upload_to='homepage/', blank=True, null=True,
        help_text='Large image shown top-right on the homepage (falls back to the current issue cover)')
    home_hero_caption = models.CharField(max_length=500, blank=True, default='')
    contribute_image = models.ImageField(
        upload_to='homepage/', blank=True, null=True,
        help_text='Image shown in the "Contribute" section of the homepage')
    contribute_caption = models.CharField(max_length=500, blank=True, default='')
    contribute_text = models.TextField(
        blank=True, default='',
        help_text='Text of the "Contribute" section on the homepage')
    featured_rotation_months = models.PositiveSmallIntegerField(
        default=6,
        help_text='How long a homepage "Across the archive" selection stays before rotating (months)')

    # ── Homepage section visibility ────────────────────────────
    show_filtered_section = models.BooleanField(
        default=True, help_text='Show the keyword/year filtered articles section on the homepage')
    show_archive_section = models.BooleanField(
        default=True, help_text='Show the "Across the archive" section on the homepage')
    show_contribute_section = models.BooleanField(
        default=True, help_text='Show the "Contribute" section on the homepage')

    # ── Email ──────────────────────────────────────────────────
    email_from_name = models.CharField(max_length=255, blank=True, default='')
    email_from_address = models.EmailField(blank=True, default='')

    EMAIL_BACKEND_MAILERSEND = 'mailersend'
    EMAIL_BACKEND_SMTP = 'smtp'
    EMAIL_BACKEND_CHOICES = [
        (EMAIL_BACKEND_MAILERSEND, 'MailerSend (API)'),
        (EMAIL_BACKEND_SMTP, 'SMTP'),
    ]
    email_backend_type = models.CharField(
        max_length=20,
        choices=EMAIL_BACKEND_CHOICES,
        default=EMAIL_BACKEND_MAILERSEND,
    )

    # MailerSend
    mailersend_api_token = models.CharField(max_length=500, blank=True, default='')

    # SMTP
    smtp_host = models.CharField(max_length=255, blank=True, default='')
    smtp_port = models.PositiveSmallIntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True, default='')
    smtp_password = models.CharField(max_length=500, blank=True, default='')
    smtp_use_tls = models.BooleanField(default=True)

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

    # ── Legal ──────────────────────────────────────────────────
    legal_notice = models.TextField(
        blank=True, default='',
        help_text='Optional jurisdiction-specific text appended to the Terms & Conditions page (DPO contact, supervisory authority, etc.)',
    )

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


class FeaturedSelection(models.Model):
    """One period of featured articles for the homepage "Across the archive" section.

    Editors pick articles manually for a period; when it expires, random
    published articles are selected automatically for another period of the
    same (configurable) length, repeating until a new manual selection is made.
    """
    KIND_MANUAL = 'manual'
    KIND_AUTO = 'auto'
    kind = models.CharField(
        max_length=10,
        choices=[(KIND_MANUAL, 'Manual'), (KIND_AUTO, 'Automatic')],
        default=KIND_AUTO,
    )
    articles = models.ManyToManyField('production.HTMLBuild', blank=True, related_name='featured_in')
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    NUM_FEATURED = 4

    class Meta:
        ordering = ['-starts_at']

    def __str__(self):
        return f'{self.get_kind_display()} selection {self.starts_at:%Y-%m-%d} → {self.ends_at:%Y-%m-%d}'

    @property
    def is_active(self):
        now = timezone.now()
        return self.starts_at <= now < self.ends_at

    @classmethod
    def _period_end(cls, start):
        months = JournalConfig.get().featured_rotation_months or 6
        # add N months without external deps
        month = start.month - 1 + months
        year = start.year + month // 12
        month = month % 12 + 1
        import calendar
        day = min(start.day, calendar.monthrange(year, month)[1])
        return start.replace(year=year, month=month, day=day)

    @classmethod
    def start_manual(cls, builds):
        """Replace the current selection with a manual one starting now."""
        now = timezone.now()
        cls.objects.filter(ends_at__gt=now).update(ends_at=now)
        sel = cls.objects.create(kind=cls.KIND_MANUAL, starts_at=now, ends_at=cls._period_end(now))
        sel.articles.set(builds)
        return sel

    @classmethod
    def current(cls):
        """Return the active selection, rotating in a random one if expired."""
        from apps.production.models import HTMLBuild
        now = timezone.now()
        sel = cls.objects.filter(starts_at__lte=now, ends_at__gt=now).first()
        if sel:
            return sel
        published = list(HTMLBuild.objects.filter(is_published=True).values_list('pk', flat=True))
        if not published:
            return None
        picks = random.sample(published, min(cls.NUM_FEATURED, len(published)))
        sel = cls.objects.create(kind=cls.KIND_AUTO, starts_at=now, ends_at=cls._period_end(now))
        sel.articles.set(picks)
        return sel


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


class NewsPost(models.Model):
    """A blog-style news / announcement post, authored by editors and admins
    via the Journal Admin dashboard and shown on the public /news/ page as
    chronologically ordered rich row cards."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    summary = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Short teaser shown on the news card. Falls back to the start of the body.',
    )
    body = models.TextField(
        blank=True, default='',
        help_text='WYSIWYG rich-text content (sanitized on save).',
    )
    thumbnail = models.ImageField(upload_to='news/', blank=True, null=True)
    author = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='news_posts',
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Set automatically when first published; drives chronological order.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Newest first; drafts (no published_at) fall back to creation time.
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        # Stamp the publish time the first time it goes live.
        if self.is_published and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        from django.utils.text import slugify
        base = slugify(self.title) or 'post'
        slug = base
        n = 2
        qs = NewsPost.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(slug=slug).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug

    @property
    def display_date(self):
        return self.published_at or self.created_at

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('news_detail', args=[self.slug])
