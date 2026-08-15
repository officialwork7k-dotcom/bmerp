import { api } from '$lib/api';

export interface ThemeOption {
	id: string;
	label: string;
	/** Swatch color for the dropdown — each theme's --theme-primary-600. */
	swatch: string;
}

export const THEMES: ThemeOption[] = [
	{ id: 'bm', label: 'BM (default)', swatch: '#714b67' },
	// Yellow/Orange swatches match app.css's --theme-primary-600, which was
	// darkened from the original amber/terracotta to clear WCAG AA contrast
	// for white button text (see app.css comments) — kept in sync so the
	// dropdown swatch shows the color a user actually gets, not the old one.
	{ id: 'yellow', label: 'Yellow', swatch: '#b06105' },
	{ id: 'blue', label: 'Blue', swatch: '#2563eb' },
	{ id: 'orange', label: 'Orange', swatch: '#b75a3c' },
	{ id: 'dark', label: 'Dark', swatch: '#4f46e5' }
];

const THEME_IDS = new Set(THEMES.map((t) => t.id));
const DEFAULT_THEME = 'bm';
const STORAGE_KEY = 'mf:theme';

export const themeState: { current: string } = $state({ current: DEFAULT_THEME });

function normalize(id: string | null | undefined): string {
	return id && THEME_IDS.has(id) ? id : DEFAULT_THEME;
}

/** Applies a theme to the DOM + localStorage only — no network call. Used
 * both by setTheme() below and by the boot-time sync in +layout.svelte,
 * which must not re-PUT the user's own already-stored preference back at
 * them on every page load. */
export function applyTheme(id: string): void {
	const normalized = normalize(id);
	themeState.current = normalized;
	if (typeof document !== 'undefined') {
		document.documentElement.dataset.theme = normalized;
	}
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(STORAGE_KEY, normalized);
	}
}

export function readStoredTheme(): string {
	if (typeof localStorage === 'undefined') return DEFAULT_THEME;
	return normalize(localStorage.getItem(STORAGE_KEY));
}

/** User-initiated theme change: applies immediately (no flash waiting on
 * the network) and persists server-side so it follows the user to another
 * device/browser the next time they log in there. */
export async function setTheme(id: string): Promise<void> {
	applyTheme(id);
	try {
		await api.setTheme(normalize(id));
	} catch {
		// Non-critical — the theme is already applied locally; a failed
		// PUT just means it won't yet follow the user to another device.
	}
}
