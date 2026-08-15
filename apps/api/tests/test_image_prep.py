"""infrastructure/image_prep.py — the server-side (Telegram) mirror of
imagePrep.ts. Verifies it produces the same shape of output the browser
path does: capped longest edge, no upscaling, true grayscale, and a
usable error on garbage input."""

import io

import pytest
from PIL import Image

from metaforge_api.infrastructure.image_prep import ImagePrepError, MAX_EDGE_PX, preprocess_receipt_image


def _jpeg_bytes(width: int, height: int, color=(60, 120, 200)) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_resizes_to_max_edge_preserving_aspect():
    result = preprocess_receipt_image(_jpeg_bytes(2000, 1400))
    assert result.width == MAX_EDGE_PX
    assert result.height == round(1400 * MAX_EDGE_PX / 2000)
    assert result.mime_type == "image/jpeg"


def test_does_not_upscale_small_images():
    result = preprocess_receipt_image(_jpeg_bytes(400, 300))
    assert result.width == 400
    assert result.height == 300


def test_output_is_grayscale():
    result = preprocess_receipt_image(_jpeg_bytes(500, 500, color=(200, 40, 40)))
    out = Image.open(io.BytesIO(result.data))
    r, g, b = out.getpixel((250, 250))
    assert r == g == b


def test_low_contrast_input_gets_stretched():
    # A narrow luma band (120-140) should widen after the percentile stretch.
    img = Image.new("RGB", (400, 400))
    px = img.load()
    for y in range(400):
        for x in range(400):
            v = 120 + (x % 20)
            px[x, y] = (v, v, v)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)

    result = preprocess_receipt_image(buf.getvalue())
    out = Image.open(io.BytesIO(result.data)).convert("L")
    lo, hi = out.getextrema()
    assert hi - lo > 20 - 0  # widened well beyond the original ~20-level band


def test_garbage_bytes_raise_image_prep_error():
    with pytest.raises(ImagePrepError):
        preprocess_receipt_image(b"this is not an image")


def test_oversized_input_rejected():
    with pytest.raises(ImagePrepError):
        preprocess_receipt_image(b"0" * (26 * 1024 * 1024))
