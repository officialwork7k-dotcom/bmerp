<script lang="ts">
	import { api, type ApprovalRequest } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// svelte-ignore state_referenced_locally -- one-time seed from load()
	let approvals = $state<ApprovalRequest[]>(data.approvals);
	// svelte-ignore state_referenced_locally
	let history = $state<ApprovalRequest[]>(data.history);
	let decidingId = $state<string | null>(null);

	async function decide(a: ApprovalRequest, approve: boolean) {
		decidingId = a.id;
		try {
			const decided = await api.decideApproval(a.id, approve);
			approvals = approvals.filter((x) => x.id !== a.id);
			history = [decided, ...history];
			toast.success(approve ? `Approved ${a.module} → ${a.to_status}` : `Rejected ${a.module} → ${a.to_status}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to record decision');
		} finally {
			decidingId = null;
		}
	}
</script>

<div class="mx-auto max-w-3xl space-y-6 p-6">
	<div>
		<h1 class="text-xl font-semibold">Approvals</h1>
		<p class="text-sm text-neutral-500">Pending status-transition requests awaiting an admin decision.</p>
	</div>

	{#if approvals.length === 0}
		<div class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-neutral-200 py-16 text-center dark:border-neutral-800">
			<p class="text-sm font-medium text-neutral-700 dark:text-neutral-300">Nothing pending</p>
			<p class="max-w-sm text-sm text-neutral-400">Requests made from a record's workflow panel show up here.</p>
		</div>
	{:else}
		<ul class="space-y-2">
			{#each approvals as a (a.id)}
				<li class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm font-medium">
								<a href={`/${a.module}/${a.record_id}`} class="hover:underline">{a.module}</a>
								: {a.from_status} → {a.to_status}
							</p>
							{#if a.note}<p class="mt-0.5 text-sm text-neutral-500">{a.note}</p>{/if}
							<p class="mt-0.5 text-xs text-neutral-400">Requested {new Date(a.created_at).toLocaleString()}</p>
						</div>
						<div class="flex items-center gap-2">
							<button
								type="button"
								disabled={decidingId === a.id}
								onclick={() => decide(a, false)}
								class="rounded-md border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-900 dark:hover:bg-red-950"
							>
								Reject
							</button>
							<button
								type="button"
								disabled={decidingId === a.id}
								onclick={() => decide(a, true)}
								class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
							>
								Approve
							</button>
						</div>
					</div>
				</li>
			{/each}
		</ul>
	{/if}

	<div>
		<h2 class="mb-2 text-sm font-semibold text-neutral-500">Decided</h2>
		{#if history.length === 0}
			<p class="text-sm text-neutral-400">No decisions recorded yet.</p>
		{:else}
			<ul class="space-y-2">
				{#each history as a (a.id)}
					<li class="rounded-lg border border-neutral-200 bg-white p-3 text-sm dark:border-neutral-800 dark:bg-neutral-900">
						<div class="flex items-center justify-between gap-2">
							<a href={`/${a.module}/${a.record_id}`} class="min-w-0 truncate hover:underline">
								{a.module}: {a.from_status} → {a.to_status}
							</a>
							<span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium {a.status === 'approved'
								? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
								: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'}"
							>
								{a.status}
							</span>
						</div>
						{#if a.note}<p class="mt-0.5 text-neutral-500">{a.note}</p>{/if}
						{#if a.decided_at}<p class="mt-0.5 text-xs text-neutral-400">Decided {new Date(a.decided_at).toLocaleString()}</p>{/if}
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>
