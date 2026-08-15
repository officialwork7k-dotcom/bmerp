<script lang="ts">
	import ListPage from '$lib/components/engine/ListPage.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<ListPage module={data.module} records={data.records} lookupLabels={data.lookupLabels} />
