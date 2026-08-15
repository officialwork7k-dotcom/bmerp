<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { THEMES, themeState, setTheme } from '$lib/theme.svelte';

	const current = $derived(THEMES.find((t) => t.id === themeState.current) ?? THEMES[0]);
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger
		class="flex items-center gap-1.5 rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
		aria-label="Choose theme"
		title="Theme: {current.label}"
	>
		<span
			class="h-4 w-4 shrink-0 rounded-full border border-black/10 dark:border-white/20"
			style:background-color={current.swatch}
		></span>
	</DropdownMenu.Trigger>
	<DropdownMenu.Portal>
		<DropdownMenu.Content
			class="z-50 w-44 rounded-md border border-neutral-200 bg-white p-1 shadow-xl dark:border-neutral-800 dark:bg-neutral-900"
			align="end"
			sideOffset={6}
		>
			<p class="px-2 py-1.5 text-xs font-semibold uppercase text-neutral-400">Theme</p>
			{#each THEMES as t (t.id)}
				<button
					type="button"
					onclick={() => setTheme(t.id)}
					class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800 {t.id ===
					themeState.current
						? 'font-medium text-primary-700 dark:text-primary-300'
						: 'text-neutral-700 dark:text-neutral-300'}"
				>
					<span class="h-3.5 w-3.5 shrink-0 rounded-full border border-black/10 dark:border-white/20" style:background-color={t.swatch}
					></span>
					<span class="flex-1">{t.label}</span>
					{#if t.id === themeState.current}
						<span aria-hidden="true">✓</span>
					{/if}
				</button>
			{/each}
		</DropdownMenu.Content>
	</DropdownMenu.Portal>
</DropdownMenu.Root>
