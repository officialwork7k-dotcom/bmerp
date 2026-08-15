import { error } from '@sveltejs/kit';
import { createApi } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch, parent }) => {
	await parent();
	const api = createApi(fetch);
	const [module, record] = await Promise.all([
		api.getModule(params.module),
		params.id === 'new'
			? Promise.resolve(undefined)
			: api.getRecord(params.module, params.id).catch((e) => {
					// A stale link (a notification from before the record was
					// deleted, or — same shape — one pointing at a record from an
					// org the session has since switched away from) throws a plain
					// "404 Not Found: ..." Error from api.ts's request(); left
					// uncaught, SvelteKit surfaces that as a generic 500 instead of
					// "this record doesn't exist," which reads as the whole page
					// being broken rather than one link being stale.
					const message = e instanceof Error ? e.message : String(e);
					if (message.startsWith('404')) {
						throw error(404, 'This record was not found — it may have been deleted, or belongs to a different organization than the one you\'re signed into.');
					}
					throw e;
				})
	]);

	const embeddedRels = module.relationships.filter((r) => r.embedded);
	const childModuleEntries = await Promise.all(
		embeddedRels.map(async (rel) => [rel.related_module, await api.getModule(rel.related_module)] as const)
	);
	const childModules = Object.fromEntries(childModuleEntries);

	return { module, record, childModules };
};
