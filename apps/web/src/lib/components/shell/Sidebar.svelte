<script lang="ts">
	import { page } from '$app/state';
	import { auth } from '$lib/auth.svelte';
	import { favorites } from '$lib/favorites.svelte';
	import type { ModuleMetadata } from '$lib/types';
	import SidebarItem from './SidebarItem.svelte';

	let {
		modules,
		collapsed = false,
		onToggleCollapse
	}: { modules: ModuleMetadata[]; collapsed?: boolean; onToggleCollapse?: () => void } = $props();

	const path = $derived(page.url.pathname);
	function isModuleActive(name: string): boolean {
		return path === `/${name}` || path.startsWith(`/${name}/`);
	}
	const builderActive = $derived(path.startsWith('/admin/builder'));

	// SAP-style area grouping for top-level nav — purely a display grouping
	// (no metadata concept of "area" exists, so this is a static map rather
	// than a builder-configurable field, matching how little churn the
	// module set actually has). A module created later that isn't in this
	// map still shows up — under "Other" — rather than silently vanishing
	// from nav, so a new Builder module is never invisible.
	const MODULE_AREAS: Record<string, string> = {
		// FI — Financial Accounting
		gl_accounts: 'Financial Accounting',
		general_journal: 'Financial Accounting',
		gl_account_determination: 'Financial Accounting',
		vendors: 'Financial Accounting',
		vendor_categories: 'Financial Accounting',
		customers: 'Financial Accounting',
		customer_categories: 'Financial Accounting',
		vendor_invoices: 'Financial Accounting',
		customer_invoices: 'Financial Accounting',
		payments: 'Financial Accounting',
		customer_receipts: 'Financial Accounting',
		tax_codes: 'Financial Accounting',
		opening_balances: 'Financial Accounting',
		// AA — Asset Accounting
		fixed_assets: 'Asset Accounting',
		asset_categories: 'Asset Accounting',
		// Bank
		bank_accounts: 'Bank',
		bank_transactions: 'Bank',
		// SD — Sales & Distribution
		sales_orders: 'Sales & Distribution',
		deliveries: 'Sales & Distribution',
		customer_price_lists: 'Sales & Distribution',
		// MM — Materials Management
		items: 'Materials Management',
		purchase_orders: 'Materials Management',
		goods_receipts: 'Materials Management',
		vendor_price_lists: 'Materials Management',
		stock_adjustments: 'Materials Management',
		// Settings
		localization_settings: 'Settings',
		countries: 'Settings',
		currencies: 'Settings'
	};
	// Order matches the user's requested reading priority: money (FI) first,
	// then what it's tied to (AA, Bank), then the two operational flows that
	// generate most of that money (SD, MM) last.
	const AREA_ORDER = ['Financial Accounting', 'Asset Accounting', 'Bank', 'Sales & Distribution', 'Materials Management', 'Settings', 'Other'];

	// Hidden modules (child-only grids, reference data — see
	// ModuleMetadata.hidden) never get their own nav entry, in favorites or
	// area groups alike; the module/API stay fully reachable by URL, this
	// only affects navigation.
	const visibleModules = $derived(modules.filter((m) => !m.hidden));

	const groupedModules = $derived.by(() => {
		const groups = new Map<string, ModuleMetadata[]>();
		for (const m of visibleModules) {
			const area = MODULE_AREAS[m.name] ?? 'Other';
			if (!groups.has(area)) groups.set(area, []);
			groups.get(area)!.push(m);
		}
		return AREA_ORDER.map((area) => ({ area, mods: groups.get(area) ?? [] })).filter((g) => g.mods.length > 0);
	});

	const favoriteModules = $derived(visibleModules.filter((m) => favorites.isFavorite(m.name)));
</script>

<nav class="flex h-full flex-col gap-4 overflow-y-auto p-3">
	<div class="flex items-center justify-between px-1">
		<a href="/" class="flex items-center gap-2 font-semibold" title="MetaForge">
			<span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary-600 text-sm text-white">M</span>
			{#if !collapsed}<span>MetaForge</span>{/if}
		</a>
		{#if onToggleCollapse}
			<button
				type="button"
				onclick={onToggleCollapse}
				class="hidden rounded-md p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 lg:block dark:hover:bg-neutral-800"
				aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
			>
				{collapsed ? '»' : '«'}
			</button>
		{/if}
	</div>

	<div>
		<SidebarItem href="/dashboard" label="Dashboard" active={path.startsWith('/dashboard')} {collapsed} />
	</div>

	{#if favoriteModules.length > 0}
		<div class="border-t border-neutral-200 pt-3 dark:border-neutral-800">
			{#if !collapsed}<p class="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">Favorites</p>{/if}
			<div class="flex flex-col gap-0.5 {collapsed ? '' : 'pl-1.5'}">
				{#each favoriteModules as m (m.name)}
					<SidebarItem
						href={`/${m.name}`}
						label={m.label}
						active={isModuleActive(m.name)}
						{collapsed}
						favoritable
						favorited
						onToggleFavorite={() => favorites.toggle(m.name)}
					/>
				{/each}
			</div>
		</div>
	{/if}

	{#each groupedModules as group, i (group.area)}
		<div class={i > 0 || favoriteModules.length > 0 ? 'border-t border-neutral-200 pt-3 dark:border-neutral-800' : ''}>
			{#if !collapsed}<p class="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">{group.area}</p>{/if}
			<div class="flex flex-col gap-0.5 {collapsed ? '' : 'pl-1.5'}">
				{#each group.mods as m (m.name)}
					<SidebarItem
						href={`/${m.name}`}
						label={m.label}
						active={isModuleActive(m.name)}
						{collapsed}
						favoritable
						favorited={favorites.isFavorite(m.name)}
						onToggleFavorite={() => favorites.toggle(m.name)}
					/>
				{/each}
			</div>
		</div>
	{/each}
	{#if visibleModules.length === 0 && !collapsed}
		<p class="px-3 text-xs text-neutral-400">No modules yet</p>
	{/if}

	<div>
		{#if !collapsed}<p class="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">Analysis</p>{/if}
		<SidebarItem href="/reports" label="Reports" active={path.startsWith('/reports')} {collapsed} />
		<SidebarItem href="/period-close" label="Period-End Close" active={path.startsWith('/period-close')} {collapsed} />
	</div>

	<div>
		{#if !collapsed}<p class="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">Account</p>{/if}
		<SidebarItem href="/admin/tokens" label="API Tokens" active={path.startsWith('/admin/tokens')} {collapsed} />
	</div>

	{#if auth.user?.is_admin}
		<div class="mt-auto">
			{#if !collapsed}<p class="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">Admin</p>{/if}
			<SidebarItem href="/admin/builder" label="Builder" active={builderActive} {collapsed} />
			<SidebarItem href="/admin/users" label="Users & Roles" active={path.startsWith('/admin/users')} {collapsed} />
			<SidebarItem href="/admin/approvals" label="Approvals" active={path.startsWith('/admin/approvals')} {collapsed} />
			<SidebarItem href="/admin/webhooks" label="Webhooks" active={path.startsWith('/admin/webhooks')} {collapsed} />
			<SidebarItem href="/admin/ai-settings" label="AI Assistant" active={path.startsWith('/admin/ai-settings')} {collapsed} />
		</div>
	{/if}
</nav>
