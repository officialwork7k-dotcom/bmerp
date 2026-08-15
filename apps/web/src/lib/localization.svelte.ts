import { createApi } from './api';

export interface LocalizationSettings {
	date_format: string;
	time_format: string;
	timezone: string;
	first_day_of_week: string;
	decimal_separator: string;
	thousands_separator: string;
	currency_code: string;
	currency_symbol_position: string;
	negative_number_format: string;
	fiscal_year_start_month: number;
	notification_position: string;
	notification_duration_seconds: number;
}

const DEFAULTS: LocalizationSettings = {
	date_format: 'DD/MM/YYYY',
	time_format: '24-hour',
	timezone: 'UTC',
	first_day_of_week: 'Monday',
	decimal_separator: '.',
	thousands_separator: ',',
	currency_code: 'USD',
	currency_symbol_position: 'before',
	negative_number_format: '-1,234.56',
	fiscal_year_start_month: 1,
	notification_position: 'bottom-center',
	notification_duration_seconds: 4
};

// A plain module-level $state singleton, not passed through component props —
// FieldControl/ListPage/DataTable/EmbeddedGrid are deep, generic children with
// no natural path back to the root layout's loaded data, and every one of
// them needs this synchronously (cell formatters can't await). Loaded once
// via loadLocalization() from the root +layout.ts before any page renders.
export const localization = $state<LocalizationSettings>({ ...DEFAULTS });

let loadPromise: Promise<void> | null = null;

export function loadLocalization(fetchImpl: typeof fetch = fetch): Promise<void> {
	if (loadPromise) return loadPromise;
	loadPromise = createApi(fetchImpl)
		// Querying `is_default=true` first, rather than an arbitrary
		// `limit: '1'` of whatever the DB returns first, is the whole point
		// of the default-flag mechanism — with more than one profile saved,
		// which one wins used to be nondeterministic.
		.listRecords('localization_settings', { is_default: 'true', limit: '1' })
		.then(async (rows) => {
			let row = Array.isArray(rows) ? rows[0] : undefined;
			if (!row) {
				// No profile is marked default yet (fresh install, or the
				// only profile predates the flag) — fall back to whatever
				// exists rather than sitting on hardcoded defaults forever.
				const fallback = await createApi(fetchImpl).listRecords('localization_settings', { limit: '1' });
				row = Array.isArray(fallback) ? fallback[0] : undefined;
			}
			if (!row) return;
			for (const key of Object.keys(DEFAULTS) as (keyof LocalizationSettings)[]) {
				const value = row[key];
				if (typeof value === typeof DEFAULTS[key]) (localization as unknown as Record<string, unknown>)[key] = value;
			}
		})
		// No localization_settings module/record yet (fresh install) — fall
		// back to defaults rather than failing every page load.
		.catch(() => {});
	return loadPromise;
}
