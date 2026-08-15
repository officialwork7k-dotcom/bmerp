<script lang="ts">
	import { formatMoney } from '$lib/format';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	function findLine(lines: { account_name: string; amount: number }[], nameContains: string): number {
		return lines.find((l) => l.account_name.toLowerCase().includes(nameContains.toLowerCase()))?.amount ?? 0;
	}

	const cash = $derived(findLine(data.balanceSheet.assets, 'cash'));
	const ar = $derived(findLine(data.balanceSheet.assets, 'receivable'));
	const ap = $derived(findLine(data.balanceSheet.liabilities, 'payable') - findLine(data.balanceSheet.liabilities, 'clearing') - findLine(data.balanceSheet.liabilities, 'freight'));

	const apOverdue = $derived(data.apAging.filter((r) => r.bucket !== 'current').reduce((s, r) => s + r.amount, 0));
	const arOverdue = $derived(data.arAging.filter((r) => r.bucket !== 'current').reduce((s, r) => s + r.amount, 0));

	const cards = $derived([
		{ label: 'Cash Position', value: cash, tone: 'neutral' as const },
		{ label: 'Accounts Receivable', value: ar, tone: 'neutral' as const },
		{ label: 'Accounts Payable', value: ap, tone: 'neutral' as const },
		{ label: 'Net Income (YTD)', value: data.ytdIncome.net_income, tone: data.ytdIncome.net_income >= 0 ? ('good' as const) : ('bad' as const) },
		{ label: 'Net Income (MTD)', value: data.mtdIncome.net_income, tone: data.mtdIncome.net_income >= 0 ? ('good' as const) : ('bad' as const) },
		{ label: 'AR Overdue', value: arOverdue, tone: arOverdue > 0 ? ('bad' as const) : ('good' as const) },
		{ label: 'AP Overdue', value: apOverdue, tone: apOverdue > 0 ? ('bad' as const) : ('good' as const) }
	]);
</script>

<div class="mx-auto max-w-6xl space-y-6 p-6">
	<div>
		<h1 class="text-xl font-semibold">Dashboard</h1>
		<p class="text-sm text-neutral-500">Financial position as of today, pulled live from posted journal entries.</p>
	</div>

	<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
		{#each cards as card (card.label)}
			<div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
				<p class="text-xs font-medium uppercase tracking-wide text-neutral-400">{card.label}</p>
				<p
					class="mt-1 text-lg font-semibold {card.tone === 'good'
						? 'text-green-600'
						: card.tone === 'bad'
							? 'text-red-600'
							: 'text-neutral-900 dark:text-neutral-100'}"
				>
					{formatMoney(card.value)}
				</p>
			</div>
		{/each}
	</div>

	<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
		<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
			<div class="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-3 py-2 dark:border-neutral-800 dark:bg-neutral-900">
				<p class="text-sm font-semibold">Pending Approvals</p>
				<a href="/admin/approvals" class="text-xs text-primary-600 hover:underline">View all</a>
			</div>
			{#if data.approvals.length === 0}
				<p class="p-4 text-sm text-neutral-400">Nothing pending.</p>
			{:else}
				<ul class="divide-y divide-neutral-100 text-sm dark:divide-neutral-800">
					{#each data.approvals.slice(0, 8) as a (a.id)}
						<li class="px-3 py-2">
							<span class="font-medium">{a.module.replace(/_/g, ' ')}</span>
							<span class="text-neutral-400"> — {a.from_status} → {a.to_status}</span>
						</li>
					{/each}
				</ul>
				{#if data.approvals.length > 8}
					<p class="border-t border-neutral-100 px-3 py-2 text-xs text-neutral-400 dark:border-neutral-800">+{data.approvals.length - 8} more</p>
				{/if}
			{/if}
		</div>

		<div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
			<div class="flex items-center justify-between border-b border-neutral-200 bg-neutral-50 px-3 py-2 dark:border-neutral-800 dark:bg-neutral-900">
				<p class="text-sm font-semibold">Quick Links</p>
			</div>
			<div class="grid grid-cols-2 gap-2 p-3 text-sm">
				<a href="/reports" class="rounded-md border border-neutral-200 px-3 py-2 hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800">Reports</a>
				<a href="/period-close" class="rounded-md border border-neutral-200 px-3 py-2 hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800">Period-End Close</a>
				<a href="/purchase_orders" class="rounded-md border border-neutral-200 px-3 py-2 hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800">Purchase Orders</a>
				<a href="/sales_orders" class="rounded-md border border-neutral-200 px-3 py-2 hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800">Sales Orders</a>
			</div>
		</div>
	</div>
</div>
