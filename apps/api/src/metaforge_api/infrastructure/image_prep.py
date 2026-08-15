"""Server-side mirror of apps/web/src/lib/imagePrep.ts, for entry points
that don't have a browser to preprocess in before the image reaches this
backend — currently just Telegram (infrastructure/telegram_handler.py).
The web client already does this in-browser via Canvas; this module
exists so a Telegram-submitted photo gets the identical treatment rather
than the two entry points silently diverging in cost/extraction quality.

Grayscale, not binarized: vision LLMs are trained on natural photographs,
and hard thresholding (Otsu / fixed cutoff) destroys anti-aliased glyph
edges, kills faint thermal-receipt print, and turns uneven lighting into
solid black blobs — a pre-modern OCR trick that measurably hurts a vision
model's ability to read the image. Grayscale still satisfies "smaller and
higher-contrast": dropping chroma alone compresses a photo ~30-40%
smaller than color at the same JPEG quality, and a mild contrast stretch
recovers dim/washed-out photos without the destructive step.

Constants and algorithm are kept in lockstep with imagePrep.ts — if you
change one, change both.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps

MAX_EDGE_PX = 1568
JPEG_QUALITY = 82
STRETCH_LOW_PERCENTILE = 0.02
STRETCH_HIGH_PERCENTILE = 0.98
SKIP_STRETCH_IF_RANGE_AT_LEAST = 200
MAX_INPUT_BYTES = 25 * 1024 * 1024


class ImagePrepError(Exception):
    pass


@dataclass
class PreprocessedImage:
    data: bytes
    mime_type: str  # always "image/jpeg"
    width: int
    height: int


def preprocess_receipt_image(raw_bytes: bytes) -> PreprocessedImage:
    if len(raw_bytes) > MAX_INPUT_BYTES:
        raise ImagePrepError("That photo is too large — try a lower-resolution shot.")

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.load()
    except Exception as exc:  # Pillow raises several distinct error types for bad input
        raise ImagePrepError("Couldn't read that image — try a different photo.") from exc

    # Server equivalent of createImageBitmap's imageOrientation: 'from-image'
    # — applies the EXIF orientation tag then strips it, so downstream code
    # never has to think about it again.
    img = ImageOps.exif_transpose(img)

    scale = min(1.0, MAX_EDGE_PX / max(img.width, img.height))
    width = max(1, round(img.width * scale))
    height = max(1, round(img.height * scale))
    if scale < 1.0:
        img = img.resize((width, height), Image.LANCZOS)

    # Pillow's "L" mode conversion IS Rec. 601 luma
    # (R*299/1000 + G*587/1000 + B*114/1000) — matches imagePrep.ts exactly.
    gray = img.convert("L")

    histogram = gray.histogram()
    pixel_count = width * height
    low_cut = pixel_count * STRETCH_LOW_PERCENTILE
    high_cut = pixel_count * STRETCH_HIGH_PERCENTILE

    cumulative = 0
    p2 = 0
    for level in range(256):
        cumulative += histogram[level]
        if cumulative >= low_cut:
            p2 = level
            break

    cumulative = 0
    p98 = 255
    for level in range(255, -1, -1):
        cumulative += histogram[level]
        if cumulative >= pixel_count - high_cut:
            p98 = level
            break

    value_range = p98 - p2
    if 0 < value_range < SKIP_STRETCH_IF_RANGE_AT_LEAST:
        stretch_scale = 255 / value_range
        gray = gray.point(lambda y: max(0, min(255, round((y - p2) * stretch_scale))))

    out = gray.convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return PreprocessedImage(data=buf.getvalue(), mime_type="image/jpeg", width=width, height=height)
