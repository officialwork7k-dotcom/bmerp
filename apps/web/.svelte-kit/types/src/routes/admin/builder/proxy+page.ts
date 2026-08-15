// @ts-nocheck
import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

export const load = async ({ fetch, parent }: Parameters<PageLoad>[0]) => {
	await parent();
	const modules = await createApi(fetch).listModules();
	return { modules };
};
