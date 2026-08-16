<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth, logout, switchClient } from '$lib/auth.svelte';
	import { toast } from '$lib/toast.svelte';
	import ChatButton from '$lib/components/ai/ChatButton.svelte';
	import Breadcrumbs from './Breadcrumbs.svelte';
	import GlobalSearch from './GlobalSearch.svelte';
	import NotificationBell from './NotificationBell.svelte';
	import ThemeSwitcher from './ThemeSwitcher.svelte';

	let { onOpenMobileNav }: { onOpenMobileNav?: () => void } = $props();

	async function onLogout() {
		await logout();
		await goto('/login', { invalidateAll: true });
	}

	let switching = $state(false);
	async function onSwitchOrg(e: Event) {
		const code = (e.target as HTMLSelectElement).value;
		if (!auth.user || code === auth.user.client_code) return;
		switching = true;
		try {
			await switchClient(code);
			// Every page's load() fetched data scoped to the old org — a full
			// reload is the simplest way to guarantee nothing stale (a saved
			// list filter, a cached lookup, a report already on screen) lingers
			// from the org just left.
			window.location.reload();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to switch organization');
			switching = false;
		}
	}
</script>

<header
	class="sticky top-0 z-10 flex h-12 items-center gap-2 border-b border-neutral-200 bg-white/80 px-3 backdrop-blur sm:gap-3 sm:px-4 dark:border-neutral-800 dark:bg-neutral-950/80"
>
	{#if onOpenMobileNav}
		<button
			type="button"
			onclick={onOpenMobileNav}
			class="shrink-0 rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 lg:hidden dark:hover:bg-neutral-800"
			aria-label="Open navigation"
		>
			☰
		</button>
	{/if}
	<div class="min-w-0 flex-1">
		<Breadcrumbs />
	</div>
	<!-- `display_name` drops below `sm` — "Sign out" alone still says who can
	     click it, and freeing that width is what keeps the theme swatch,
	     bell, and sign-out button from being pushed off the right edge of a
	     phone screen (all three used to land past x=375 on a 375px
	     viewport). -->
	<div class="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-3">
		{#if auth.user}
			<GlobalSearch />
		{/if}
		{#if auth.user}
			{#if auth.user.organizations.length > 1}
				<select
					value={auth.user.client_code}
					onchange={onSwitchOrg}
					disabled={switching}
					aria-label="Switch organization"
					class="max-w-[9rem] truncate rounded-md border border-neutral-200 bg-white px-1.5 py-1 text-xs font-medium text-neutral-600 outline-none disabled:opacity-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300"
				>
					{#each auth.user.organizations as org (org.code)}
						<option value={org.code}>{org.name}</option>
					{/each}
				</select>
			{:else}
				<span
					class="hidden max-w-[9rem] truncate text-xs font-medium text-neutral-500 sm:inline dark:text-neutral-400"
					title={auth.user.client_name}
				>
					{auth.user.client_name}
				</span>
			{/if}
		{/if}
		<ThemeSwitcher />
		{#if auth.user}
			<ChatButton />
			<NotificationBell />
			<span class="hidden text-sm text-neutral-600 sm:inline dark:text-neutral-400">{auth.user.display_name}</span>
			<button
				type="button"
				onclick={onLogout}
				class="rounded-md px-2 py-1 text-sm text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 dark:hover:bg-neutral-800 dark:hover:text-neutral-100"
			>
				Sign out
			</button>
		{/if}
	</div>
</header>
