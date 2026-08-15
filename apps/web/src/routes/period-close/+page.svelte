<script lang="ts">
	import { api, type FiscalPeriod } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// svelte-ignore state_referenced_locally -- one-time seed from load()
	let periods = $state<FiscalPeriod[]>(data.periods);
	// svelte-ignore state_referenced_locally -- one-time seed from load()
	let depreciationRuns = $state(data.depreciationRuns);
	let busyId = $state<string | null>(null);
	let generating = $state(false);

	const currentYear = new Date().getFullYear();
	const openPeriods = $derived(periods.filter((p) => p.status === 'open').sort((a, b) => a.period_key.localeCompare(b.period_key)));
	const closedPeriods = $derived(periods.filter((p) => p.status === 'closed').sort((a, b) => b.period_key.localeCompare(a.period_key)));

	function depreciationStatus(periodKey: string): string {
		const run = depreciationRuns.find((r) => r.period_key === periodKey);
		if (!run) return 'Not run';
		if (run.status === 'completed') {
			const processed = (run.result_summary?.assets_processed as number) ?? 0;
			return `Completed (${processed} assets)`;
		}
		return run.status;
	}

	async function runDepreciation(periodKey: string) {
		busyId = `dep-${periodKey}`;
		try {
			await api.triggerPeriodicRun('asset_depreciation', periodKey);
			toast.success(`Depreciation run for ${periodKey} completed`);
			depreciationRuns = await api.listPeriodicRuns('asset_depreciation');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Depreciation run failed');
		} finally {
			busyId = null;
		}
	}

	async function closePeriod(p: FiscalPeriod) {
		busyId = p.id;
		try {
			const updated = await api.closeFiscalPeriod(p.id);
			periods = periods.map((x) => (x.id === p.id ? updated : x));
			toast.success(`Closed ${p.period_key}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to close period');
		} finally {
			busyId = null;
		}
	}

	async function reopenPeriod(p: FiscalPeriod) {
		busyId = p.id;
		try {
			const updated = await api.reopenFiscalPeriod(p.id);
			periods = periods.map((x) => (x.id === p.id ? updated : x));
			toast.success(`Reopened ${p.period_key}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to reopen period');
		} finally {
			busyId = null;
		}
	}

	async function generateYear() {
		generating = true;
		try {
			const created = await api.generateFiscalYear(currentYear);
			periods = [...periods, ...created];
			toast.success(`Generated ${created.length} periods for ${currentYear}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to generate fiscal year');
		} finally {
			generating = false;
		}
	}

	const totalDrafts = $derived(data.draftCounts.reduce((s, d) => s + d.drafts.length, 0));
</script>

<div class="mx-auto max-w-4xl space-y-6 p-6">
	<div>
		<h1 class="text-xl font-semibold">Period-End Close</h1>
		<p class="text-sm text-neutral-500">Fiscal period status, outstanding documents, and the depreciation run — everything to check before closing a period.</p>
	</div>

	<div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div class="mb-2 flex items-center justify-between">
			<p class="text-sm font-semibold">Outstanding Documents {totalDrafts > 0 ? `(${totalDrafts})` : ''}</p>
		</div>
		{#if totalDrafts === 0}
			<p class="text-sm text-green-600">Nothing still in draft across MM/SD/FI document flows.</p>
		{:else}
			<ul class="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
				{#each data.draftCounts as d (d.module)}
					<li class="rounded-md border border-neutral-200 px-3 py-2 dark:border-neutral-800">
						<a href={`/${d.module}`} class="font-medium hover:underline">{d.module.replace(/_/g, ' ')}</a>
						<p class="text-neutral-500">{d.drafts.length} draft</p>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
		<div class="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-3 py-2 dark:border-neutral-800 dark:bg-neutral-900">
			<p class="text-sm font-semibold">Open Periods</p>
			{#if periods.length === 0}
				<button
					type="button"
					disabled={generating}
					onclick={generateYear}
					class="rounded-md bg-primary-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-primary-700 disabled:opacity-50"
				>
					{generating ? 'Generating…' : `Generate ${currentYear}`}
				</button>
			{/if}
		</div>
		{#if openPeriods.length === 0}
			<p class="p-4 text-sm text-neutral-400">No open periods{periods.length > 0 ? ' — all closed' : '. Generate a fiscal year to get started.'}</p>
		{:else}
			<table class="w-full text-sm">
				<thead class="text-xs text-neutral-400">
					<tr>
						<th class="px-3 py-1.5 text-left font-medium">Period</th>
						<th class="px-3 py-1.5 text-left font-medium">Depreciation</th>
						<th class="px-3 py-1.5"></th>
					</tr>
				</thead>
				<tbody>
					{#each openPeriods as p (p.id)}
						<tr class="border-t border-neutral-100 dark:border-neutral-800">
							<td class="px-3 py-1.5 font-medium">{p.period_key}</td>
							<td class="px-3 py-1.5 text-neutral-500">{depreciationStatus(p.period_key)}</td>
							<td class="px-3 py-1.5 text-right">
								<button
									type="button"
									disabled={busyId === `dep-${p.period_key}`}
									onclick={() => runDepreciation(p.period_key)}
									class="mr-2 rounded-md border border-neutral-200 px-2 py-1 text-xs hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
								>
									Run Depreciation
								</button>
								<button
									type="button"
									disabled={busyId === p.id}
									onclick={() => closePeriod(p)}
									class="rounded-md bg-neutral-800 px-2 py-1 text-xs font-medium text-white hover:bg-neutral-900 disabled:opacity-50 dark:bg-neutral-200 dark:text-neutral-900"
								>
									{busyId === p.id ? 'Closing…' : 'Close'}
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	{#if closedPeriods.length > 0}
		<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
			<p class="border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold dark:border-neutral-800 dark:bg-neutral-900">Closed Periods</p>
			<table class="w-full text-sm">
				<tbody>
					{#each closedPeriods as p (p.id)}
						<tr class="border-t border-neutral-100 dark:border-neutral-800">
							<td class="px-3 py-1.5 text-neutral-500">{p.period_key}</td>
							<td class="px-3 py-1.5 text-right">
								<button
									type="button"
									disabled={busyId === p.id}
									onclick={() => reopenPeriod(p)}
									class="rounded-md border border-neutral-200 px-2 py-1 text-xs hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
								>
									{busyId === p.id ? 'Reopening…' : 'Reopen'}
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
