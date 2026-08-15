<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Dialog } from 'bits-ui';
	import { beforeNavigate } from '$app/navigation';
	import type { ModuleMetadata } from '$lib/types';
	import Sidebar from './Sidebar.svelte';
	import Topbar from './Topbar.svelte';
	import Toaster from '$lib/components/ui/Toaster.svelte';
	import ChatPanel from '$lib/components/ai/ChatPanel.svelte';

	let { modules, children }: { modules: ModuleMetadata[]; children: Snippet } = $props();

	// A module that only ever exists as another module's embedded child grid
	// (a line-items table) is never meant to be browsed on its own — no ERP
	// puts "Invoice Lines" next to "Vendor Invoices" in primary nav. Derived
	// straight from the relationships every module already declares, so a
	// module authored in the Builder with an embedded child relationship is
	// automatically kept out of top-level nav with no extra configuration.
	const embeddedChildNames = $derived(
		new Set(
			modules.flatMap((m) => m.relationships.filter((r) => r.embedded && r.type === 'ONE_TO_MANY').map((r) => r.related_module))
		)
	);
	const navModules = $derived(modules.filter((m) => !embeddedChildNames.has(m.name)));

	let collapsed = $state(false);
	let mobileOpen = $state(false);

	$effect(() => {
		const stored = localStorage.getItem('mf:sidebar');
		if (stored === 'collapsed') collapsed = true;
	});

	function toggleCollapse() {
		collapsed = !collapsed;
		localStorage.setItem('mf:sidebar', collapsed ? 'collapsed' : 'expanded');
	}

	beforeNavigate(() => {
		mobileOpen = false;
	});
</script>

<div class="flex h-screen bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
	<aside
		class="hidden shrink-0 border-r border-neutral-200 transition-[width] duration-150 lg:block dark:border-neutral-800"
		style:width={collapsed ? '4rem' : '15rem'}
	>
		<Sidebar modules={navModules} {collapsed} onToggleCollapse={toggleCollapse} />
	</aside>

	<Dialog.Root bind:open={mobileOpen}>
		<Dialog.Portal>
			<Dialog.Overlay class="fixed inset-0 z-40 bg-black/40 lg:hidden" />
			<Dialog.Content class="fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-xl lg:hidden dark:bg-neutral-950">
				<Sidebar modules={navModules} />
			</Dialog.Content>
		</Dialog.Portal>
	</Dialog.Root>

	<div class="flex min-w-0 flex-1 flex-col">
		<Topbar onOpenMobileNav={() => (mobileOpen = true)} />
		<main class="min-w-0 flex-1 overflow-y-auto">
			{@render children()}
		</main>
	</div>

	<Toaster />
	<ChatPanel />
</div>
