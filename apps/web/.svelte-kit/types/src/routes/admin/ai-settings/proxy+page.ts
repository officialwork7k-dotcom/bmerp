// @ts-nocheck
import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

export const load = async ({ fetch, parent }: Parameters<PageLoad>[0]) => {
	await parent();
	const api = createApi(fetch);
	const [settings, modules] = await Promise.all([api.getAiSettings(), api.listModules()]);
	return { settings, modules };
};
