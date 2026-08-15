<script lang="ts">
	import { api, type SubledgerReconciliation } from '$lib/api';
	import { formatMoney } from '$lib/format';
	import { todayISO } from '$lib/date';

	let asOfDate = $state(todayISO());
	let result = $state<SubledgerReconciliation | null>(null);
	let running = $state(false);
	let error = $state<string | null>(null);

	async function run() {
		running = true;
		error = null;
		try {
			result = await api.subledgerReconciliation(asOfDate);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to run subledger reconciliation';
			result = null;
		} finally {
			running = false;
		}
	}
</script>

<div class="space-y-4">
	<div class="flex flex-wrap items-end gap-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div>
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="sr-as-of">As of date</label>
			<input
				id="sr-as-of"
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
			<span class="ml-auto text-sm font-medium {result.all_matched ? 'text-green-600' : 'text-red-600'}">
				{result.all_matched ? '✓ All reconciliation accounts match their subledger' : '✗ Variance found — see below'}
			</span>
		{/if}
	</div>

	<p class="text-sm text-neutral-500">
		For every GL account tagged as a reconciliation account, compares its trial-balance balance against the total
		obtained by replaying every posting rule that resolves to it, across every currently-posted document — using
		the same resolution logic the posting engine uses. A nonzero variance means a posted document's data was
		altered after posting, or something is posting to the account outside the configured subledger path.
	</p>

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
						<th class="px-3 py-2 text-left font-medium text-neutral-500">Sources</th>
						<th class="px-3 py-2 text-right font-medium text-neutral-500">GL Balance</th>
						<th class="px-3 py-2 text-right font-medium text-neutral-500">Subledger Balance</th>
						<th class="px-3 py-2 text-right font-medium text-neutral-500">Variance</th>
						<th class="px-3 py-2 text-center font-medium text-neutral-500">Status</th>
					</tr>
				</thead>
				<tbody>
					{#if result.accounts.length === 0}
						<tr><td colspan="7" class="p-4 text-center text-sm text-neutral-400">No accounts are tagged as reconciliation accounts. Tag one in Chart of Accounts.</td></tr>
					{/if}
					{#each result.accounts as row (row.account_code)}
						<tr class="border-t border-neutral-100 dark:border-neutral-800 {row.matched ? '' : 'bg-red-50 dark:bg-red-950/30'}">
							<td class="px-3 py-1.5 font-mono text-xs">{row.account_code}</td>
							<td class="px-3 py-1.5">{row.account_name}</td>
							<td class="px-3 py-1.5 text-xs text-neutral-500">
								{Object.entries(row.sources).map(([m, n]) => `${m} (${n})`).join(', ') || '—'}
							</td>
							<td class="px-3 py-1.5 text-right">{formatMoney(row.gl_balance)}</td>
							<td class="px-3 py-1.5 text-right">{formatMoney(row.subledger_balance)}</td>
							<td class="px-3 py-1.5 text-right {row.matched ? '' : 'font-semibold text-red-600'}">{formatMoney(row.variance)}</td>
							<td class="px-3 py-1.5 text-center">
								{#if row.matched}
									<span class="text-green-600">✓</span>
								{:else}
									<span class="text-red-600">✗</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
