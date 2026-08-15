<script lang="ts">
	import { api, type AgingRow } from '$lib/api';
	import { formatMoney } from '$lib/format';
	import { formatDateDisplay } from '$lib/date';
	import { todayISO } from '$lib/date';

	const BUCKETS = ['current', '1-30', '31-60', '61-90', '90+'] as const;
	const BUCKET_LABELS: Record<(typeof BUCKETS)[number], string> = {
		current: 'Current',
		'1-30': '1-30 days',
		'31-60': '31-60 days',
		'61-90': '61-90 days',
		'90+': '90+ days'
	};

	let group = $state<'AP' | 'AR'>('AP');
	let asOfDate = $state(todayISO());
	let rows = $state<AgingRow[] | null>(null);
	let running = $state(false);
	let error = $state<string | null>(null);

	async function run() {
		running = true;
		error = null;
		try {
			rows = await api.aging(group, asOfDate);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to run aging report';
			rows = null;
		} finally {
			running = false;
		}
	}

	const byParty = $derived.by(() => {
		if (!rows) return [];
		const groups = new Map<string, { label: string; buckets: Record<string, number>; total: number; items: AgingRow[] }>();
		for (const r of rows) {
			const key = r.party_id ?? '—';
			if (!groups.has(key)) {
				groups.set(key, { label: r.party_label ?? 'Unassigned', buckets: Object.fromEntries(BUCKETS.map((b) => [b, 0])), total: 0, items: [] });
			}
			const g = groups.get(key)!;
			g.buckets[r.bucket] += r.amount;
			g.total += r.amount;
			g.items.push(r);
		}
		return [...groups.values()].sort((a, b) => b.total - a.total);
	});

	const bucketTotals = $derived.by(() => {
		const totals = Object.fromEntries(BUCKETS.map((b) => [b, 0])) as Record<string, number>;
		for (const g of byParty) for (const b of BUCKETS) totals[b] += g.buckets[b];
		return totals;
	});

	const grandTotal = $derived(byParty.reduce((sum, g) => sum + g.total, 0));
</script>

<div class="space-y-4">
	<div class="flex flex-wrap items-end gap-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div>
			<span class="mb-1 block text-xs font-medium text-neutral-500">Type</span>
			<div class="flex rounded-md border border-neutral-200 dark:border-neutral-700">
				<button
					type="button"
					onclick={() => (group = 'AP')}
					class="px-3 py-1.5 text-sm {group === 'AP'
						? 'bg-primary-600 text-white'
						: 'text-neutral-600 hover:bg-neutral-50 dark:text-neutral-400 dark:hover:bg-neutral-800'} rounded-l-md"
				>
					AP (Vendor)
				</button>
				<button
					type="button"
					onclick={() => (group = 'AR')}
					class="px-3 py-1.5 text-sm {group === 'AR'
						? 'bg-primary-600 text-white'
						: 'text-neutral-600 hover:bg-neutral-50 dark:text-neutral-400 dark:hover:bg-neutral-800'} rounded-r-md"
				>
					AR (Customer)
				</button>
			</div>
		</div>
		<div>
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="aging-as-of">As of date</label>
			<input
				id="aging-as-of"
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
	</div>

	{#if error}
		<p class="text-sm text-red-600">{error}</p>
	{/if}

	{#if rows}
		<div class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
			<table class="w-full text-sm">
				<thead class="bg-neutral-50 dark:bg-neutral-900">
					<tr>
						<th class="px-3 py-2 text-left font-medium text-neutral-500">{group === 'AP' ? 'Vendor' : 'Customer'}</th>
						{#each BUCKETS as b (b)}
							<th class="px-3 py-2 text-right font-medium text-neutral-500">{BUCKET_LABELS[b]}</th>
						{/each}
						<th class="px-3 py-2 text-right font-medium text-neutral-500">Total</th>
					</tr>
				</thead>
				<tbody>
					{#if byParty.length === 0}
						<tr><td colspan={BUCKETS.length + 2} class="p-4 text-center text-sm text-neutral-400">No open items as of this date.</td></tr>
					{/if}
					{#each byParty as g (g.label)}
						<tr class="border-t border-neutral-100 dark:border-neutral-800">
							<td class="px-3 py-1.5 font-medium">{g.label}</td>
							{#each BUCKETS as b (b)}
								<td class="px-3 py-1.5 text-right {g.buckets[b] > 0 ? '' : 'text-neutral-300 dark:text-neutral-700'}">
									{g.buckets[b] > 0 ? formatMoney(g.buckets[b]) : '—'}
								</td>
							{/each}
							<td class="px-3 py-1.5 text-right font-semibold">{formatMoney(g.total)}</td>
						</tr>
					{/each}
				</tbody>
				{#if byParty.length > 0}
					<tfoot>
						<tr class="border-t-2 border-neutral-300 font-semibold dark:border-neutral-700">
							<td class="px-3 py-2">Total</td>
							{#each BUCKETS as b (b)}
								<td class="px-3 py-2 text-right">{formatMoney(bucketTotals[b])}</td>
							{/each}
							<td class="px-3 py-2 text-right">{formatMoney(grandTotal)}</td>
						</tr>
					</tfoot>
				{/if}
			</table>
		</div>

		{#if byParty.length > 0}
			<div class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
				<table class="w-full text-sm">
					<thead class="bg-neutral-50 dark:bg-neutral-900">
						<tr>
							<th class="px-3 py-2 text-left font-medium text-neutral-500">{group === 'AP' ? 'Vendor' : 'Customer'}</th>
							<th class="px-3 py-2 text-left font-medium text-neutral-500">Document</th>
							<th class="px-3 py-2 text-left font-medium text-neutral-500">Due Date</th>
							<th class="px-3 py-2 text-right font-medium text-neutral-500">Days Overdue</th>
							<th class="px-3 py-2 text-left font-medium text-neutral-500">Bucket</th>
							<th class="px-3 py-2 text-right font-medium text-neutral-500">Amount</th>
						</tr>
					</thead>
					<tbody>
						{#each byParty as g (g.label)}
							{#each g.items as item (item.record_id)}
								<tr class="border-t border-neutral-100 dark:border-neutral-800">
									<td class="px-3 py-1.5">{g.label}</td>
									<td class="px-3 py-1.5">{item.document_label}</td>
									<td class="px-3 py-1.5">{item.due_date ? formatDateDisplay(item.due_date) : '—'}</td>
									<td class="px-3 py-1.5 text-right">{item.days_overdue}</td>
									<td class="px-3 py-1.5">
										<span class="rounded-full bg-neutral-100 px-2 py-0.5 text-xs dark:bg-neutral-800">{BUCKET_LABELS[item.bucket]}</span>
									</td>
									<td class="px-3 py-1.5 text-right">{formatMoney(item.amount)}</td>
								</tr>
							{/each}
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>
