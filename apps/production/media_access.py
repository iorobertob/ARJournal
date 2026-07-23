"""Signed, short-lived access tokens for protected media (HLS + originals).

Video and audio are never exposed as a directly downloadable file. Instead the
streaming view (apps/production/views.py :: stream_media) hands out URLs carrying
an HMAC token bound to the exact media path and an expiry. A copied URL stops
working after `MEDIA_SIGNED_URL_TTL` seconds and cannot be reused for another
path. This is a deterrent against casual downloading/hotlinking — combined with
`controlsList=nodownload` and HLS segmentation — not DRM.
"""
import base64
import hashlib
import hmac
import time

from django.conf import settings
from django.urls import reverse


def _key() -> bytes:
    return (getattr(settings, 'MEDIA_SIGNING_KEY', '') or settings.SECRET_KEY).encode()


def _token(media_path: str, exp: int) -> str:
    msg = f'{media_path}:{exp}'.encode()
    sig = hmac.new(_key(), msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip('=')


def sign(media_path: str, ttl: int | None = None) -> tuple[int, str]:
    """Return (exp, token) for a MEDIA_ROOT-relative path."""
    ttl = int(ttl if ttl is not None else getattr(settings, 'MEDIA_SIGNED_URL_TTL', 10800))
    exp = int(time.time()) + ttl
    return exp, _token(media_path, exp)


def verify(media_path: str, exp, token: str) -> bool:
    """Constant-time verify a token for a path; False if expired/invalid."""
    try:
        exp = int(exp)
    except (TypeError, ValueError):
        return False
    if exp < int(time.time()):
        return False
    return hmac.compare_digest(_token(media_path, exp), token or '')


def signed_stream_url(media_path: str, ttl: int | None = None) -> str:
    """Full URL to stream a MEDIA_ROOT-relative path through the protected view."""
    media_path = media_path.lstrip('/')
    exp, token = sign(media_path, ttl)
    base = reverse('stream_media', kwargs={'media_path': media_path})
    return f'{base}?exp={exp}&t={token}'
