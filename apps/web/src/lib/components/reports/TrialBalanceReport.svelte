<script lang="ts">
	import { api, type TrialBalance } from '$lib/api';
	import { formatMoney } from '$lib/format';
	import { todayISO } from '$lib/date';

	let asOfDate = $state(todayISO());
	let result = $state<TrialBalance | null>(null);
	let running = $state(false);
	let error = $state<string | null>(null);

	async function run() {
		running = true;
		error = null;
		try {
			result = await api.trialBalance(asOfDate);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to run trial balance';
			result = null;
		} finally {
			running = false;
		}
	}
</script>

<div class="space-y-4">
	<div class="flex flex-wrap items-end gap-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div>
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="tb-as-of">As of date</label>
			<input
				id="tb-as-of"
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
		<div class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
			<table class="w-full text-sm">
				<thead class="bg-neutral-50 dark:bg-neutral-900">
					<tr>
						<th class="px-3 py-2 text-left font-medium text-neutral-500">Account Code</th>
						<th class="px-3 py-2 text-left font-medium text-neutral-500">Account Name</th>
						<th class="px-3 py-2 text-right font-medium text-neutral-500">Debit</th>
						<th class="px-3 py-2 text-right font-medium text-neutral-500">Credit</th>
					</tr>
				</thead>
				<tbody>
					{#if result.rows.length === 0}
						<tr><td colspan="4" class="p-4 text-center text-sm text-neutral-400">No posted journal activity as of this date.</td></tr>
					{/if}
					{#each result.rows as row (row.account_code)}
						<tr class="border-t border-neutral-100 dark:border-neutral-800">
							<td class="px-3 py-1.5 font-mono text-xs">{row.account_code}</td>
							<td class="px-3 py-1.5">{row.account_name}</td>
							<td class="px-3 py-1.5 text-right">{row.balance_debit > 0 ? formatMoney(row.balance_debit) : ''}</td>
							<td class="px-3 py-1.5 text-right">{row.balance_credit > 0 ? formatMoney(row.balance_credit) : ''}</td>
						</tr>
					{/each}
				</tbody>
				<tfoot>
					<tr class="border-t-2 border-neutral-300 font-semibold dark:border-neutral-700">
						<td colspan="2" class="px-3 py-2">Total</td>
						<td class="px-3 py-2 text-right">{formatMoney(result.total_debit)}</td>
						<td class="px-3 py-2 text-right">{formatMoney(result.total_credit)}</td>
					</tr>
				</tfoot>
			</table>
		</div>
	{/if}
</div>
