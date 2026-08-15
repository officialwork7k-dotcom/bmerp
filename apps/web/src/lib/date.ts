import { localization } from './localization.svelte';

type DateToken = 'D' | 'M' | 'Y';

const FORMAT_ORDERS: Record<string, [DateToken, DateToken, DateToken]> = {
	'DD/MM/YYYY': ['D', 'M', 'Y'],
	'MM/DD/YYYY': ['M', 'D', 'Y'],
	'YYYY-MM-DD': ['Y', 'M', 'D'],
	'DD.MM.YYYY': ['D', 'M', 'Y'],
	'DD-MM-YYYY': ['D', 'M', 'Y']
};

const FORMAT_SEPARATORS: Record<string, string> = {
	'DD/MM/YYYY': '/',
	'MM/DD/YYYY': '/',
	'YYYY-MM-DD': '-',
	'DD.MM.YYYY': '.',
	'DD-MM-YYYY': '-'
};

function pad(n: number): string {
	return String(n).padStart(2, '0');
}

function toISO(y: number, m: number, d: number): string {
	return `${y}-${pad(m)}-${pad(d)}`;
}

export function todayISO(): string {
	const d = new Date();
	return toISO(d.getFullYear(), d.getMonth() + 1, d.getDate());
}

/** Turns configured display format into the `yyyy-mm-dd` the backend and
 * every internal comparison expect. Supports SAP-style quick entry:
 * "t" / "today" for today, "t+3" / "t-1" for relative days, a bare ISO
 * string passed through as-is, and short numeric dates ("1.1.26",
 * "1/1/2026", "01-01-26") interpreted using the configured field order —
 * a 2-digit day/month with no year assumes the current year; a 2-digit year
 * expands with a SAP-style pivot (<50 → 20xx, else 19xx). Returns null for
 * anything that doesn't parse into a real calendar date, so a caller can
 * fall back to the previous value instead of silently corrupting it. */
export function parseDateInput(text: string, format: string = localization.date_format): string | null {
	const t = text.trim();
	if (!t) return null;

	const lower = t.toLowerCase();
	if (lower === 't' || lower === 'today') return todayISO();

	const relative = lower.match(/^t([+-]\d+)$/);
	if (relative) {
		const d = new Date();
		d.setDate(d.getDate() + Number(relative[1]));
		return toISO(d.getFullYear(), d.getMonth() + 1, d.getDate());
	}

	if (/^\d{4}-\d{2}-\d{2}$/.test(t)) {
		return isValidCalendarDate(t) ? t : null;
	}

	const parts = t.split(/[.\/\-\s]+/).filter(Boolean);
	if (parts.length < 2 || parts.some((p) => !/^\d{1,4}$/.test(p))) return null;

	const order = FORMAT_ORDERS[format] ?? FORMAT_ORDERS['DD/MM/YYYY'];
	const now = new Date();
	let day: number;
	let month: number;
	let year: number;

	if (parts.length === 2) {
		// No year given — use the format's day/month order, assume this year.
		const dmOrder = order.filter((token) => token !== 'Y');
		const values: Partial<Record<DateToken, number>> = {};
		dmOrder.forEach((token, i) => (values[token] = Number(parts[i])));
		day = values.D!;
		month = values.M!;
		year = now.getFullYear();
	} else {
		const values: Partial<Record<DateToken, number>> = {};
		order.forEach((token, i) => (values[token] = Number(parts[i])));
		day = values.D!;
		month = values.M!;
		year = values.Y!;
		if (year < 100) year += year < 50 ? 2000 : 1900;
	}

	if (!day || !month || month < 1 || month > 12 || day < 1 || day > 31) return null;
	const iso = toISO(year, month, day);
	return isValidCalendarDate(iso) ? iso : null;
}

function isValidCalendarDate(iso: string): boolean {
	const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
	if (!m) return false;
	const [, y, mo, d] = m;
	const dt = new Date(Date.UTC(Number(y), Number(mo) - 1, Number(d)));
	return dt.getUTCFullYear() === Number(y) && dt.getUTCMonth() + 1 === Number(mo) && dt.getUTCDate() === Number(d);
}

/** Renders a stored `yyyy-mm-dd` (or a full ISO datetime, using just its
 * date part) in the configured display format. Never used for parsing —
 * the stored value is always the ISO form; this is purely for what the
 * user sees, in both read-only display and an unfocused entry field. */
export function formatDateDisplay(iso: string | null | undefined, format: string = localization.date_format): string {
	if (!iso) return '';
	const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
	if (!m) return String(iso);
	const [, y, mo, d] = m;
	const sep = FORMAT_SEPARATORS[format] ?? '/';
	const order = FORMAT_ORDERS[format] ?? FORMAT_ORDERS['DD/MM/YYYY'];
	const map: Record<DateToken, string> = { D: d, M: mo, Y: y };
	return order.map((token) => map[token]).join(sep);
}
