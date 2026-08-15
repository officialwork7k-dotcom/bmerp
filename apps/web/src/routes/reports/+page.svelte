<script lang="ts">
	import { api, type ReportDefinition, type ReportFilter, type ReportMeasure, type SavedReport } from '$lib/api';
	import { resolveLabel } from '$lib/lookup';
	import { toast } from '$lib/toast.svelte';
	import TrialBalanceReport from '$lib/components/reports/TrialBalanceReport.svelte';
	import AgingReport from '$lib/components/reports/AgingReport.svelte';
	import LedgerReport from '$lib/components/reports/LedgerReport.svelte';
	import BalanceSheetReport from '$lib/components/reports/BalanceSheetReport.svelte';
	import IncomeStatementReport from '$lib/components/reports/IncomeStatementReport.svelte';
	import InventoryValuationReport from '$lib/components/reports/InventoryValuationReport.svelte';
	import SubledgerReconciliationReport from '$lib/components/reports/SubledgerReconciliationReport.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const TABS = [
		{ id: 'ad-hoc', label: 'Ad-hoc' },
		{ id: 'balance-sheet', label: 'Balance Sheet' },
		{ id: 'income-statement', label: 'Income Statement' },
		{ id: 'trial-balance', label: 'Trial Balance' },
		{ id: 'aging', label: 'Aging (AR/AP)' },
		{ id: 'ledger', label: 'Vendor/Customer Ledger' },
		{ id: 'inventory', label: 'Inventory Valuation' },
		{ id: 'subledger-reconciliation', label: 'Subledger Reconciliation' }
	] as const;
	let activeTab = $state<(typeof TABS)[number]['id']>('ad-hoc');

	// svelte-ignore state_referenced_locally -- one-time seed from load(), doesn't change within a page visit
	const modules = data.modules;
	// svelte-ignore state_referenced_locally -- one-time seed from load()
	let savedReports = $state<SavedReport[]>(data.savedReports);

	let sourceModule = $state(modules[0]?.name ?? '');
	let groupBy = $state<string[]>([]);
	let measures = $state<ReportMeasure[]>([]);
	let filters = $state<ReportFilter[]>([]);
	let reportName = $state('');
	let editingId = $state<string | null>(null);

	let results = $state<Record<string, unknown>[] | null>(null);
	let running = $state(false);
	let runError = $state<string | null>(null);
	// `${column}:${id}` -> resolved label, for any result column that's a LOOKUP
	// field — the report engine returns raw foreign-key ids (it doesn't know
	// what a human-readable label is), so results would otherwise show bare
	// UUIDs instead of e.g. a vendor name.
	let lookupLabels = $state<Record<string, string>>({});

	const currentModule = $derived(modules.find((m) => m.name === sourceModule));
	const fieldNames = $derived(currentModule ? currentModule.fields.map((f) => f.name) : []);

	async function resolveResultLookups(module: string, rows: Record<string, unknown>[]) {
		const mod = modules.find((m) => m.name === module);
		if (!mod) return;
		const lookupFields = mod.fields.filter((f) => f.data_type === 'LOOKUP' && f.lookup_module);
		const labels: Record<string, string> = {};
		await Promise.all(
			lookupFields.flatMap((f) =>
				rows
					.map((r) => r[f.name])
					.filter((v): v is string => typeof v === 'string')
					.filter((v, i, arr) => arr.indexOf(v) === i)
					.map(async (id) => {
						labels[`${f.name}:${id}`] = await resolveLabel(f.lookup_module!, id);
					})
			)
		);
		lookupLabels = labels;
	}

	function resetBuilder() {
		editingId = null;
		reportName = '';
		sourceModule = modules[0]?.name ?? '';
		groupBy = [];
		measures = [];
		filters = [];
		results = null;
		runError = null;
	}

	function loadIntoBuilder(r: SavedReport) {
		editingId = r.id;
		reportName = r.name;
		sourceModule = r.definition.source_module;
		groupBy = [...r.definition.group_by];
		measures = r.definition.measures.map((m) => ({ ...m }));
		filters = r.definition.filters.map((f) => ({ ...f }));
		results = null;
		runError = null;
	}

	function addMeasure() {
		measures = [...measures, { op: 'count', field: null, label: '' }];
	}
	function removeMeasure(i: number) {
		measures = measures.filter((_, idx) => idx !== i);
	}

	function addFilter() {
		filters = [...filters, { field: fieldNames[0] ?? '', op: 'eq', value: '' }];
	}
	function removeFilter(i: number) {
		filters = filters.filter((_, idx) => idx !== i);
	}

	function toggleGroupBy(field: string) {
		groupBy = groupBy.includes(field) ? groupBy.filter((f) => f !== field) : [...groupBy, field];
	}

	function currentDefinition(): ReportDefinition {
		return {
			source_module: sourceModule,
			group_by: groupBy,
			measures: measures.map((m) => ({ ...m, field: m.op === 'count' ? null : m.field })),
			filters
		};
	}

	async function run() {
		if (!sourceModule) return;
		running = true;
		runError = null;
		lookupLabels = {};
		try {
			results = await api.runReport(currentDefinition());
			await resolveResultLookups(sourceModule, results);
		} catch (e) {
			runError = e instanceof Error ? e.message : 'Failed to run report';
			results = null;
		} finally {
			running = false;
		}
	}

	async function save() {
		if (!reportName.trim()) {
			toast.error('Give the report a name first');
			return;
		}
		try {
			if (editingId) {
				const updated = await api.updateReport(editingId, reportName, currentDefinition());
				savedReports = savedReports.map((r) => (r.id === editingId ? updated : r));
				toast.success('Report updated');
			} else {
				const created = await api.createReport(reportName, currentDefinition());
				savedReports = [created, ...savedReports];
				editingId = created.id;
				toast.success('Report saved');
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save report');
		}
	}

	async function runSaved(r: SavedReport) {
		loadIntoBuilder(r);
		running = true;
		runError = null;
		lookupLabels = {};
		try {
			results = await api.runSavedReport(r.id);
			await resolveResultLookups(r.definition.source_module, results);
		} catch (e) {
			runError = e instanceof Error ? e.message : 'Failed to run report';
		} finally {
			running = false;
		}
	}

	async function remove(r: SavedReport) {
		try {
			await api.deleteReport(r.id);
			savedReports = savedReports.filter((x) => x.id !== r.id);
			if (editingId === r.id) resetBuilder();
			toast.success('Report deleted');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to delete report');
		}
	}

	function formatCell(column: string, v: unknown): string {
		if (v === null || v === undefined) return '—';
		if (typeof v === 'string' && lookupLabels[`${column}:${v}`]) return lookupLabels[`${column}:${v}`];
		if (typeof v === 'number') return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
		return String(v);
	}
</script>

<div class="mx-auto max-w-6xl space-y-6 p-6">
	<div>
		<h1 class="text-xl font-semibold">Reports</h1>
		<p class="text-sm text-neutral-500">Group and aggregate any module's data, or run a standard financial report.</p>
	</div>

	<div class="flex gap-1 border-b border-neutral-200 dark:border-neutral-800">
		{#each TABS as tab (tab.id)}
			<button
				type="button"
				onclick={() => (activeTab = tab.id)}
				class="border-b-2 px-3 py-2 text-sm font-medium {activeTab === tab.id
					? 'border-primary-600 text-primary-700 dark:text-primary-400'
					: 'border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
			>
				{tab.label}
			</button>
		{/each}
	</div>

	{#if activeTab === 'balance-sheet'}
		<BalanceSheetReport />
	{:else if activeTab === 'income-statement'}
		<IncomeStatementReport />
	{:else if activeTab === 'trial-balance'}
		<TrialBalanceReport />
	{:else if activeTab === 'aging'}
		<AgingReport />
	{:else if activeTab === 'ledger'}
		<LedgerReport />
	{:else if activeTab === 'inventory'}
		<InventoryValuationReport />
	{:else if activeTab === 'subledger-reconciliation'}
		<SubledgerReconciliationReport />
	{:else}
	<div class="grid grid-cols-1 gap-6 lg:grid-cols-[16rem_1fr]">
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<p class="text-xs font-semibold uppercase tracking-wide text-neutral-400">Saved Reports</p>
				<button type="button" onclick={resetBuilder} class="text-xs text-primary-600 hover:underline">+ New</button>
			</div>
			{#if savedReports.length === 0}
				<p class="text-sm text-neutral-400">None yet</p>
			{:else}
				<ul class="space-y-1">
					{#each savedReports as r (r.id)}
						<li class="flex items-center justify-between rounded-md px-2 py-1.5 text-sm {editingId === r.id ? 'bg-primary-50 dark:bg-primary-950' : 'hover:bg-neutral-100 dark:hover:bg-neutral-800'}">
							<button type="button" onclick={() => runSaved(r)} class="min-w-0 flex-1 truncate text-left">{r.name}</button>
							<button
								type="button"
								onclick={() => remove(r)}
								class="ml-1 shrink-0 rounded px-1 text-neutral-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950"
								aria-label={`Delete ${r.name}`}
							>
								✕
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</div>

		<div class="space-y-4">
			<div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<div>
						<label class="mb-1 block text-xs font-medium text-neutral-500" for="report-name">Report Name</label>
						<input
							id="report-name"
							type="text"
							bind:value={reportName}
							placeholder="e.g. Vendor Invoice Totals by Status"
							class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
						/>
					</div>
					<div>
						<label class="mb-1 block text-xs font-medium text-neutral-500" for="source-module">Source Module</label>
						<select
							id="source-module"
							bind:value={sourceModule}
							onchange={() => {
								groupBy = [];
								measures = [];
								filters = [];
							}}
							class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
						>
							{#each modules as m (m.name)}
								<option value={m.name}>{m.label}</option>
							{/each}
						</select>
					</div>
				</div>

				<div class="mt-4">
					<p class="mb-1.5 text-xs font-medium text-neutral-500">Group By</p>
					<div class="flex flex-wrap gap-1.5">
						{#each fieldNames as f (f)}
							<button
								type="button"
								onclick={() => toggleGroupBy(f)}
								class="rounded-full border px-2.5 py-1 text-xs {groupBy.includes(f)
									? 'border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300'
									: 'border-neutral-200 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-800'}"
							>
								{f}
							</button>
						{/each}
					</div>
				</div>

				<div class="mt-4">
					<div class="mb-1.5 flex items-center justify-between">
						<p class="text-xs font-medium text-neutral-500">Measures</p>
						<button type="button" onclick={addMeasure} class="text-xs text-primary-600 hover:underline">+ Add measure</button>
					</div>
					<div class="space-y-1.5">
						{#each measures as m, i (i)}
							<div class="flex items-center gap-1.5">
								<select bind:value={m.op} class="rounded-md border border-neutral-200 px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900">
									<option value="count">Count</option>
									<option value="sum">Sum</option>
									<option value="avg">Avg</option>
									<option value="min">Min</option>
									<option value="max">Max</option>
								</select>
								{#if m.op !== 'count'}
									<select bind:value={m.field} class="rounded-md border border-neutral-200 px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900">
										{#each fieldNames as f (f)}
											<option value={f}>{f}</option>
										{/each}
									</select>
								{/if}
								<input
									type="text"
									bind:value={m.label}
									placeholder="label (optional)"
									class="w-32 rounded-md border border-neutral-200 px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900"
								/>
								<button type="button" onclick={() => removeMeasure(i)} class="text-xs text-neutral-400 hover:text-red-600">✕</button>
							</div>
						{/each}
						{#if measures.length === 0}<p class="text-xs text-neutral-400">No measures — showing distinct group rows only.</p>{/if}
					</div>
				</div>

				<div class="mt-4">
					<div class="mb-1.5 flex items-center justify-between">
						<p class="text-xs font-medium text-neutral-500">Filters</p>
						<button type="button" onclick={addFilter} class="text-xs text-primary-600 hover:underline">+ Add filter</button>
					</div>
					<div class="space-y-1.5">
						{#each filters as f, i (i)}
							<div class="flex items-center gap-1.5">
								<select bind:value={f.field} class="rounded-md border border-neutral-200 px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900">
									{#each fieldNames as fn (fn)}
										<option value={fn}>{fn}</option>
									{/each}
								</select>
								<select bind:value={f.op} class="rounded-md border border-neutral-200 px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900">
									<option value="eq">=</option>
									<option value="neq">≠</option>
									<option value="gt">&gt;</option>
									<option value="gte">≥</option>
									<option value="lt">&lt;</option>
									<option value="lte">≤</option>
								</select>
								<input
									type="text"
									bind:value={f.value}
									placeholder="value"
									class="w-32 rounded-md border border-neutral-200 px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900"
								/>
								<button type="button" onclick={() => removeFilter(i)} class="text-xs text-neutral-400 hover:text-red-600">✕</button>
							</div>
						{/each}
					</div>
				</div>

				<div class="mt-4 flex items-center gap-2">
					<button
						type="button"
						disabled={running || !sourceModule}
						onclick={run}
						class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
					>
						{running ? 'Running…' : 'Run'}
					</button>
					<button
						type="button"
						onclick={save}
						class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
					>
						{editingId ? 'Update' : 'Save'}
					</button>
				</div>
			</div>

			{#if runError}
				<p class="text-sm text-red-600">{runError}</p>
			{/if}

			{#if results}
				<div class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
					{#if results.length === 0}
						<p class="p-4 text-sm text-neutral-400">No rows.</p>
					{:else}
						<table class="w-full text-sm">
							<thead class="bg-neutral-50 dark:bg-neutral-900">
								<tr>
									{#each Object.keys(results[0]) as col (col)}
										<th class="px-3 py-2 text-left font-medium text-neutral-500">{col}</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each results as row, i (i)}
									<tr class="border-t border-neutral-100 dark:border-neutral-800">
										{#each Object.keys(row) as col (col)}
											<td class="px-3 py-1.5">{formatCell(col, row[col])}</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}
				</div>
			{/if}
		</div>
	</div>
	{/if}
</div>
