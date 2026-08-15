import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

const DOC_MODULES = ['vendor_invoices', 'customer_invoices', 'goods_receipts', 'deliveries'] as const;

export const load: PageLoad = async ({ fetch }) => {
	const api = createApi(fetch);

	const [periods, depreciationRuns, draftCounts] = await Promise.all([
		api.listFiscalPeriods().catch(() => []),
		api.listPeriodicRuns('asset_depreciation').catch(() => []),
		Promise.all(
			DOC_MODULES.map(async (m) => ({
				module: m,
				drafts: await api.listRecords(m, { status: 'draft', limit: '200' }).catch(() => [])
			}))
		)
	]);

	return { periods, depreciationRuns, draftCounts };
};
