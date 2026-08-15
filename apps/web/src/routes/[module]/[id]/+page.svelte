<script lang="ts">
	import { goto } from '$app/navigation';
	import DetailPage from '$lib/components/engine/DetailPage.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

{#key `${data.module.name}/${data.record?.id ?? 'new'}`}
	<!-- DetailPage seeds its editable `values`/`savedSnapshot`/child-grid state
	     from props exactly once (a deliberate one-time seed, not a reactive
	     derivation — see its own svelte-ignore comments). SvelteKit reuses
	     this same component instance across navigations that only change
	     route params (module/id), so without this #key, going from one
	     record to another — including across different modules, e.g. the
	     document-flow "create GR from this PO" action — left the page
	     showing the *previous* record's stale status/values until a full
	     reload. Keying on module+id forces a real remount whenever either
	     changes, which is exactly the reset point wanted. -->
	<DetailPage
		module={data.module}
		childModules={data.childModules}
		record={data.record}
		onCreated={(created) => goto(`/${data.module.name}/${created.id}`)}
	/>
{/key}
