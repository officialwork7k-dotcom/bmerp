import { redirect } from '@sveltejs/kit';
import { createApi } from '$lib/api';
import { fetchCurrentUser } from '$lib/auth.svelte';
import { loadLocalization } from '$lib/localization.svelte';
import type { LayoutLoad } from './$types';

// CSR-only: relative `fetch` calls in `load` functions must go through the
// real HTTP layer (browser fetch → our /api/[...path] proxy route) —
// SvelteKit's SSR `fetch` resolves relative URLs against its own route
// tree in-process, which behaves differently. Also the lower-memory choice
// per the RAM budget: an authenticated internal tool has no SEO/no-JS need.
export const ssr = false;

export const load: LayoutLoad = async ({ fetch, depends, url }) => {
	depends('app:modules');
	depends('app:localization');
	depends('app:auth');

	const user = await fetchCurrentUser(fetch);
	if (!user) {
		if (url.pathname !== '/login') {
			const redirectTo = url.pathname === '/' ? '' : `?redirect=${encodeURIComponent(url.pathname + url.search)}`;
			throw redirect(303, `/login${redirectTo}`);
		}
		return { modules: [], user: null };
	}

	// Awaited alongside modules, not fire-and-forgot: FieldControl/ListPage/
	// EmbeddedGrid read the localization $state singleton synchronously
	// (cell formatters can't await), so it has to be populated before the
	// first page renders, not just "eventually."
	const [modules] = await Promise.all([createApi(fetch).listModules(), loadLocalization(fetch)]);
	return { modules, user };
};
