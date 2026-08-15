import { colorSchemeDark, themeQuartz } from 'ag-grid-community';

// Single shared AG Grid theme via the Theming API only — never combine with
// the legacy `ag-theme-quartz` CSS class (AG Grid v32+ error #239, and the
// two systems visibly fight each other). This installed AG Grid version
// (v32.3.x) doesn't have the newer per-param dark-mode variant syntax
// (`withParams(params, 'dark')`), so light/dark are two composed theme
// instances instead — see pickGridTheme(), which reads the app's *current*
// theme (light accent color + whether "dark" is the active theme) off the
// `<html data-theme>` attribute's computed CSS custom properties every time
// it's called, so the grid re-themes correctly for any of the five themes
// in $lib/theme.svelte.ts, not just BM.
const shared = {
	fontFamily: 'inherit',
	fontSize: 13,
	headerFontWeight: 500,
	wrapperBorderRadius: 4,
	spacing: 6
};

function readThemeVar(name: string, fallback: string): string {
	if (typeof window === 'undefined') return fallback;
	const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
	return value || fallback;
}

function isDarkTheme(): boolean {
	if (typeof document === 'undefined') return false;
	return document.documentElement.dataset.theme === 'dark';
}

export function pickGridTheme() {
	const dark = isDarkTheme();
	const accentColor = readThemeVar('--theme-primary-600', dark ? '#4f46e5' : '#714b67');
	const rowHoverColor = readThemeVar('--theme-primary-50', dark ? '#1e1b4b' : '#f1edf0');

	if (dark) {
		return themeQuartz.withPart(colorSchemeDark).withParams({
			...shared,
			accentColor,
			rowHoverColor,
			headerBackgroundColor: '#1f2937',
			borderColor: '#374151'
		});
	}
	return themeQuartz.withParams({
		...shared,
		accentColor,
		rowHoverColor,
		headerBackgroundColor: '#ffffff',
		headerTextColor: '#111827',
		borderColor: '#d8dadd'
	});
}
