<script lang="ts" generics="TData extends { id: string }">
	import {
		getCoreRowModel,
		getExpandedRowModel,
		getGroupedRowModel,
		getSortedRowModel,
		type ColumnDef,
		type SortingState
	} from '@tanstack/table-core';
	import type { Snippet } from 'svelte';
	import { createSvelteTable } from './create-svelte-table.svelte';

	let {
		data,
		columns,
		groupBy = null,
		expandable = false,
		subRow,
		onRowClick
	}: {
		data: TData[];
		columns: ColumnDef<TData, unknown>[];
		/** One-way: DataTable never writes this back. Grouping is derived
		 * from it via a `state.grouping` getter, not synced through an
		 * effect — see create-svelte-table.svelte.ts for why that matters. */
		groupBy?: string | null;
		expandable?: boolean;
		subRow?: Snippet<[TData]>;
		onRowClick?: (row: TData) => void;
	} = $props();

	// Called once and reused, not invoked fresh on every render: each call to
	// getCoreRowModel()/getGroupedRowModel()/getExpandedRowModel() returns a
	// new closure, so rebuilding them every time makes table options
	// "different" by reference even when nothing meaningful changed.
	const coreRowModel = getCoreRowModel<TData>();
	const groupedRowModel = getGroupedRowModel<TData>();
	const expandedRowModel = getExpandedRowModel<TData>();
	const sortedRowModel = getSortedRowModel<TData>();
	const getRowId = (row: TData) => row.id;

	let sorting = $state<SortingState>([]);

	const table = createSvelteTable({
		get data() {
			return data;
		},
		get columns() {
			return columns;
		},
		state: {
			get grouping() {
				return groupBy ? [groupBy] : [];
			},
			get sorting() {
				return sorting;
			}
		},
		onSortingChange: (updater) => {
			sorting = typeof updater === 'function' ? updater(sorting) : updater;
		},
		getCoreRowModel: coreRowModel,
		getGroupedRowModel: groupedRowModel,
		getExpandedRowModel: expandedRowModel,
		getSortedRowModel: sortedRowModel,
		getRowId,
		// Without this, toggleExpanded() is a silent no-op: TanStack's
		// default expandability check looks for real `subRows` data, which
		// we don't have — the sub-row content here is our own `subRow`
		// snippet, not TanStack's subRow rendering.
		getRowCanExpand: () => expandable,
		groupedColumnMode: false,
		// The actual root cause of the earlier infinite-loop bug: this
		// defaults to on whenever getExpandedRowModel is provided, and
		// resets `expanded` to a fresh {} via a queued microtask whenever it
		// detects data/grouping changes — feeding a new object identity back
		// through onExpandedChange on every row-model computation. Expansion
		// reset, if ever needed, should be an explicit call
		// (table.resetExpanded()) at the point the intent actually lives,
		// not an implicit background loop.
		autoResetExpanded: false
	});
</script>

<div class="max-h-[70vh] overflow-auto">
	<table class="w-full border-collapse text-sm">
		<thead>
			<tr class="text-left">
				{#if expandable}<th class="sticky top-0 z-10 w-8 border-b border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900"></th>{/if}
				{#each table.getHeaderGroups()[0]?.headers ?? [] as header (header.id)}
					{@const sort = header.column.getIsSorted()}
					<th
						class="sticky top-0 z-10 border-b border-neutral-200 bg-white px-3 py-2 font-medium text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900 {header.column.getCanSort()
							? 'cursor-pointer select-none hover:text-neutral-700 dark:hover:text-neutral-300'
							: ''}"
						onclick={header.column.getCanSort() ? header.column.getToggleSortingHandler() : undefined}
						aria-sort={sort === 'asc' ? 'ascending' : sort === 'desc' ? 'descending' : 'none'}
					>
						<span class="inline-flex items-center gap-1">
							{typeof header.column.columnDef.header === 'string' ? header.column.columnDef.header : header.id}
							{#if sort === 'asc'}<span class="text-neutral-400">▲</span>
							{:else if sort === 'desc'}<span class="text-neutral-400">▼</span>{/if}
						</span>
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each table.getRowModel().rows as row, i (row.id)}
				{#if row.getIsGrouped()}
					<tr class="bg-neutral-50 dark:bg-neutral-900">
						<td colspan={columns.length + (expandable ? 1 : 0)} class="px-3 py-2 font-medium">
							<button type="button" onclick={() => row.toggleExpanded()} class="mr-1">
								{row.getIsExpanded() ? '▾' : '▸'}
							</button>
							{String(row.getValue(row.groupingColumnId ?? ''))}
							<span class="ml-2 text-neutral-400">({row.subRows.length})</span>
						</td>
					</tr>
				{:else}
					<tr
						class="border-b border-neutral-100 dark:border-neutral-900 {i % 2 === 1
							? 'bg-neutral-50/60 dark:bg-neutral-900/40'
							: ''} {onRowClick ? 'cursor-pointer hover:bg-primary-50/60 dark:hover:bg-primary-950/30' : ''}"
						onclick={onRowClick ? () => onRowClick(row.original) : undefined}
					>
						{#if expandable}
							<td class="px-2">
								<button
									type="button"
									onclick={(e) => {
										e.stopPropagation();
										row.toggleExpanded();
									}}
								>
									{row.getIsExpanded() ? '▾' : '▸'}
								</button>
							</td>
						{/if}
						{#each row.getVisibleCells() as cell (cell.id)}
							{@const meta = cell.column.columnDef.meta as { format?: (v: unknown) => string; align?: 'right' } | undefined}
							<td class="px-3 py-2 {meta?.align === 'right' ? 'text-right tabular-nums' : ''}">
								{meta?.format ? meta.format(cell.getValue()) : String(cell.getValue() ?? '')}
							</td>
						{/each}
					</tr>
					{#if expandable && row.getIsExpanded() && subRow}
						<tr>
							<td colspan={columns.length + 1} class="bg-neutral-50 px-6 py-3 dark:bg-neutral-950">
								{@render subRow(row.original)}
							</td>
						</tr>
					{/if}
				{/if}
			{/each}
		</tbody>
	</table>
</div>
