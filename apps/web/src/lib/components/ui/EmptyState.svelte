<script lang="ts">
	let {
		title,
		description,
		actionLabel,
		actionHref
	}: { title: string; description?: string; actionLabel?: string; actionHref?: string } = $props();
</script>

<div class="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-neutral-200 py-16 text-center dark:border-neutral-800">
	<p class="text-sm font-medium text-neutral-700 dark:text-neutral-300">{title}</p>
	{#if description}<p class="max-w-sm text-sm text-neutral-400">{description}</p>{/if}
	{#if actionLabel && actionHref}
		<a href={actionHref} class="mt-2 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700">
			{actionLabel}
		</a>
	{/if}
</div>
