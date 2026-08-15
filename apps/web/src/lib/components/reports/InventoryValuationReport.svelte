<script lang="ts">
	import { api, type InventoryValuation, type InventoryValuationRow, type StockMovement } from '$lib/api';
	import { formatMoney, formatDecimal } from '$lib/format';
	import { formatDateDisplay } from '$lib/date';

	let result = $state<InventoryValuation | null>(null);
	let running = $state(false);
	let error = $state<string | null>(null);

	let selected = $state<InventoryValuationRow | null>(null);
	let movements = $state<StockMovement[] | null>(null);
	let movementsLoading = $state(false);

	async function run() {
		running = true;
		error = null;
		try {
			result = await api.inventoryValuation();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to run inventory valuation';
			result = null;
		} finally {
			running = false;
		}
	}

	async function showMovements(row: InventoryValuationRow) {
		selected = row;
		movements = null;
		movementsLoading = true;
		try {
			movements = await api.stockMovements(row.item_module, row.item_id);
		} finally {
			movementsLoading = false;
		}
	}

	$effect(() => {
		run();
	});
</script>

<div class="space-y-4">
	<div class="flex flex-wrap items-center gap-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<button
			type="button"
			disabled={running}
			onclick={run}
			class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
		>
			{running ? 'Running…' : 'Refresh'}
		</button>
		{#if result}
			<span class="ml-auto text-sm font-medium">Total value: {formatMoney(result.total_value)}</span>
		{/if}
	</div>

	{#if error}
		<p class="text-sm text-red-600">{error}</p>
	{/if}

	{#if result}
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_20rem]">
			<div class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
				<table class="w-full text-sm">
					<thead class="bg-neutral-50 dark:bg-neutral-900">
						<tr>
							<th class="px-3 py-2 text-left font-medium text-neutral-500">Item</th>
							<th class="px-3 py-2 text-right font-medium text-neutral-500">On Hand Qty</th>
							<th class="px-3 py-2 text-right font-medium text-neutral-500">Avg Cost</th>
							<th class="px-3 py-2 text-right font-medium text-neutral-500">Value</th>
						</tr>
					</thead>
					<tbody>
						{#if result.rows.length === 0}
							<tr><td colspan="4" class="p-4 text-center text-sm text-neutral-400">No stock on hand.</td></tr>
						{/if}
						{#each result.rows as row (row.item_module + row.item_id)}
							<tr
								class="cursor-pointer border-t border-neutral-100 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-800 {selected === row ? 'bg-primary-50 dark:bg-primary-950' : ''}"
								onclick={() => showMovements(row)}
							>
								<td class="px-3 py-1.5">{row.item_label}</td>
								<td class="px-3 py-1.5 text-right">{formatDecimal(row.on_hand_qty)}</td>
								<td class="px-3 py-1.5 text-right">{formatMoney(row.avg_cost)}</td>
								<td class="px-3 py-1.5 text-right">{formatMoney(row.value)}</td>
							</tr>
						{/each}
					</tbody>
					{#if result.rows.length > 0}
						<tfoot>
							<tr class="border-t-2 border-neutral-300 font-semibold dark:border-neutral-700">
								<td colspan="3" class="px-3 py-2">Total</td>
								<td class="px-3 py-2 text-right">{formatMoney(result.total_value)}</td>
							</tr>
						</tfoot>
					{/if}
				</table>
			</div>

			<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
				<p class="border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold dark:border-neutral-800 dark:bg-neutral-900">
					{selected ? `Movements — ${selected.item_label}` : 'Select an item'}
				</p>
				{#if movementsLoading}
					<p class="p-3 text-sm text-neutral-400">Loading…</p>
				{:else if movements}
					<ul class="max-h-96 divide-y divide-neutral-100 overflow-y-auto text-xs dark:divide-neutral-800">
						{#each movements as m (m.id)}
							<li class="px-3 py-2">
								<div class="flex justify-between">
									<span class="font-medium {m.movement_type === 'receipt' ? 'text-green-600' : 'text-red-600'}">
										{m.movement_type === 'receipt' ? '+' : '−'}{formatDecimal(Math.abs(m.quantity))}
									</span>
									<span class="text-neutral-400">{formatDateDisplay(m.created_at.slice(0, 10))}</span>
								</div>
								<div class="text-neutral-500">
									Balance: {formatDecimal(m.resulting_qty)} @ {formatMoney(m.resulting_avg_cost)}
									{#if m.document_module}
										· {m.document_module}
									{/if}
								</div>
							</li>
						{/each}
						{#if movements.length === 0}
							<li class="px-3 py-3 text-center text-neutral-400">No movements.</li>
						{/if}
					</ul>
				{:else}
					<p class="p-3 text-sm text-neutral-400">Click a row to see its movement history.</p>
				{/if}
			</div>
		</div>
	{/if}
</div>
