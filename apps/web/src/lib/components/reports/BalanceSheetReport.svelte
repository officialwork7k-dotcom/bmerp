<script lang="ts">
	import { api, type BalanceSheet } from '$lib/api';
	import { formatMoney } from '$lib/format';
	import { todayISO } from '$lib/date';

	let asOfDate = $state(todayISO());
	let result = $state<BalanceSheet | null>(null);
	let running = $state(false);
	let error = $state<string | null>(null);

	async function run() {
		running = true;
		error = null;
		try {
			result = await api.balanceSheet(asOfDate);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to run balance sheet';
			result = null;
		} finally {
			running = false;
		}
	}
</script>

<div class="space-y-4">
	<div class="flex flex-wrap items-end gap-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div>
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="bs-as-of">As of date</label>
			<input
				id="bs-as-of"
				type="date"
				bind:value={asOfDate}
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
		{#if result}
			<span class="ml-auto text-sm font-medium {result.balanced ? 'text-green-600' : 'text-red-600'}">
				{result.balanced ? '✓ Balanced' : '✗ Out of balance'}
			</span>
		{/if}
	</div>

	{#if error}
		<p class="text-sm text-red-600">{error}</p>
	{/if}

	{#if result}
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<div class="space-y-4">
				<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
					<p class="border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold dark:border-neutral-800 dark:bg-neutral-900">Liabilities</p>
					<table class="w-full text-sm">
						<tbody>
							{#each result.liabilities as row (row.account_code)}
								<tr class="border-t border-neutral-100 dark:border-neutral-800">
									<td class="px-3 py-1.5">{row.account_name}</td>
									<td class="px-3 py-1.5 text-right">{formatMoney(row.amount)}</td>
								</tr>
							{/each}
							{#if result.liabilities.length === 0}
								<tr><td colspan="2" class="p-4 text-center text-sm text-neutral-400">No liability activity.</td></tr>
							{/if}
						</tbody>
						<tfoot>
							<tr class="border-t-2 border-neutral-300 font-semibold dark:border-neutral-700">
								<td class="px-3 py-2">Total Liabilities</td>
								<td class="px-3 py-2 text-right">{formatMoney(result.total_liabilities)}</td>
							</tr>
						</tfoot>
					</table>
				</div>

				<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
					<p class="border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold dark:border-neutral-800 dark:bg-neutral-900">Equity</p>
					<table class="w-full text-sm">
						<tbody>
							{#each result.equity as row (row.account_code ?? row.account_name)}
								<tr class="border-t border-neutral-100 dark:border-neutral-800">
									<td class="px-3 py-1.5">{row.account_name}</td>
									<td class="px-3 py-1.5 text-right">{formatMoney(row.amount)}</td>
								</tr>
							{/each}
							{#if result.equity.length === 0}
								<tr><td colspan="2" class="p-4 text-center text-sm text-neutral-400">No equity activity.</td></tr>
							{/if}
						</tbody>
						<tfoot>
							<tr class="border-t-2 border-neutral-300 font-semibold dark:border-neutral-700">
								<td class="px-3 py-2">Total Equity</td>
								<td class="px-3 py-2 text-right">{formatMoney(result.total_equity)}</td>
							</tr>
						</tfoot>
					</table>
				</div>

				<div class="rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm font-semibold dark:border-neutral-700 dark:bg-neutral-900">
					<div class="flex justify-between">
						<span>Total Liabilities + Equity</span>
						<span>{formatMoney(result.total_liabilities_and_equity)}</span>
					</div>
				</div>
			</div>

			<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
				<p class="border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold dark:border-neutral-800 dark:bg-neutral-900">Assets</p>
				<table class="w-full text-sm">
					<tbody>
						{#each result.assets as row (row.account_code)}
							<tr class="border-t border-neutral-100 dark:border-neutral-800">
								<td class="px-3 py-1.5">{row.account_name}</td>
								<td class="px-3 py-1.5 text-right">{formatMoney(row.amount)}</td>
							</tr>
						{/each}
						{#if result.assets.length === 0}
							<tr><td colspan="2" class="p-4 text-center text-sm text-neutral-400">No asset activity.</td></tr>
						{/if}
					</tbody>
					<tfoot>
						<tr class="border-t-2 border-neutral-300 font-semibold dark:border-neutral-700">
							<td class="px-3 py-2">Total Assets</td>
							<td class="px-3 py-2 text-right">{formatMoney(result.total_assets)}</td>
						</tr>
					</tfoot>
				</table>
			</div>
		</div>
	{/if}
</div>
