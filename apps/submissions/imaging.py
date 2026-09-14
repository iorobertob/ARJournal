"""Responsive image derivative generation (Pillow).

Given an uploaded image, produce a set of **downscale-only** WebP renditions at
role-appropriate widths, keep the original untouched, and record the intrinsic
dimensions. Used so the platform can serve/embed a correctly-sized image per
context (online srcset, print-capped PDF) instead of the full-resolution original
everywhere, and so small images (logos/icons) are never forced/upscaled.

Stakeholder recommended source sizes this maps onto:
  - Hero/full-width : 1920×1080 – 2500 px wide   (role "hero")
  - Content images  : ~1200 px wide              (role "content")
  - Logos/Icons     : ≤ 300×300 px               (role "logo" — no derivatives)

Design rules:
  - Never upscale: only widths strictly smaller than the source are generated.
  - Logos get no derivatives — they render at natural size.
  - Failures are swallowed and return an empty/partial result; callers must treat
    derivatives as best-effort and always keep the original `src` as a fallback.
"""
import io
import os

from PIL import Image, ImageOps

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

# Width ladders per role (px). Only widths < the source width are produced.
WIDTH_LADDERS = {
    'content': [400, 800, 1200, 1600],
    'hero': [800, 1280, 1920, 2500],
    'logo': [],
}
LOGO_MAX = 300           # ≤ this on the long edge ⇒ treated as a logo/icon
PRINT_CAP = 1600         # max width worth embedding into a PDF
WEBP_QUALITY = 82


def pad_to_aspect_ratio(uploaded_file, ratio_w, ratio_h, bg=(244, 242, 247), tol=0.01):
    """Letterbox/pillarbox an uploaded image onto a canvas of the target aspect
    ratio, **without cropping or stretching** — the whole image is kept at its
    original proportions and the extra space is filled with a solid background.

    ``uploaded_file`` is a Django UploadedFile / FieldFile. Returns a
    ``(filename, ContentFile)`` pair to assign to an ImageField, or ``None`` when
    the image already matches the ratio (within ``tol``) or can't be read as an
    image. Default ``bg`` is the design system's "ghost" (#F4F2F7), matching the
    CSS fallback behind issue covers.
    """
    try:
        uploaded_file.seek(0)
        img = ImageOps.exif_transpose(Image.open(uploaded_file))
        img.load()
    except Exception:
        return None
    finally:
        try:
            uploaded_file.seek(0)   # rewind so a caller can still save the original
        except Exception:
            pass

    iw, ih = img.size
    if iw <= 0 or ih <= 0:
        return None

    target = ratio_w / ratio_h
    current = iw / ih
    if abs(current - target) <= tol * target:
        return None  # already the expected ratio — leave it untouched

    # Flatten onto the opaque background (also resolves alpha/palette modes).
    if img.mode in ('RGBA', 'LA', 'P'):
        rgba = img.convert('RGBA')
        base = Image.new('RGBA', rgba.size, bg + (255,))
        base.alpha_composite(rgba)
        img = base.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Grow only the deficient dimension so nothing is scaled down or cropped.
    if current > target:                 # too wide → add top/bottom padding
        canvas_w, canvas_h = iw, round(iw / target)
    else:                                # too tall/narrow → add left/right padding
        canvas_w, canvas_h = round(ih * target), ih

    canvas = Image.new('RGB', (canvas_w, canvas_h), bg)
    canvas.paste(img, ((canvas_w - iw) // 2, (canvas_h - ih) // 2))

    buf = io.BytesIO()
    canvas.save(buf, 'JPEG', quality=90)
    stem = os.path.splitext(os.path.basename(getattr(uploaded_file, 'name', 'cover')))[0]
    return (f'{stem}.jpg', ContentFile(buf.getvalue()))


def detect_role(width, height, hint=None):
    """Resolve the image role. An explicit hint wins; otherwise infer from size."""
    if hint in ('content', 'hero', 'logo'):
        return hint
    if max(width, height) <= LOGO_MAX:
        return 'logo'
    return 'content'


def _derivative_name(original_name, width):
    """Path for a derivative, kept in a `derivatives/` subdir next to the original."""
    directory = os.path.dirname(original_name)
    stem = os.path.splitext(os.path.basename(original_name))[0]
    prefix = f'{directory}/derivatives' if directory else 'derivatives'
    return f'{prefix}/{stem}-{width}.webp'


def _load_image(image_field):
    """Read a Django FieldFile into a Pillow image (bytes-buffered for S3 safety)."""
    image_field.open('rb')
    try:
        data = image_field.read()
    finally:
        try:
            image_field.close()
        except Exception:
            pass
    img = Image.open(io.BytesIO(data))
    img.load()
    return ImageOps.exif_transpose(img)  # honour camera orientation


def generate_derivatives(image_field, role_hint=None):
    """Generate WebP derivatives for an image FieldFile.

    Returns a dict:
      {
        'role': 'content' | 'hero' | 'logo',
        'intrinsic_width': int, 'intrinsic_height': int,
        'derivatives': { '800': '/media/…-800.webp', … },   # keyed by width (str)
      }
    Returns {} if the file could not be read as an image.
    """
    if not image_field:
        return {}
    try:
        img = _load_image(image_field)
        iw, ih = img.size
    except Exception:
        return {}

    role = detect_role(iw, ih, role_hint)
    result = {'role': role, 'intrinsic_width': iw, 'intrinsic_height': ih, 'derivatives': {}}
    if role == 'logo':
        return result  # natural size — no derivatives needed

    # Normalise to a WebP-friendly mode, preserving alpha where present.
    if img.mode in ('P', 'LA'):
        img = img.convert('RGBA')
    elif img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')

    for width in WIDTH_LADDERS[role]:
        if width >= iw:
            continue  # never upscale
        height = max(1, round(ih * width / iw))
        try:
            resized = img.resize((width, height), Image.LANCZOS)
            buf = io.BytesIO()
            resized.save(buf, 'WEBP', quality=WEBP_QUALITY, method=6)
            name = _derivative_name(image_field.name, width)
            if default_storage.exists(name):
                default_storage.delete(name)  # overwrite stale derivative on re-upload
            saved = default_storage.save(name, ContentFile(buf.getvalue()))
            result['derivatives'][str(width)] = default_storage.url(saved)
        except Exception:
            continue  # skip this width; others may still succeed
    return result


def best_derivative_url(derivatives, max_width, original_url=''):
    """Pick the largest derivative not exceeding `max_width`.

    Falls back to the smallest available derivative, then to `original_url`.
    Used by the PDF exporter to embed a print-capped rendition.
    """
    if not derivatives:
        return original_url
    widths = sorted(int(w) for w in derivatives.keys())
    eligible = [w for w in widths if w <= max_width]
    chosen = eligible[-1] if eligible else widths[0]
    return derivatives.get(str(chosen), original_url)
