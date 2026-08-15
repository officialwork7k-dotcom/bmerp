<script lang="ts">
	import { goto } from '$app/navigation';
	import { Popover } from 'bits-ui';
	import { api } from '$lib/api';

	let open = $state(false);
	let query = $state('');
	let results = $state<{ module: string; module_label: string; id: string; label: string }[]>([]);
	let loading = $state(false);

	async function doSearch() {
		if (query.trim().length < 2) {
			results = [];
			return;
		}
		loading = true;
		try {
			const res = await api.globalSearch(query);
			results = res.results;
		} finally {
			loading = false;
		}
	}

	let debounceHandle: ReturnType<typeof setTimeout>;
	function onInput() {
		open = true;
		clearTimeout(debounceHandle);
		debounceHandle = setTimeout(doSearch, 200);
	}

	function select(r: { module: string; id: string }) {
		open = false;
		query = '';
		results = [];
		goto(`/${r.module}/${r.id}`);
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger class="hidden w-56 items-center rounded-md border border-neutral-200 px-2.5 py-1.5 text-left text-sm text-neutral-400 hover:border-neutral-300 sm:flex dark:border-neutral-700 dark:hover:border-neutral-600">
		<span>Search…</span>
	</Popover.Trigger>
	<Popover.Portal>
		<Popover.Content class="z-50 w-80 rounded-md border border-neutral-200 bg-white p-1 shadow-lg dark:border-neutral-700 dark:bg-neutral-900" align="start">
			<input
				bind:value={query}
				oninput={onInput}
				placeholder="Search across every module…"
				class="mb-1 h-8 w-full border-b border-neutral-200 px-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
			/>
			<div class="max-h-80 overflow-y-auto">
				{#if loading}
					<div class="px-2 py-1.5 text-sm text-neutral-500">Searching…</div>
				{:else if query.trim().length >= 2 && results.length === 0}
					<div class="px-2 py-1.5 text-sm text-neutral-500">No matches</div>
				{/if}
				{#each results as r (r.module + r.id)}
					<button
						type="button"
						class="block w-full truncate rounded px-2 py-1.5 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
						onclick={() => select(r)}
					>
						<span class="font-medium">{r.label}</span>
						<span class="ml-1.5 text-xs text-neutral-400">{r.module_label}</span>
					</button>
				{/each}
			</div>
		</Popover.Content>
	</Popover.Portal>
</Popover.Root>
