<script lang="ts">
	import { api } from '$lib/api';

	let { module, recordId }: { module: string; recordId: string } = $props();

	type Entry = { id: string; action: string; changes: Record<string, unknown> | null; actor: string; created_at: string };

	let open = $state(false);
	let loading = $state(false);
	let loaded = $state(false);
	let entries = $state<Entry[]>([]);
	let loadError = $state<string | null>(null);

	async function toggle() {
		open = !open;
		if (open && !loaded) {
			loading = true;
			loadError = null;
			try {
				entries = await api.getRecordHistory(module, recordId);
				loaded = true;
			} catch (e) {
				loadError = e instanceof Error ? e.message : 'Failed to load history';
			} finally {
				loading = false;
			}
		}
	}

	function formatValue(v: unknown): string {
		if (v === null || v === undefined) return '—';
		if (typeof v === 'object') return JSON.stringify(v);
		return String(v);
	}

	function fieldDiffs(changes: Record<string, unknown>): { field: string; old: unknown; new: unknown }[] {
		// A transition's `changes` carries the same {old,new} shape as an
		// update's, plus a `note` string alongside it (not itself a field
		// diff) — skip that one key rather than rendering "note: null → …".
		return Object.entries(changes)
			.filter(([field, v]) => field !== 'note' && v && typeof v === 'object' && ('old' in v || 'new' in v))
			.map(([field, v]) => {
				const d = v as { old?: unknown; new?: unknown };
				return { field, old: d?.old, new: d?.new };
			});
	}

	function actionLabel(action: string): string {
		switch (action) {
			case 'approval_requested':
				return 'Requested approval';
			case 'approval_rejected':
				return 'Rejected';
			default:
				return action;
		}
	}
</script>

<div class="rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
	<button
		type="button"
		onclick={toggle}
		class="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-neutral-500"
	>
		History
		<span class="text-xs font-normal text-neutral-400">{open ? '▲' : '▼'}</span>
	</button>

	{#if open}
		<div class="border-t border-neutral-200 px-4 py-3 dark:border-neutral-800">
			{#if loading}
				<p class="text-sm text-neutral-400">Loading…</p>
			{:else if loadError}
				<p class="text-sm text-red-600">{loadError}</p>
			{:else if entries.length === 0}
				<p class="text-sm text-neutral-400">No changes recorded yet.</p>
			{:else}
				<ol class="space-y-3">
					{#each entries as entry (entry.id)}
						<li class="border-l-2 border-neutral-200 pl-3 text-sm dark:border-neutral-800">
							<div class="flex items-center gap-2 text-neutral-500">
								<span class="font-medium capitalize text-neutral-700 dark:text-neutral-300">{actionLabel(entry.action)}</span>
								<span>by {entry.actor}</span>
								<span>·</span>
								<span>{new Date(entry.created_at).toLocaleString()}</span>
							</div>
							{#if (entry.action === 'update' || entry.action === 'transition') && entry.changes}
								<ul class="mt-1 space-y-0.5">
									{#each fieldDiffs(entry.changes) as fd (fd.field)}
										<li class="text-neutral-600 dark:text-neutral-400">
											<span class="font-medium">{fd.field}</span>:
											<span class="text-red-500 line-through">{formatValue(fd.old)}</span>
											→
											<span class="text-green-600 dark:text-green-400">{formatValue(fd.new)}</span>
										</li>
									{/each}
								</ul>
								{#if typeof entry.changes.note === 'string' && entry.changes.note}
									<p class="mt-0.5 text-neutral-500">"{entry.changes.note}"</p>
								{/if}
							{:else if entry.action === 'create'}
								<p class="mt-1 text-neutral-500">Record created</p>
							{:else if entry.action === 'delete'}
								<p class="mt-1 text-neutral-500">Record deleted</p>
							{:else if entry.action === 'approval_requested' && entry.changes}
								<p class="mt-1 text-neutral-500">
									Requested move to <span class="font-medium">{String(entry.changes.to_status)}</span>
									{#if typeof entry.changes.note === 'string' && entry.changes.note}— "{entry.changes.note}"{/if}
								</p>
							{:else if entry.action === 'approval_rejected' && entry.changes}
								<p class="mt-1 text-neutral-500">
									Rejected the move to <span class="font-medium">{String(entry.changes.to_status)}</span>
									{#if typeof entry.changes.note === 'string' && entry.changes.note}— "{entry.changes.note}"{/if}
								</p>
							{/if}
						</li>
					{/each}
				</ol>
			{/if}
		</div>
	{/if}
</div>
