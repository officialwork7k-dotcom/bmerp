import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent }) => {
	await parent();
	const api = createApi(fetch);
	const webhooks = await api.listWebhooks();
	return { webhooks };
};
