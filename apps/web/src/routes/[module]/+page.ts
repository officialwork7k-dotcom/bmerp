import { createApi } from '$lib/api';
import { displayName } from '$lib/types';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch, parent }) => {
	// Waits for the root layout's auth check (and its redirect-to-/login on
	// 401) to resolve before firing any request of its own — otherwise this
	// load's fetches race the parent's and throw their own uncaught 401s.
	await parent();
	const api = createApi(fetch);
	const [module, records] = await Promise.all([
		api.getModule(params.module),
		api.listRecords(params.module, { limit: '100' })
	]);

	// Resolve LOOKUP foreign-key ids to display labels here in `load`, not in
	// a component $effect: doing it reactively in a component previously
	// caused a genuine effect_update_depth_exceeded loop (a $derived reading
	// a $state that its own resolution effect reassigned). `load` runs once
	// per navigation and its result is just data, so there's no cycle.
	const lookupFields = module.fields.filter((f) => f.name !== 'id' && f.data_type === 'LOOKUP' && f.lookup_module);
	const lookupEntries = await Promise.all(
		lookupFields.map(async (field) => {
			const relatedRecords = await api.listRecords(field.lookup_module!, { limit: '500' });
			return [field.name, Object.fromEntries(relatedRecords.map((r) => [r.id, displayName(r)]))] as const;
		})
	);
	const lookupLabels = Object.fromEntries(lookupEntries);

	return { module, records, lookupLabels };
};
