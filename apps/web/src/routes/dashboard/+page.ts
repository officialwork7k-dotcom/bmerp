import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

function todayISO(): string {
	return new Date().toISOString().slice(0, 10);
}

export const load: PageLoad = async ({ fetch, parent }) => {
	await parent();
	const api = createApi(fetch);
	const today = todayISO();
	const yearStart = today.slice(0, 4) + '-01-01';
	const monthStart = today.slice(0, 7) + '-01';

	const [balanceSheet, ytdIncome, mtdIncome, apAging, arAging, approvals] = await Promise.all([
		api.balanceSheet(today),
		api.incomeStatement(yearStart, today),
		api.incomeStatement(monthStart, today),
		api.aging('AP', today).catch(() => []),
		api.aging('AR', today).catch(() => []),
		api.listPendingApprovals().catch(() => [])
	]);

	return { balanceSheet, ytdIncome, mtdIncome, apAging, arAging, approvals };
};
