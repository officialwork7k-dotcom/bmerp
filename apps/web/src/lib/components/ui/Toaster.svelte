<script lang="ts">
	import { toast } from '$lib/toast.svelte';
	import { localization } from '$lib/localization.svelte';

	// Static class strings (not composed at runtime) so Tailwind v4's
	// build-time scanner actually sees and emits them — a dynamically
	// concatenated class name would silently produce no CSS.
	const POSITION_CLASSES: Record<string, string> = {
		'top-left': 'top-4 left-4 items-start',
		'top-center': 'top-4 left-1/2 -translate-x-1/2 items-center',
		'top-right': 'top-4 right-4 items-end',
		'bottom-left': 'bottom-4 left-4 items-start',
		'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2 items-center',
		'bottom-right': 'bottom-4 right-4 items-end'
	};

	const KIND_CLASSES: Record<string, string> = {
		success: 'border-green-200 bg-green-50 text-green-800 dark:border-green-900 dark:bg-green-950 dark:text-green-300',
		error: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300',
		warning: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300',
		info: 'border-primary-200 bg-primary-50 text-primary-800 dark:border-primary-900 dark:bg-primary-950 dark:text-primary-300'
	};

	const positionClass = $derived(POSITION_CLASSES[localization.notification_position] ?? POSITION_CLASSES['bottom-center']);
	// Stack order flips for top-anchored positions so the newest toast
	// still appears nearest the edge it's anchored to, not pushed away from it.
	const isTop = $derived(localization.notification_position.startsWith('top'));
</script>

<div
	class="pointer-events-none fixed z-50 flex flex-col gap-2 {positionClass} {isTop ? 'flex-col' : 'flex-col-reverse'}"
	role="status"
	aria-live="polite"
>
	{#each toast.list() as t (t.id)}
		<div
			class="pointer-events-auto flex max-w-sm items-start gap-2 rounded-md border px-4 py-2.5 text-sm shadow-lg {KIND_CLASSES[t.kind]}"
			onmouseenter={() => toast.pause(t.id)}
			onmouseleave={() => toast.resume(t.id)}
			role="alert"
		>
			<span class="flex-1">{t.message}</span>
			<button
				type="button"
				class="ml-2 shrink-0 text-xs opacity-60 hover:opacity-100"
				onclick={() => toast.dismiss(t.id)}
				aria-label="Dismiss"
			>
				✕
			</button>
		</div>
	{/each}
</div>
