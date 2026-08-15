import { localization } from './localization.svelte';

export const CURRENCY_SYMBOLS: Record<string, string> = {
	USD: '$',
	EUR: '€',
	GBP: '£',
	INR: '₹',
	JPY: '¥',
	AUD: 'A$',
	CAD: 'C$',
	CNY: '¥'
};

// Intl.NumberFormat's grouping/decimal separators are locked to a BCP-47
// locale, not settable independently — an ERP's decimal/thousands-separator
// pickers need exact control that locale mapping can't give per-currency,
// so this formats manually from the two separator settings directly rather
// than through a combined-format lookup table.
function formatNumber(
	value: number,
	decimals: number,
	decimalSep: string = localization.decimal_separator,
	thousandsSep: string = localization.thousands_separator
): string {
	const fixed = Math.abs(value).toFixed(decimals);
	const [intPart, fracPart] = fixed.split('.');
	const grouped = thousandsSep === 'none' ? intPart : intPart.replace(/\B(?=(\d{3})+(?!\d))/g, thousandsSep);
	const magnitude = grouped + (fracPart ? decimalSep + fracPart : '');
	if (value >= 0) return magnitude;
	// SAP/accounting convention: negative numbers can render as "(1,234.56)"
	// instead of "-1,234.56" — a per-profile setting, not a hardcoded sign.
	return localization.negative_number_format.startsWith('(') ? `(${magnitude})` : `-${magnitude}`;
}

export function formatMoney(value: unknown, currencyCode: string = localization.currency_code): string {
	if (value === undefined || value === null || value === '') return '';
	const symbol = CURRENCY_SYMBOLS[currencyCode] ?? currencyCode + ' ';
	const num = Number(value);
	const body = formatNumber(num, 2);
	if (localization.currency_symbol_position === 'after') return `${body} ${symbol}`;
	// Negative amounts keep the sign/parenthesis nearest the number, symbol
	// stays glued to the front: "-$1,234.56", not "$-1,234.56".
	return num < 0 && body.startsWith('-') ? `-${symbol}${body.slice(1)}` : `${symbol}${body}`;
}

export function formatDecimal(value: unknown, decimals = 2): string {
	if (value === undefined || value === null || value === '') return '';
	return formatNumber(Number(value), decimals);
}

export function formatPercent(value: unknown): string {
	if (value === undefined || value === null || value === '') return '';
	return formatNumber(Number(value), 2) + '%';
}
