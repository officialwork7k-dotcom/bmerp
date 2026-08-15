<script lang="ts">
	import { api, type ApiToken } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import { formatDateDisplay } from '$lib/date';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// svelte-ignore state_referenced_locally -- one-time seed from load()
	let tokens = $state<ApiToken[]>(data.tokens);
	let name = $state('');
	let creating = $state(false);
	let revealedToken = $state<string | null>(null);

	async function create() {
		if (!name.trim()) {
			toast.error('Give the token a name first');
			return;
		}
		creating = true;
		try {
			const created = await api.createToken(name.trim());
			tokens = [...tokens, { id: created.id, name: created.name, last_used_at: null }];
			revealedToken = created.token;
			name = '';
			toast.success('Token created');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to create token');
		} finally {
			creating = false;
		}
	}

	async function revoke(t: ApiToken) {
		try {
			await api.revokeToken(t.id);
			tokens = tokens.filter((x) => x.id !== t.id);
			toast.success('Token revoked');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to revoke token');
		}
	}
</script>

<div class="mx-auto max-w-3xl space-y-6 p-6">
	<div>
		<h1 class="text-xl font-semibold">API Tokens</h1>
		<p class="text-sm text-neutral-500">Personal access tokens for scripts/integrations — use as a <code>Bearer</code> token in place of your session.</p>
	</div>

	<div class="flex items-end gap-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div class="flex-1">
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="tok-name">Name</label>
			<input
				id="tok-name"
				bind:value={name}
				placeholder="e.g. reporting script"
				class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
			/>
		</div>
		<button
			type="button"
			disabled={creating}
			onclick={create}
			class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
		>
			{creating ? 'Creating…' : 'Create Token'}
		</button>
	</div>

	{#if revealedToken}
		<div class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950">
			<p class="font-medium text-amber-800 dark:text-amber-300">Token (shown once — copy it now):</p>
			<code class="mt-1 block break-all rounded bg-white px-2 py-1 text-xs dark:bg-neutral-900">{revealedToken}</code>
		</div>
	{/if}

	{#if tokens.length === 0}
		<p class="text-sm text-neutral-400">No tokens yet.</p>
	{:else}
		<ul class="space-y-2">
			{#each tokens as t (t.id)}
				<li class="flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-3 text-sm dark:border-neutral-800 dark:bg-neutral-900">
					<div>
						<p class="font-medium">{t.name}</p>
						<p class="text-xs text-neutral-400">{t.last_used_at ? `Last used ${formatDateDisplay(t.last_used_at.slice(0, 10))}` : 'Never used'}</p>
					</div>
					<button type="button" onclick={() => revoke(t)} class="text-xs text-neutral-400 hover:text-red-600">Revoke</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>
