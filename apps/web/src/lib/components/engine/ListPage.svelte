<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { DropdownMenu } from 'bits-ui';
	import type { ColumnDef } from '@tanstack/table-core';
	import type { ModuleMetadata, RecordRow } from '$lib/types';
	import { embeddedChildren } from '$lib/types';
	import DataTable from './DataTable.svelte';
	import CardList from './CardList.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import RecycleBinDialog from './RecycleBinDialog.svelte';
	import { formatDateDisplay } from '$lib/date';
	import { formatDecimal, formatMoney, formatPercent } from '$lib/format';
	import { api } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import { canCreate, canDelete } from '$lib/auth.svelte';

	let {
		module,
		records,
		lookupLabels = {}
	}: {
		module: ModuleMetadata;
		records: RecordRow[];
		/** field name -> { foreign id -> display label }, resolved once in `load()`. */
		lookupLabels?: Record<string, Record<string, string>>;
	} = $props();

	const listFields = $derived(module.fields.filter((f) => f.name !== 'id').slice(0, 6));
	const rels = $derived(embeddedChildren(module));
	const hasChildren = $derived(rels.length > 0);

	// Below Tailwind's `sm` (640px) the table view switches to CardList —
	// tracked via matchMedia rather than a resize listener so it only
	// re-evaluates at the actual breakpoint crossing, not on every pixel.
	let isNarrow = $state(false);
	$effect(() => {
		const query = window.matchMedia('(max-width: 639px)');
		isNarrow = query.matches;
		const onChange = (e: MediaQueryListEvent) => (isNarrow = e.matches);
		query.addEventListener('change', onChange);
		return () => query.removeEventListener('change', onChange);
	});

	let groupBy = $state<string | null>(null);
	let search = $state('');
	let recycleBinOpen = $state(false);
	let exporting = $state(false);
	let importing = $state(false);
	let fileInput = $state<HTMLInputElement>();

	async function exportCsv() {
		exporting = true;
		try {
			const blob = await api.exportRecords(module.name);
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${module.name}.csv`;
			document.body.appendChild(a);
			a.click();
			a.remove();
			URL.revokeObjectURL(url);
			toast.success(`${module.label} exported`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Export failed');
		} finally {
			exporting = false;
		}
	}

	function pickImportFile() {
		fileInput?.click();
	}

	async function onImportFileSelected(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (fileInput) fileInput.value = '';
		if (!file) return;
		importing = true;
		try {
			const summary = await api.importRecords(module.name, file);
			if (summary.errors.length > 0) {
				toast.warning(`Imported ${summary.created} row(s), ${summary.errors.length} failed — see console for details`);
				console.warn(`Import errors for ${module.name}:`, summary.errors);
			} else {
				toast.success(`Imported ${summary.created} ${module.label.toLowerCase()} row(s)`);
			}
			await invalidateAll();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Import failed');
		} finally {
			importing = false;
		}
	}

	const filteredRecords = $derived.by(() => {
		const term = search.trim().toLowerCase();
		if (!term) return records;
		return records.filter((r) =>
			listFields.some((f) => {
				const raw = r[f.name];
				// LOOKUP fields store the foreign id, DATE stores raw ISO —
				// search against what's actually displayed, not the
				// underlying value the user never sees.
				const format = formatterFor(f);
				const displayed = format ? format(raw) : raw;
				return String(displayed ?? '').toLowerCase().includes(term);
			})
		);
	});

	const numericTypes = new Set(['INTEGER', 'DECIMAL', 'MONEY', 'PERCENT']);
	function formatterFor(f: ModuleMetadata['fields'][number]): ((v: unknown) => string) | undefined {
		if (f.data_type === 'LOOKUP') {
			const labelMap = lookupLabels[f.name];
			return labelMap ? (v: unknown) => labelMap[String(v)] ?? String(v ?? '') : undefined;
		}
		if (f.data_type === 'DATE') return (v) => formatDateDisplay(v as string | undefined);
		if (f.data_type === 'MONEY') return (v) => formatMoney(v);
		if (f.data_type === 'PERCENT') return (v) => formatPercent(v);
		if (f.data_type === 'DECIMAL') return (v) => formatDecimal(v, f.scale ?? 2);
		if (f.data_type === 'BOOLEAN') {
			// A default-flag column reads as a status, not a checkbox — "which
			// row is active" is the whole point of glancing at this list.
			if (f.is_default_flag) return (v) => (v ? '★ Default' : '');
			return (v) => (v ? 'Yes' : 'No');
		}
		return undefined;
	}
	const columns = $derived<ColumnDef<RecordRow, unknown>[]>(
		listFields.map((f) => {
			const format = formatterFor(f);
			const align = numericTypes.has(f.data_type) ? ('right' as const) : undefined;
			return {
				id: f.name,
				accessorKey: f.name,
				header: f.label,
				enableGrouping: f.data_type === 'ENUM' || f.data_type === 'LOOKUP' || f.data_type === 'BOOLEAN',
				meta: format || align ? { format, align } : undefined
			};
		})
	);

	const groupableFields = $derived(listFields.filter((f) => f.data_type === 'ENUM' || f.data_type === 'BOOLEAN'));

	const childRowsByParent = $state<Record<string, RecordRow[]>>({});
	async function loadChildren(parentId: string) {
		if (childRowsByParent[parentId]) return;
		const all: RecordRow[] = [];
		for (const rel of rels) {
			const res = await fetch(`/api/data/${rel.related_module}?${rel.foreign_key}=${parentId}`);
			if (res.ok) {
				const rows = await res.json();
				all.push(...(Array.isArray(rows) ? rows : (rows.items ?? [])));
			}
		}
		childRowsByParent[parentId] = all;
	}

	function openRecord(record: RecordRow) {
		goto(`/${module.name}/${record.id}`);
	}
</script>

<div class="p-4 sm:p-6">
	<div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-xl font-semibold">{module.label}</h1>
			<p class="text-sm text-neutral-400">{records.length} {records.length === 1 ? 'record' : 'records'}</p>
		</div>
		<div class="flex flex-wrap items-center gap-2 sm:gap-3">
			{#if records.length > 0}
				<input
					type="search"
					placeholder="Search…"
					bind:value={search}
					class="h-9 w-full flex-1 rounded-md border border-neutral-300 px-3 text-sm outline-none focus:ring-2 focus:ring-primary-500 sm:w-48 sm:flex-none dark:border-neutral-700 dark:bg-neutral-900"
				/>
			{/if}
			{#if groupableFields.length}
				<label class="hidden text-sm text-neutral-500 sm:inline-flex sm:items-center">
					Group by
					<select bind:value={groupBy} class="ml-1 rounded-md border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900">
						<option value={null}>None</option>
						{#each groupableFields as f (f.name)}
							<option value={f.name}>{f.label}</option>
						{/each}
					</select>
				</label>
			{/if}

			<!-- Secondary actions collapse into a "⋯" menu below `sm` so they
			     can't push New/Search off the edge of a phone screen the way a
			     plain unwrapped flex row used to (Export/Import/New landed at
			     x>400 on a 375px viewport — reachable only by scrolling a
			     container that gave no visible scrollbar hint). Above `sm`
			     there's room, so they render as normal buttons instead. -->
			<div class="sm:hidden">
				<DropdownMenu.Root>
						<DropdownMenu.Trigger
							class="flex h-9 w-9 items-center justify-center rounded-md border border-neutral-300 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
							aria-label="More actions"
						>
							⋯
						</DropdownMenu.Trigger>
						<DropdownMenu.Portal>
							<DropdownMenu.Content
								class="z-50 w-52 rounded-md border border-neutral-200 bg-white p-1 shadow-xl dark:border-neutral-800 dark:bg-neutral-900"
								align="end"
								sideOffset={6}
							>
								{#if groupableFields.length}
									<label class="block px-2 py-1.5 text-sm text-neutral-500">
										Group by
										<select bind:value={groupBy} class="mt-1 w-full rounded-md border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900">
											<option value={null}>None</option>
											{#each groupableFields as f (f.name)}
												<option value={f.name}>{f.label}</option>
											{/each}
										</select>
									</label>
								{/if}
								{#if canDelete(module.name)}
									<button
										type="button"
										onclick={() => (recycleBinOpen = true)}
										class="block w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
									>
										Recycle bin
									</button>
								{/if}
								<button
									type="button"
									disabled={exporting}
									onclick={exportCsv}
									class="block w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-neutral-100 disabled:opacity-50 dark:hover:bg-neutral-800"
								>
									{exporting ? 'Exporting…' : 'Export CSV'}
								</button>
								{#if canCreate(module.name)}
									<button
										type="button"
										disabled={importing}
										onclick={pickImportFile}
										class="block w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-neutral-100 disabled:opacity-50 dark:hover:bg-neutral-800"
									>
										{importing ? 'Importing…' : 'Import CSV'}
									</button>
								{/if}
							</DropdownMenu.Content>
						</DropdownMenu.Portal>
					</DropdownMenu.Root>
				</div>

			<div class="hidden items-center gap-2 sm:flex sm:gap-3">
				{#if canDelete(module.name)}
					<button
						type="button"
						onclick={() => (recycleBinOpen = true)}
						class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
					>
						Recycle bin
					</button>
				{/if}
				<button
					type="button"
					disabled={exporting}
					onclick={exportCsv}
					class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
				>
					{exporting ? 'Exporting…' : 'Export CSV'}
				</button>
				{#if canCreate(module.name)}
					<button
						type="button"
						disabled={importing}
						onclick={pickImportFile}
						class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
					>
						{importing ? 'Importing…' : 'Import CSV'}
					</button>
				{/if}
			</div>
			<input bind:this={fileInput} type="file" accept=".csv,text/csv" class="hidden" onchange={onImportFileSelected} />

			<a
				href={`/${module.name}/new`}
				class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium whitespace-nowrap text-white hover:bg-primary-700"
			>
				New {module.label}
			</a>
		</div>
	</div>

	{#if canDelete(module.name)}
		<RecycleBinDialog bind:open={recycleBinOpen} {module} />
	{/if}

	{#if records.length === 0}
		<EmptyState
			title={`No ${module.label.toLowerCase()} yet`}
			description={`Create the first ${module.label.toLowerCase()} record to get started.`}
			actionLabel={`New ${module.label}`}
			actionHref={`/${module.name}/new`}
		/>
	{:else if filteredRecords.length === 0}
		<EmptyState title="No matches" description={`Nothing matches "${search}".`} />
	{:else if isNarrow}
		<!-- Below `sm`, a wide table is either crushed unreadable or forces a
		     sideways scroll a thumb has to discover — a stacked card per
		     record (Fable's recommended pattern for a metadata-driven list
		     that can't know its own column count ahead of time) stays legible
		     at any width instead. Reuses the exact same `listFields`/
		     `formatterFor` the table columns are built from, so card and
		     table never show different data. -->
		<CardList {module} records={filteredRecords} {listFields} {formatterFor} onRowClick={openRecord} />
	{:else}
		<div class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
			<DataTable data={filteredRecords} {columns} {groupBy} expandable={hasChildren} subRow={hasChildren ? childrenPreview : undefined} onRowClick={openRecord} />
		</div>
	{/if}
</div>

{#snippet childrenPreview(record: RecordRow)}
	{#await loadChildren(record.id)}
		<span class="text-xs text-neutral-400">Loading…</span>
	{:then}
		{#if childRowsByParent[record.id]?.length}
			<ul class="space-y-1 text-xs text-neutral-600 dark:text-neutral-400">
				{#each childRowsByParent[record.id] as child (child.id)}
					<li>{Object.values(child).slice(1, 4).join(' · ')}</li>
				{/each}
			</ul>
		{:else}
			<span class="text-xs text-neutral-400">No related records</span>
		{/if}
	{/await}
{/snippet}
