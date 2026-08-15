// @ts-nocheck
import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

export const load = async ({ fetch, parent }: Parameters<PageLoad>[0]) => {
	await parent();
	const api = createApi(fetch);
	const tokens = await api.listTokens();
	return { tokens };
};
