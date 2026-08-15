<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import AppShell from '$lib/components/shell/AppShell.svelte';
	import { applyTheme } from '$lib/theme.svelte';
	import type { LayoutData } from './$types';

	let { data, children }: { data: LayoutData; children: import('svelte').Snippet } = $props();

	// Reconciles the fast localStorage-cached theme (applied synchronously
	// in app.html, before this component even mounts) with the server's
	// per-user value once it's known — authoritative on a new device, or
	// after the user changed their theme somewhere else. A no-op re-write
	// when they already match.
	$effect(() => {
		if (data.user?.theme) applyTheme(data.user.theme);
	});
</script>

{#if page.url.pathname === '/login'}
	{@render children()}
{:else}
	<AppShell modules={data.modules}>
		{@render children()}
	</AppShell>
{/if}
