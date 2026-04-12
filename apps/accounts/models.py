from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    AUTHOR = 'author', 'Author'
    REVIEWER = 'reviewer', 'Reviewer'
    EDITORIAL_ASSISTANT = 'editorial_assistant', 'Editorial Assistant'
    HANDLING_EDITOR = 'handling_editor', 'Handling Editor'
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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

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
            UserRole.HANDLING_EDITOR, UserRole.EDITORIAL_ASSISTANT,
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
        editorial = {
            UserRole.EDITORIAL_ASSISTANT, UserRole.HANDLING_EDITOR,
            UserRole.EDITOR_IN_CHIEF, UserRole.MANAGING_EDITOR,
            UserRole.JOURNAL_ADMIN, UserRole.SYSTEM_ADMIN,
        }
        return bool(editorial & set(self.roles or []))

    def has_reviewer_access(self):
        return self.has_role(UserRole.REVIEWER) or self.has_editorial_access()


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile: {self.user.email}'
