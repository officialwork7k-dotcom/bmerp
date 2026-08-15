<script lang="ts">
	let {
		href,
		label,
		active,
		collapsed = false,
		favoritable = false,
		favorited = false,
		onToggleFavorite
	}: {
		href: string;
		label: string;
		active: boolean;
		collapsed?: boolean;
		favoritable?: boolean;
		favorited?: boolean;
		onToggleFavorite?: () => void;
	} = $props();
</script>

<a
	{href}
	aria-current={active ? 'page' : undefined}
	title={collapsed ? label : undefined}
	class="group relative flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors {active
		? 'bg-primary-50 font-medium text-primary-900 dark:bg-primary-950 dark:text-primary-100'
		: 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-900'}"
>
	{#if active}
		<span class="absolute inset-y-1 left-0 w-[3px] rounded-full bg-primary-600"></span>
	{/if}
	{#if collapsed}
		<span class="mx-auto flex h-6 w-6 items-center justify-center rounded bg-neutral-200 text-[10px] font-semibold dark:bg-neutral-800">
			{label.slice(0, 2).toUpperCase()}
		</span>
	{:else}
		<span class="min-w-0 flex-1 truncate">{label}</span>
		{#if favoritable}
			<button
				type="button"
				onclick={(e) => {
					e.preventDefault();
					e.stopPropagation();
					onToggleFavorite?.();
				}}
				title={favorited ? 'Remove from favorites' : 'Add to favorites'}
				aria-label={favorited ? `Remove ${label} from favorites` : `Add ${label} to favorites`}
				class="shrink-0 rounded p-0.5 text-xs {favorited
					? 'text-amber-500 opacity-100'
					: 'text-neutral-300 opacity-0 group-hover:opacity-100 hover:text-amber-500 dark:text-neutral-600'}"
			>
				{favorited ? '★' : '☆'}
			</button>
		{/if}
	{/if}
</a>
