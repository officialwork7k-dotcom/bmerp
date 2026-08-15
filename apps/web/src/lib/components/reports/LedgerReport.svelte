<script lang="ts">
	import { Popover } from 'bits-ui';
	import { api, type PartyLedger } from '$lib/api';
	import { createSearchController, type LookupOption } from '$lib/lookup';
	import { formatMoney } from '$lib/format';
	import { formatDateDisplay, todayISO } from '$lib/date';

	let group = $state<'AP' | 'AR'>('AP');
	let dateFrom = $state(todayISO().slice(0, 4) + '-01-01');
	let dateTo = $state(todayISO());
	let result = $state<PartyLedger | null>(null);
	let running = $state(false);
	let error = $state<string | null>(null);

	// --- party picker (vendor for AP, customer for AR) ---
	let partyOpen = $state(false);
	let partySearch = $state('');
	let partyOptions = $state<LookupOption[]>([]);
	let partyLoading = $state(false);
	let selectedParty = $state<LookupOption | null>(null);
	const partyModule = $derived(group === 'AP' ? 'vendors' : 'customers');

	const searchController = createSearchController(200);
	$effect(() => {
		if (!partyOpen) return;
		searchController.run(
			partyModule,
			partySearch,
			(results) => (partyOptions = results),
			(l) => (partyLoading = l)
		);
	});
	$effect(() => () => searchController.dispose());

	function switchGroup(g: 'AP' | 'AR') {
		group = g;
		selectedParty = null;
		result = null;
	}

	async function run() {
		if (!selectedParty) return;
		running = true;
		error = null;
		try {
			result = await api.ledger(group, selectedParty.value, dateFrom, dateTo);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to run ledger';
			result = null;
		} finally {
			running = false;
		}
	}
</script>

<div class="space-y-4">
	<div class="flex flex-wrap items-end gap-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div>
			<span class="mb-1 block text-xs font-medium text-neutral-500">Type</span>
			<div class="flex rounded-md border border-neutral-200 dark:border-neutral-700">
				<button
					type="button"
					onclick={() => switchGroup('AP')}
					class="px-3 py-1.5 text-sm {group === 'AP'
						? 'bg-primary-600 text-white'
						: 'text-neutral-600 hover:bg-neutral-50 dark:text-neutral-400 dark:hover:bg-neutral-800'} rounded-l-md"
				>
					Vendor Ledger
				</button>
				<button
					type="button"
					onclick={() => switchGroup('AR')}
					class="px-3 py-1.5 text-sm {group === 'AR'
						? 'bg-primary-600 text-white'
						: 'text-neutral-600 hover:bg-neutral-50 dark:text-neutral-400 dark:hover:bg-neutral-800'} rounded-r-md"
				>
					Customer Ledger
				</button>
			</div>
		</div>

		<div>
			<span class="mb-1 block text-xs font-medium text-neutral-500">{group === 'AP' ? 'Vendor' : 'Customer'}</span>
			<Popover.Root bind:open={partyOpen}>
				<Popover.Trigger
					class="flex h-9 w-56 items-center justify-between rounded-md border border-neutral-300 bg-white px-3 text-left text-sm dark:border-neutral-700 dark:bg-neutral-900"
				>
					<span class="truncate">{selectedParty?.label ?? 'Select…'}</span>
				</Popover.Trigger>
				<Popover.Portal>
					<Popover.Content class="z-50 w-72 rounded-md border border-neutral-200 bg-white p-1 shadow-lg dark:border-neutral-700 dark:bg-neutral-900">
						<input
							class="mb-1 h-8 w-full border-b border-neutral-200 px-2 text-sm outline-none dark:border-neutral-700"
							placeholder="Search…"
							bind:value={partySearch}
						/>
						<div class="max-h-64 overflow-y-auto">
							{#if partyLoading}
								<div class="px-2 py-1.5 text-sm text-neutral-500">Loading…</div>
							{:else if partyOptions.length === 0}
								<div class="px-2 py-1.5 text-sm text-neutral-500">No matches</div>
							{/if}
							{#each partyOptions as opt (opt.value)}
								<button
									type="button"
									class="block w-full truncate rounded px-2 py-1.5 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
									onclick={() => {
										selectedParty = opt;
										partyOpen = false;
									}}
								>
									{opt.label}
								</button>
							{/each}
						</div>
					</Popover.Content>
				</Popover.Portal>
			</Popover.Root>
		</div>

		<div>
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="ledger-from">From</label>
			<input
				id="ledger-from"
				type="date"
				bind:value={dateFrom}
				class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
			/>
		</div>
		<div>
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="ledger-to">To</label>
			<input
				id="ledger-to"
				type="date"
				bind:value={dateTo}
				class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
			/>
		</div>
		<button
			type="button"
			disabled={running || !selectedParty}
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
		<div class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
			<table class="w-full text-sm">
				<thead class="bg-neutral-50 dark:bg-neutral-900">
					<tr>
						<th class="px-3 py-2 text-left font-medium text-neutral-500">Date</th>
						<th class="px-3 py-2 text-left font-medium text-neutral-500">Document</th>
						<th class="px-3 py-2 text-right font-medium text-neutral-500">Amount</th>
						<th class="px-3 py-2 text-right font-medium text-neutral-500">Balance</th>
					</tr>
				</thead>
				<tbody>
					<tr class="border-t border-neutral-100 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900/50">
						<td class="px-3 py-1.5" colspan="3">Opening balance</td>
						<td class="px-3 py-1.5 text-right font-medium">{formatMoney(result.opening_balance)}</td>
					</tr>
					{#if result.entries.length === 0}
						<tr><td colspan="4" class="p-4 text-center text-sm text-neutral-400">No transactions in this date range.</td></tr>
					{/if}
					{#each result.entries as e (e.record_id)}
						<tr class="border-t border-neutral-100 dark:border-neutral-800">
							<td class="px-3 py-1.5">{formatDateDisplay(e.date)}</td>
							<td class="px-3 py-1.5">{e.document_label}</td>
							<td class="px-3 py-1.5 text-right">{formatMoney(e.amount)}</td>
							<td class="px-3 py-1.5 text-right">{formatMoney(e.balance)}</td>
						</tr>
					{/each}
				</tbody>
				<tfoot>
					<tr class="border-t-2 border-neutral-300 font-semibold dark:border-neutral-700">
						<td class="px-3 py-2" colspan="3">Closing balance</td>
						<td class="px-3 py-2 text-right">{formatMoney(result.closing_balance)}</td>
					</tr>
				</tfoot>
			</table>
		</div>
	{/if}
</div>
