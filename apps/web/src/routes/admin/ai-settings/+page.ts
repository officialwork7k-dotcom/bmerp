import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent }) => {
	await parent();
	const api = createApi(fetch);
	const [settings, modules] = await Promise.all([api.getAiSettings(), api.listModules()]);
	return { settings, modules };
};
