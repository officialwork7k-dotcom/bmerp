<script lang="ts">
	import { Dialog } from 'bits-ui';
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import { displayName } from '$lib/types';
	import type { ModuleMetadata, RecordRow } from '$lib/types';

	let { open = $bindable(false), module }: { open?: boolean; module: ModuleMetadata } = $props();

	let loading = $state(false);
	let loaded = $state(false);
	let rows = $state<RecordRow[]>([]);
	let restoringId = $state<string | null>(null);

	async function load() {
		loading = true;
		try {
			rows = await api.listDeleted(module.name);
			loaded = true;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to load recycle bin');
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (open && !loaded) load();
	});

	async function restore(row: RecordRow) {
		restoringId = row.id;
		try {
			await api.restoreRecord(module.name, row.id);
			rows = rows.filter((r) => r.id !== row.id);
			toast.success(`${module.label} restored`);
			await invalidateAll();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Restore failed');
		} finally {
			restoringId = null;
		}
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-50 bg-black/40" />
		<Dialog.Content
			class="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border border-neutral-200 bg-white p-5 shadow-xl dark:border-neutral-800 dark:bg-neutral-900"
		>
			<Dialog.Title class="text-base font-semibold">{module.label} — Recycle Bin</Dialog.Title>
			<Dialog.Description class="mt-1 text-sm text-neutral-500">
				Deleted records, most recent first. Restoring puts a record back exactly as it was.
			</Dialog.Description>

			<div class="mt-4 max-h-80 overflow-y-auto">
				{#if loading}
					<p class="py-6 text-center text-sm text-neutral-400">Loading…</p>
				{:else if rows.length === 0}
					<p class="py-6 text-center text-sm text-neutral-400">Nothing in the recycle bin.</p>
				{:else}
					<ul class="divide-y divide-neutral-100 dark:divide-neutral-800">
						{#each rows as row (row.id)}
							<li class="flex items-center justify-between py-2">
								<span class="text-sm">{displayName(row, row.id)}</span>
								<button
									type="button"
									disabled={restoringId === row.id}
									onclick={() => restore(row)}
									class="rounded-md border border-neutral-300 px-2.5 py-1 text-xs font-medium hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
								>
									{restoringId === row.id ? 'Restoring…' : 'Restore'}
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="mt-4 flex justify-end">
				<Dialog.Close class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800">
					Close
				</Dialog.Close>
			</div>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
