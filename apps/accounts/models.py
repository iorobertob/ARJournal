from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    """
    Custom manager for the email-based User model (no username field).
    Django's default UserManager.create_superuser() expects 'username' as a
    positional arg, which breaks when username=None on the model.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser must have is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class UserRole(models.TextChoices):
    AUTHOR = 'author', 'Author'
    REVIEWER = 'reviewer', 'Reviewer'
    EDITORIAL_ASSISTANT = 'editorial_assistant', 'Editorial Assistant'
    HANDLING_EDITOR = 'handling_editor', 'Handling Editor'
    ASSOCIATE_EDITOR = 'associate_editor', 'Associate Editor'
    GUEST_EDITOR = 'guest_editor', 'Guest Editor'
    EDITOR_IN_CHIEF = 'editor_in_chief', 'Editor-in-Chief'
    MANAGING_EDITOR = 'managing_editor', 'Managing Editor'
    COPYEDITOR = 'copyeditor', 'Copyeditor'
    PRODUCTION_EDITOR = 'production_editor', 'Production Editor'
    JOURNAL_ADMIN = 'journal_admin', 'Journal Administrator'
    SYSTEM_ADMIN = 'system_admin', 'System Administrator'


class User(AbstractUser):
    """Custom user model: email-based login, multi-role access, ORCID linking."""
    username = None
    email = models.EmailField(unique=True)
    roles = models.JSONField(default=list, blank=True)
    orcid_id = models.CharField(max_length=50, blank=True, default='')
    governance_access = models.BooleanField(
        default=False,
        help_text='Grants access to the Governance section (minutes, reports, planning) '
                  'to a user who is not an admin / senior editor — e.g. an editorial secretary.',
    )
    governance_blocked = models.BooleanField(
        default=False,
        help_text='Explicitly removes Governance access from a user who would otherwise '
                  'have it via their role (admin / senior editor). Overrides both the role '
                  'and an explicit grant; leaves all other roles and permissions untouched.',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        if self.first_name or self.last_name:
            return f'{self.first_name} {self.last_name}'.strip()
        return self.email

    def has_role(self, *role_values):
        """Return True if the user has any of the given roles."""
        return bool(set(self.roles or []) & set(role_values))

    @property
    def primary_role(self):
        """Return the most privileged role for display purposes."""
        priority = [
            UserRole.SYSTEM_ADMIN, UserRole.JOURNAL_ADMIN,
            UserRole.EDITOR_IN_CHIEF, UserRole.MANAGING_EDITOR,
            UserRole.ASSOCIATE_EDITOR, UserRole.HANDLING_EDITOR,
            UserRole.GUEST_EDITOR, UserRole.EDITORIAL_ASSISTANT,
            UserRole.PRODUCTION_EDITOR, UserRole.COPYEDITOR,
            UserRole.REVIEWER, UserRole.AUTHOR,
        ]
        for r in priority:
            if r in (self.roles or []):
                return r
        return UserRole.AUTHOR

    def get_roles_display(self):
        label = dict(UserRole.choices)
        return [label.get(r, r) for r in (self.roles or [])]

    def has_editorial_access(self):
        if self.is_superuser:
            return True
        editorial = {
            UserRole.EDITORIAL_ASSISTANT, UserRole.HANDLING_EDITOR,
            UserRole.ASSOCIATE_EDITOR, UserRole.GUEST_EDITOR,
            UserRole.EDITOR_IN_CHIEF, UserRole.MANAGING_EDITOR,
            UserRole.JOURNAL_ADMIN, UserRole.SYSTEM_ADMIN,
        }
        return bool(editorial & set(self.roles or []))

    def has_reviewer_access(self):
        return self.has_role(UserRole.REVIEWER) or self.has_editorial_access()

    def has_journal_admin_access(self):
        """Access to the Journal Admin dashboard — a stricter subset of editorial
        access. Mirrors the `journal_admin_required` decorator so navigation only
        links here for users who can actually enter."""
        return self.is_superuser or self.has_role(
            UserRole.JOURNAL_ADMIN, UserRole.SYSTEM_ADMIN,
            UserRole.EDITOR_IN_CHIEF, UserRole.MANAGING_EDITOR,
        )

    def has_governance_access(self):
        """Access to the Governance section: admins + senior editors (same gate as
        the journal admin dashboard), plus any user explicitly granted it — unless
        they have been explicitly blocked. A superuser can never be blocked out."""
        if self.governance_blocked and not self.is_superuser:
            return False
        return self.has_journal_admin_access() or bool(self.governance_access)

    def can_grant_governance_access(self):
        """Only admins / senior editors may grant, revoke, or block governance
        access for other users (a granted secretary cannot grant it onward)."""
        return self.has_journal_admin_access()

    def can_purge_content(self):
        """Prerogative to PERMANENTLY delete articles/records — an override of the
        journal's default 'never delete the scholarly record' policy, reserved for
        the super-admin (Django superuser or System Administrator) and the
        Editor-in-Chief. Every use is recorded in the immutable audit log."""
        return self.is_superuser or self.has_role(
            UserRole.SYSTEM_ADMIN, UserRole.EDITOR_IN_CHIEF,
        )


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, default='')
    institution = models.CharField(max_length=255, blank=True, default='')
    department = models.CharField(max_length=255, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    interests = models.JSONField(default=list, blank=True)
    website = models.URLField(blank=True, default='')
    public_profile = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile: {self.user.email}'


class PurgeExemption(models.Model):
    """A runtime allowlist entry protecting an email or whole domain from the
    unverified-account cleanup. Managed over the CLI via
    `python manage.py purge_allowlist add|remove|list`.

    `value` is stored normalized (lower-cased; a domain has no leading '@').
    """
    KIND_EMAIL = 'email'
    KIND_DOMAIN = 'domain'
    KIND_CHOICES = [(KIND_EMAIL, 'Email address'), (KIND_DOMAIN, 'Domain')]

    value = models.CharField(max_length=255, unique=True)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    note = models.CharField(max_length=255, blank=True, default='')
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purge_exemptions_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['kind', 'value']

    def __str__(self):
        return f'{self.get_kind_display()}: {self.value}'

    @staticmethod
    def normalize(raw):
        """Return (kind, value) for a raw CLI token. '@example.com' or a bare
        'example.com' (no local part) is a domain; anything with a local part is
        an email. Values are lower-cased."""
        v = (raw or '').strip().lower()
        if v.startswith('@'):
            return (PurgeExemption.KIND_DOMAIN, v[1:])
        if '@' in v:
            return (PurgeExemption.KIND_EMAIL, v)
        return (PurgeExemption.KIND_DOMAIN, v)
