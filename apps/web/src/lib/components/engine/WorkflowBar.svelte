<script lang="ts">
	import { api } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import type { ModuleMetadata, RecordRow } from '$lib/types';

	let {
		module,
		record,
		onTransitioned
	}: {
		module: ModuleMetadata;
		record: RecordRow;
		/** Called with the freshly transitioned record so the caller can refresh its local state. */
		onTransitioned: (updated: RecordRow) => void;
	} = $props();

	const workflow = $derived(module.workflow);
	const current = $derived(workflow ? (record[workflow.field] as string | undefined) : undefined);
	const stateConfig = $derived(workflow && current ? workflow.states[current] : undefined);
	const allowedNext = $derived(workflow && current ? (workflow.transitions[current] ?? []) : []);

	let transitioning = $state<string | null>(null);

	// Fixed palette so Tailwind's JIT scanner can see every class name
	// statically — an interpolated `bg-${color}-100` string never gets
	// picked up by the build, it just silently renders unstyled.
	const COLOR_CLASSES: Record<string, string> = {
		neutral: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
		blue: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
		green: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
		amber: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
		red: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
		purple: 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300'
	};

	async function transition(to: string) {
		if (!current) return;
		transitioning = to;
		try {
			const updated = await api.transitionRecord(module.name, record.id, to, undefined, record.version as number | undefined);
			onTransitioned(updated);
			toast.success(`Moved to "${to}"`);
		} catch (e) {
			const message = e instanceof Error ? e.message : 'Transition failed';
			// No "update" permission on this module: the direct transition is
			// off the table, but requesting one for an admin to decide still
			// is — this is the generic non-admin path into the approval queue
			// (see api/routers/approvals.py), not a dead end.
			if (message.startsWith('403')) {
				try {
					await api.requestApproval(module.name, record.id, current, to);
					toast.success(`Requested approval to move to "${to}"`);
				} catch (e2) {
					toast.error(e2 instanceof Error ? e2.message : 'Failed to request approval');
				}
			} else {
				toast.error(message);
			}
		} finally {
			transitioning = null;
		}
	}
</script>

{#if workflow && current}
	<div class="flex flex-wrap items-center gap-2 rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-900">
		<span class="text-xs font-semibold uppercase text-neutral-400">Status</span>
		<span class="rounded-full px-2.5 py-1 text-xs font-medium {COLOR_CLASSES[stateConfig?.color ?? 'neutral'] ?? COLOR_CLASSES.neutral}">
			{current}
		</span>
		{#if stateConfig?.locked}
			<span class="text-xs text-neutral-400">🔒 locked — only a status change is allowed</span>
		{/if}
		{#if allowedNext.length > 0}
			<span class="mx-1 text-neutral-300 dark:text-neutral-700">→</span>
			{#each allowedNext as next (next)}
				<button
					type="button"
					disabled={!!transitioning}
					onclick={() => transition(next)}
					class="rounded-md border border-neutral-300 px-2.5 py-1 text-xs font-medium hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
				>
					{transitioning === next ? 'Moving…' : `Move to ${next}`}
				</button>
			{/each}
		{/if}
	</div>
{/if}
