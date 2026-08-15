<script lang="ts">
	import { api, type Webhook } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// svelte-ignore state_referenced_locally -- one-time seed from load()
	let webhooks = $state<Webhook[]>(data.webhooks);
	let module = $state('');
	let url = $state('');
	let events = $state<string[]>(['create', 'update', 'delete']);
	let creating = $state(false);
	let revealedSecret = $state<{ id: string; secret: string } | null>(null);

	function toggleEvent(e: string) {
		events = events.includes(e) ? events.filter((x) => x !== e) : [...events, e];
	}

	async function create() {
		if (!module.trim() || !url.trim()) {
			toast.error('Module and URL are required');
			return;
		}
		creating = true;
		try {
			const created = await api.createWebhook(module.trim(), url.trim(), events);
			webhooks = [...webhooks, created];
			revealedSecret = { id: created.id, secret: created.secret };
			module = '';
			url = '';
			toast.success('Webhook created');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to create webhook');
		} finally {
			creating = false;
		}
	}

	async function remove(w: Webhook) {
		try {
			await api.deleteWebhook(w.id);
			webhooks = webhooks.filter((x) => x.id !== w.id);
			toast.success('Webhook deleted');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to delete webhook');
		}
	}
</script>

<div class="mx-auto max-w-3xl space-y-6 p-6">
	<div>
		<h1 class="text-xl font-semibold">Webhooks</h1>
		<p class="text-sm text-neutral-500">Notify an external URL when a module's records are created, updated, or deleted.</p>
	</div>

	<div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
			<div>
				<label class="mb-1 block text-xs font-medium text-neutral-500" for="wh-module">Module</label>
				<input
					id="wh-module"
					bind:value={module}
					placeholder="e.g. vendor_invoices"
					class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
				/>
			</div>
			<div>
				<label class="mb-1 block text-xs font-medium text-neutral-500" for="wh-url">URL</label>
				<input
					id="wh-url"
					bind:value={url}
					placeholder="https://example.com/hooks/metaforge"
					class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
				/>
			</div>
		</div>
		<div class="mt-3 flex items-center gap-3">
			{#each ['create', 'update', 'delete'] as e (e)}
				<label class="flex items-center gap-1.5 text-sm">
					<input type="checkbox" checked={events.includes(e)} onchange={() => toggleEvent(e)} />
					{e}
				</label>
			{/each}
			<button
				type="button"
				disabled={creating}
				onclick={create}
				class="ml-auto rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
			>
				{creating ? 'Creating…' : 'Create Webhook'}
			</button>
		</div>
	</div>

	{#if revealedSecret}
		<div class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950">
			<p class="font-medium text-amber-800 dark:text-amber-300">Secret (shown once — copy it now):</p>
			<code class="mt-1 block break-all rounded bg-white px-2 py-1 text-xs dark:bg-neutral-900">{revealedSecret.secret}</code>
		</div>
	{/if}

	{#if webhooks.length === 0}
		<p class="text-sm text-neutral-400">No webhooks configured.</p>
	{:else}
		<ul class="space-y-2">
			{#each webhooks as w (w.id)}
				<li class="flex items-center justify-between rounded-lg border border-neutral-200 bg-white p-3 text-sm dark:border-neutral-800 dark:bg-neutral-900">
					<div>
						<p class="font-medium">{w.module}</p>
						<p class="text-neutral-500">{w.url}</p>
						<p class="text-xs text-neutral-400">{w.events.join(', ')}</p>
					</div>
					<button type="button" onclick={() => remove(w)} class="text-xs text-neutral-400 hover:text-red-600">Delete</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>
