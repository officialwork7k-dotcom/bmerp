<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import type { ModuleMetadata, RecordRow } from '$lib/types';

	let {
		module,
		record
	}: {
		module: ModuleMetadata;
		record: RecordRow;
	} = $props();

	const flows = $derived(module.document_flows ?? []);

	let copying = $state<string | null>(null);
	// Populated lazily per flow (open-line totals aren't needed until the
	// button's tooltip/disabled state is checked) — {flowName: totalOpenQty}.
	let openTotals = $state<Record<string, number>>({});

	$effect(() => {
		for (const flow of flows) {
			api
				.openFlowLines(module.name, record.id, flow.name)
				.then((lines) => {
					openTotals[flow.name] = lines.reduce((sum, l) => sum + l.open_qty, 0);
				})
				.catch(() => {
					// A flow that can't compute open lines (e.g. the source has no
					// lines yet) just doesn't show a total — the button itself
					// still works and surfaces the real error on click.
				});
		}
	});

	async function copy(flowName: string, targetModule: string) {
		copying = flowName;
		try {
			const created = await api.copyDocument(module.name, record.id, flowName);
			toast.success(`Created ${targetModule.replace(/_/g, ' ')} from remaining open quantity`);
			await goto(`/${targetModule}/${created.id}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to create follow-on document');
		} finally {
			copying = null;
		}
	}
</script>

{#if flows.length > 0}
	<div class="flex flex-wrap items-center gap-2 rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-900">
		<span class="text-xs font-semibold uppercase text-neutral-400">Create from this document</span>
		{#each flows as flow (flow.name)}
			{@const total = openTotals[flow.name]}
			<button
				type="button"
				disabled={copying !== null || total === 0}
				onclick={() => copy(flow.name, flow.target_module)}
				class="rounded-md border border-primary-300 bg-primary-50 px-2.5 py-1 text-xs font-medium text-primary-700 hover:bg-primary-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-primary-800 dark:bg-primary-950 dark:text-primary-300 dark:hover:bg-primary-900"
				title={total === 0 ? 'Nothing left to copy — every line is already fully referenced' : undefined}
			>
				{copying === flow.name ? 'Creating…' : flow.name}
				{#if total !== undefined && total > 0}
					<span class="ml-1 text-primary-400">({total} open)</span>
				{/if}
			</button>
		{/each}
	</div>
{/if}
