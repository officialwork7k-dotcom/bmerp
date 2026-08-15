<script lang="ts">
	import { api, type IncomeStatement } from '$lib/api';
	import { formatMoney } from '$lib/format';
	import { todayISO } from '$lib/date';

	let dateFrom = $state(todayISO().slice(0, 4) + '-01-01');
	let dateTo = $state(todayISO());
	let result = $state<IncomeStatement | null>(null);
	let running = $state(false);
	let error = $state<string | null>(null);

	async function run() {
		running = true;
		error = null;
		try {
			result = await api.incomeStatement(dateFrom, dateTo);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to run income statement';
			result = null;
		} finally {
			running = false;
		}
	}
</script>

<div class="space-y-4">
	<div class="flex flex-wrap items-end gap-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div>
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="is-from">From</label>
			<input
				id="is-from"
				type="date"
				bind:value={dateFrom}
				class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
			/>
		</div>
		<div>
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="is-to">To</label>
			<input
				id="is-to"
				type="date"
				bind:value={dateTo}
				class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
			/>
		</div>
		<button
			type="button"
			disabled={running}
			onclick={run}
			class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
		>
			{running ? 'Running…' : 'Run'}
		</button>
	</div>

	{#if error}
		<p class="text-sm text-red-600">{error}</p>
	{/if}

	{#if result}
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
				<p class="border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold dark:border-neutral-800 dark:bg-neutral-900">Expenses</p>
				<table class="w-full text-sm">
					<tbody>
						{#each result.expenses as row (row.account_code)}
							<tr class="border-t border-neutral-100 dark:border-neutral-800">
								<td class="px-3 py-1.5">{row.account_name}</td>
								<td class="px-3 py-1.5 text-right">{formatMoney(row.amount)}</td>
							</tr>
						{/each}
						{#if result.expenses.length === 0}
							<tr><td colspan="2" class="p-4 text-center text-sm text-neutral-400">No expenses in this range.</td></tr>
						{/if}
					</tbody>
					<tfoot>
						<tr class="border-t-2 border-neutral-300 font-semibold dark:border-neutral-700">
							<td class="px-3 py-2">Total Expenses</td>
							<td class="px-3 py-2 text-right">{formatMoney(result.total_expenses)}</td>
						</tr>
					</tfoot>
				</table>
			</div>

			<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
				<p class="border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold dark:border-neutral-800 dark:bg-neutral-900">Revenue</p>
				<table class="w-full text-sm">
					<tbody>
						{#each result.revenue as row (row.account_code)}
							<tr class="border-t border-neutral-100 dark:border-neutral-800">
								<td class="px-3 py-1.5">{row.account_name}</td>
								<td class="px-3 py-1.5 text-right">{formatMoney(row.amount)}</td>
							</tr>
						{/each}
						{#if result.revenue.length === 0}
							<tr><td colspan="2" class="p-4 text-center text-sm text-neutral-400">No revenue in this range.</td></tr>
						{/if}
					</tbody>
					<tfoot>
						<tr class="border-t-2 border-neutral-300 font-semibold dark:border-neutral-700">
							<td class="px-3 py-2">Total Revenue</td>
							<td class="px-3 py-2 text-right">{formatMoney(result.total_revenue)}</td>
						</tr>
					</tfoot>
				</table>
			</div>
		</div>

		<div class="rounded-lg border border-neutral-300 bg-neutral-50 px-4 py-3 dark:border-neutral-700 dark:bg-neutral-900">
			<div class="flex justify-between text-base font-semibold {result.net_income >= 0 ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}">
				<span>Net Income</span>
				<span>{formatMoney(result.net_income)}</span>
			</div>
		</div>
	{/if}
</div>
