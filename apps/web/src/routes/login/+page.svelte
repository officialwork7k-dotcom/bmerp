<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { login, ClientSelectionRequiredError } from '$lib/auth.svelte';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let submitting = $state(false);
	let availableClients = $state<string[] | null>(null);
	let selectedClient = $state('');

	async function finishLogin(clientCode?: string) {
		await login(username, password, undefined, clientCode);
		const redirectTo = page.url.searchParams.get('redirect') || '/';
		await goto(redirectTo, { invalidateAll: true });
	}

	async function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (submitting) return;
		submitting = true;
		error = '';
		try {
			await finishLogin();
		} catch (err) {
			if (err instanceof ClientSelectionRequiredError) {
				availableClients = err.availableClients;
				selectedClient = err.availableClients[0] ?? '';
			} else {
				error = err instanceof Error ? err.message : 'Login failed';
			}
		} finally {
			submitting = false;
		}
	}

	async function onSelectClient(e: SubmitEvent) {
		e.preventDefault();
		if (submitting || !selectedClient) return;
		submitting = true;
		error = '';
		try {
			await finishLogin(selectedClient);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Login failed';
		} finally {
			submitting = false;
		}
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-neutral-50 dark:bg-neutral-950">
	{#if availableClients}
		<form
			onsubmit={onSelectClient}
			class="w-full max-w-sm rounded-lg border border-neutral-200 bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-900"
		>
			<h1 class="mb-1 text-lg font-semibold text-neutral-900 dark:text-neutral-100">Choose organization</h1>
			<p class="mb-6 text-sm text-neutral-500 dark:text-neutral-400">
				This account has access to multiple organizations. Pick one to continue.
			</p>

			{#if error}
				<div class="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">
					{error}
				</div>
			{/if}

			<label class="mb-6 block text-sm">
				<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Organization</span>
				<select
					bind:value={selectedClient}
					class="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-800"
				>
					{#each availableClients as code (code)}
						<option value={code}>{code}</option>
					{/each}
				</select>
			</label>

			<button
				type="submit"
				disabled={submitting}
				class="w-full rounded-md bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-60 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-200"
			>
				{submitting ? 'Signing in…' : 'Continue'}
			</button>
			<button
				type="button"
				onclick={() => (availableClients = null)}
				class="mt-2 w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
			>
				Back
			</button>
		</form>
	{:else}
		<form
			onsubmit={onSubmit}
			class="w-full max-w-sm rounded-lg border border-neutral-200 bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-900"
		>
			<h1 class="mb-1 text-lg font-semibold text-neutral-900 dark:text-neutral-100">MetaForge</h1>
			<p class="mb-6 text-sm text-neutral-500 dark:text-neutral-400">Sign in to continue</p>

			{#if error}
				<div class="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">
					{error}
				</div>
			{/if}

			<label class="mb-3 block text-sm">
				<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Username</span>
				<input
					bind:value={username}
					name="username"
					autocomplete="username"
					required
					class="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-800"
				/>
			</label>

			<label class="mb-6 block text-sm">
				<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Password</span>
				<input
					bind:value={password}
					name="password"
					type="password"
					autocomplete="current-password"
					required
					class="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-800"
				/>
			</label>

			<button
				type="submit"
				disabled={submitting}
				class="w-full rounded-md bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-60 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-200"
			>
				{submitting ? 'Signing in…' : 'Sign in'}
			</button>

			<div class="my-4 flex items-center gap-3 text-xs text-neutral-400">
				<div class="h-px flex-1 bg-neutral-200 dark:bg-neutral-800"></div>
				or
				<div class="h-px flex-1 bg-neutral-200 dark:bg-neutral-800"></div>
			</div>

			<a
				href="/api/auth/oauth/google/start"
				class="flex w-full items-center justify-center gap-2 rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-800"
			>
				<svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
					<path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.9 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.5 6 29.5 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.7-.4-3.5z" />
					<path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 15.9 18.9 13 24 13c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.5 6 29.5 4 24 4c-7.7 0-14.4 4.3-17.7 10.7z" />
					<path fill="#4CAF50" d="M24 44c5.4 0 10.3-1.8 14.1-5.1l-6.5-5.5C29.5 35 26.9 36 24 36c-5.3 0-9.7-3.1-11.3-7.5l-6.5 5C9.5 39.7 16.2 44 24 44z" />
					<path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.9 2.5-2.5 4.6-4.7 6.1l6.5 5.5C40.5 36.4 44 30.8 44 24c0-1.3-.1-2.7-.4-3.5z" />
				</svg>
				Sign in with Google
			</a>
		</form>
	{/if}
</div>
