import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent }) => {
	await parent();
	const api = createApi(fetch);
	const [approvals, history] = await Promise.all([api.listPendingApprovals(), api.listApprovalHistory()]);
	return { approvals, history };
};
