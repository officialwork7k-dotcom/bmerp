/**
 * Client-side preprocessing for AI-assistant document scans: grayscale
 * (not hard-thresholded black-and-white — see below) plus a longest-edge
 * resize, before the image ever leaves the browser.
 *
 * Grayscale, not binarized: vision LLMs are trained on natural photographs,
 * and hard thresholding (Otsu / fixed cutoff) destroys anti-aliased glyph
 * edges, kills faint thermal-receipt print, and turns uneven lighting into
 * solid black blobs — a pre-modern OCR trick that measurably hurts a vision
 * model's ability to read the image. Grayscale still satisfies "smaller and
 * higher-contrast": dropping chroma alone compresses a photo ~30-40%
 * smaller than color at the same JPEG quality, and a mild contrast stretch
 * recovers dim/washed-out photos without the destructive step.
 */

const MAX_EDGE_PX = 1568;
const JPEG_QUALITY = 0.82;
const STRETCH_LOW_PERCENTILE = 0.02;
const STRETCH_HIGH_PERCENTILE = 0.98;
const SKIP_STRETCH_IF_RANGE_AT_LEAST = 200;
const MAX_INPUT_BYTES = 25 * 1024 * 1024;

export interface PreprocessedImage {
	dataUrl: string;
	base64: string;
	mimeType: 'image/jpeg';
	width: number;
	height: number;
}

export class ImagePrepError extends Error {}

export async function preprocessReceiptImage(file: File): Promise<PreprocessedImage> {
	if (file.size > MAX_INPUT_BYTES) {
		throw new ImagePrepError("That photo is too large — try a lower-resolution shot.");
	}

	let bitmap: ImageBitmap;
	try {
		bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
	} catch {
		throw new ImagePrepError("Couldn't read that image — try a different photo.");
	}

	const scale = Math.min(1, MAX_EDGE_PX / Math.max(bitmap.width, bitmap.height));
	const width = Math.max(1, Math.round(bitmap.width * scale));
	const height = Math.max(1, Math.round(bitmap.height * scale));

	const canvas = document.createElement('canvas');
	canvas.width = width;
	canvas.height = height;
	const ctx = canvas.getContext('2d', { willReadFrequently: true });
	if (!ctx) throw new ImagePrepError("Image processing isn't supported in this browser.");
	ctx.drawImage(bitmap, 0, 0, width, height);
	bitmap.close();

	const imageData = ctx.getImageData(0, 0, width, height);
	const { data } = imageData;
	const pixelCount = width * height;

	// Pass 1: Rec. 601 luma per pixel, plus a histogram for the contrast
	// stretch — one array walk instead of two.
	const luma = new Uint8ClampedArray(pixelCount);
	const histogram = new Uint32Array(256);
	for (let i = 0, p = 0; i < data.length; i += 4, p++) {
		const y = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
		luma[p] = y;
		histogram[luma[p]]++;
	}

	const lowCut = pixelCount * STRETCH_LOW_PERCENTILE;
	const highCut = pixelCount * STRETCH_HIGH_PERCENTILE;
	let cumulative = 0;
	let p2 = 0;
	let p98 = 255;
	for (let level = 0; level < 256; level++) {
		cumulative += histogram[level];
		if (cumulative >= lowCut) {
			p2 = level;
			break;
		}
	}
	cumulative = 0;
	for (let level = 255; level >= 0; level--) {
		cumulative += histogram[level];
		if (cumulative >= pixelCount - highCut) {
			p98 = level;
			break;
		}
	}

	const range = p98 - p2;
	const applyStretch = range > 0 && range < SKIP_STRETCH_IF_RANGE_AT_LEAST;
	const stretchScale = applyStretch ? 255 / range : 1;

	// Pass 2: write the (optionally stretched) luma back into r/g/b.
	for (let i = 0, p = 0; i < data.length; i += 4, p++) {
		let y = luma[p];
		if (applyStretch) {
			y = Math.min(255, Math.max(0, (y - p2) * stretchScale));
		}
		data[i] = y;
		data[i + 1] = y;
		data[i + 2] = y;
	}
	ctx.putImageData(imageData, 0, 0);

	const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY);
	const commaIndex = dataUrl.indexOf(',');
	const base64 = dataUrl.slice(commaIndex + 1);

	return { dataUrl, base64, mimeType: 'image/jpeg', width, height };
}
