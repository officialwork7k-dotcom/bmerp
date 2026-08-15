import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent }) => {
	const { modules } = await parent();
	const api = createApi(fetch);
	const [roles, users, clients, approvalRules] = await Promise.all([
		api.listRoles(),
		api.listUsers(),
		api.listClients(),
		api.listApprovalRules()
	]);
	return { roles, users, clients, approvalRules, modules };
};
