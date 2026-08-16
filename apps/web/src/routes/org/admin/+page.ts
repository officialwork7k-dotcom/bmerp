import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const api = createApi(fetch);
	const [users, invites, aiSettings] = await Promise.all([
		api.listOrgUsers(),
		api.listOrgInvites(),
		api.getOrgAiSettings()
	]);
	return { users, invites, aiSettings };
};
