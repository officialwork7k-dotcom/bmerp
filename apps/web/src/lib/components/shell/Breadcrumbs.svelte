<script lang="ts">
	import { page } from '$app/state';
	import { displayName } from '$lib/types';

	// Derived entirely from the current page's params/load-data — no
	// per-route breadcrumb configuration needed anywhere.
	const crumbs = $derived.by(() => {
		const path = page.url.pathname;
		if (path.startsWith('/admin')) {
			return [{ label: 'Admin', href: '/admin/builder' }, { label: 'Builder', href: null }];
		}
		const moduleName = page.params.module;
		if (!moduleName) return [];

		const data = page.data as { module?: { label: string }; record?: Record<string, unknown> };
		const moduleLabel = data.module?.label ?? moduleName;
		const list: { label: string; href: string | null }[] = [{ label: moduleLabel, href: `/${moduleName}` }];

		if (page.params.id) {
			const recordLabel = page.params.id === 'new' ? 'New' : displayName(data.record);
			list.push({ label: recordLabel, href: null });
		}
		return list;
	});
</script>

{#if crumbs.length > 0}
	<nav class="flex min-w-0 items-center gap-1.5 text-sm text-neutral-500" aria-label="Breadcrumb">
		{#each crumbs as crumb, i (i)}
			{#if i > 0}<span class="shrink-0 text-neutral-300 dark:text-neutral-700">/</span>{/if}
			{#if crumb.href}
				<a href={crumb.href} class="shrink-0 hover:text-neutral-900 hover:underline dark:hover:text-neutral-100">{crumb.label}</a>
			{:else}
				<span class="min-w-0 truncate font-medium text-neutral-900 dark:text-neutral-100">{crumb.label}</span>
			{/if}
		{/each}
	</nav>
{/if}
