"""Hardened account forms — anti-abuse controls layered on allauth's signup.

Defence in depth against bot/spam registrations:
  1. Honeypot field — a form field hidden from real users (via CSS in the
     template); only bots fill it, and any value fails the submission silently.
  2. Disposable-email block — reject known throwaway email providers.
  3. Cloudflare Turnstile — server-side CAPTCHA verification. Skipped when no
     secret key is configured (local dev / tests), so it never blocks those.

Rate limiting is handled separately by allauth (settings.ACCOUNT_RATE_LIMITS),
and email verification remains mandatory (settings.ACCOUNT_EMAIL_VERIFICATION).
"""
import json
import urllib.parse
import urllib.request

from django import forms
from django.conf import settings
from allauth.account.forms import SignupForm as AllauthSignupForm


# Small, extensible blocklist of disposable / throwaway email domains.
DISPOSABLE_EMAIL_DOMAINS = {
    'mailinator.com', 'guerrillamail.com', 'guerrillamail.info', 'sharklasers.com',
    '10minutemail.com', '10minutemail.net', 'tempmail.com', 'temp-mail.org',
    'yopmail.com', 'getnada.com', 'trashmail.com', 'dispostable.com', 'maildrop.cc',
    'mailnesia.com', 'fakeinbox.com', 'throwawaymail.com', 'mohmal.com',
    'emailondeck.com', 'spam4.me', 'mailcatch.com', 'tempmailo.com', 'tempr.email',
    'moakt.com', 'inboxkitten.com', 'mintemail.com', 'discard.email', 'burnermail.io',
}

TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def verify_turnstile(token, remoteip=None):
    """Return True if the Turnstile token is valid, or if Turnstile is not
    configured (no secret key). Fails closed on verification errors."""
    secret = getattr(settings, 'TURNSTILE_SECRET_KEY', '')
    if not secret:
        return True  # not configured → skip (dev / tests)
    if not token:
        return False
    payload = {'secret': secret, 'response': token}
    if remoteip:
        payload['remoteip'] = remoteip
    try:
        req = urllib.request.Request(
            TURNSTILE_VERIFY_URL,
            data=urllib.parse.urlencode(payload).encode(),
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
        return bool(result.get('success'))
    except Exception:
        return False  # fail closed


class SignupForm(AllauthSignupForm):
    """allauth signup form hardened with honeypot, disposable-email block and
    Cloudflare Turnstile verification."""

    def clean_email(self):
        email = super().clean_email()
        domain = email.rsplit('@', 1)[-1].lower() if '@' in email else ''
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            raise forms.ValidationError(
                'Please use a permanent email address — disposable email '
                'providers are not accepted.'
            )
        return email

    def clean(self):
        cleaned = super().clean()

        # 1. Honeypot — read straight from POST (name="website" in the template).
        if (self.data.get('website') or '').strip():
            # Generic message; never reveal that this is a honeypot.
            raise forms.ValidationError('Your registration could not be completed.')

        # 2. Cloudflare Turnstile.
        token = self.data.get('cf-turnstile-response', '')
        remoteip = None
        request = getattr(self, 'request', None)
        if request is not None:
            remoteip = (request.META.get('HTTP_CF_CONNECTING_IP')
                        or request.META.get('REMOTE_ADDR'))
        if not verify_turnstile(token, remoteip):
            raise forms.ValidationError(
                'Human-verification check failed. Please complete the challenge and try again.'
            )

        return cleaned
