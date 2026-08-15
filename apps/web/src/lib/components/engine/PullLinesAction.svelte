<script lang="ts">
	import { api } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import type { ModuleMetadata } from '$lib/types';

	let {
		module,
		values,
		childRows
	}: {
		module: ModuleMetadata;
		values: Record<string, unknown>;
		/** The parent's $state object, mutated in place (`childRows[rel] = [...]`) —
		 * not reassigned, so no $bindable needed; Svelte 5's deep reactivity on
		 * $state proxies picks up the in-place property write. */
		childRows: Record<string, Record<string, unknown>[]>;
	} = $props();

	type Flow = { source_module: string; flow_name: string; header_field_map: Record<string, string>; target_line_relation: string | null };

	let flows = $state<Flow[]>([]);
	let pulling = $state<string | null>(null);

	$effect(() => {
		api.flowsInto(module.name).then((f) => (flows = f));
	});

	// A flow "lands" on this module via one of its own LOOKUP fields (e.g.
	// vendor_invoices.gr_id, target of goods_receipts' "GR to Vendor
	// Invoice" flow's header_field_map). Only offer the pull action once
	// that field actually has a value selected.
	const pullable = $derived(
		flows
			.map((f) => {
				const triggerField = Object.entries(f.header_field_map).find(
					([, target]) => module.fields.find((mf) => mf.name === target)?.data_type === 'LOOKUP'
				)?.[1];
				return triggerField && f.target_line_relation ? { ...f, triggerField } : null;
			})
			.filter((f): f is Flow & { triggerField: string } => f !== null && !!values[f.triggerField])
	);

	async function pull(flow: Flow & { triggerField: string }) {
		pulling = flow.flow_name;
		try {
			const preview = await api.previewFlowCopy(flow.source_module, String(values[flow.triggerField]), flow.flow_name);
			for (const [k, v] of Object.entries(preview.header)) {
				// `k in values` would miss any header field the user hasn't
				// touched yet (create mode only seeds keys that have a static
				// `field.default` — a LOOKUP like vendor_id is absent from
				// `values` entirely until something sets it), so check against
				// the module's actual field list instead of the current values.
				if (module.fields.some((f) => f.name === k)) values[k] = v;
			}
			const relName = flow.target_line_relation!;
			childRows[relName] = [...(childRows[relName] ?? []), ...preview.lines];
			// Untracked relations (e.g. other-charges) riding along with the
			// tracked lines — same in-place merge, just keyed by whatever
			// relation name the flow's extra_relations mapped them to.
			for (const [extraRel, rows] of Object.entries(preview.extra ?? {})) {
				childRows[extraRel] = [...(childRows[extraRel] ?? []), ...rows];
			}
			toast.success(`Pulled ${preview.lines.length} line${preview.lines.length === 1 ? '' : 's'} from ${flow.source_module.replace(/_/g, ' ')}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to pull lines');
		} finally {
			pulling = null;
		}
	}
</script>

{#if pullable.length > 0}
	<div class="flex flex-wrap items-center gap-2 rounded-lg border border-primary-200 bg-primary-50 p-3 dark:border-primary-900 dark:bg-primary-950">
		<span class="text-xs font-semibold uppercase text-primary-600 dark:text-primary-400">Pull lines</span>
		{#each pullable as flow (flow.flow_name)}
			<button
				type="button"
				disabled={pulling !== null}
				onclick={() => pull(flow)}
				class="rounded-md border border-primary-300 bg-white px-2.5 py-1 text-xs font-medium text-primary-700 hover:bg-primary-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-primary-800 dark:bg-neutral-900 dark:text-primary-300 dark:hover:bg-primary-900"
			>
				{pulling === flow.flow_name ? 'Pulling…' : `from ${flow.source_module.replace(/_/g, ' ')}`}
			</button>
		{/each}
	</div>
{/if}
