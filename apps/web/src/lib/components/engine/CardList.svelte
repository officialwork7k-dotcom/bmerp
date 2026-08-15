<script lang="ts">
	import type { FieldMetadata, ModuleMetadata, RecordRow } from '$lib/types';
	import { displayName } from '$lib/types';

	let {
		module,
		records,
		listFields,
		formatterFor,
		onRowClick
	}: {
		module: ModuleMetadata;
		records: RecordRow[];
		/** Same field subset ListPage already shows as table columns — kept
		 * as the single source of truth for "what's worth showing" so the
		 * card and table views never disagree about which fields matter. */
		listFields: FieldMetadata[];
		formatterFor: (f: FieldMetadata) => ((v: unknown) => string) | undefined;
		onRowClick: (record: RecordRow) => void;
	} = $props();

	// Zero-config layout heuristic: works for *any* module's field set
	// without new metadata, by picking the most legible field for each
	// card role from whatever's already in `listFields`. A module that
	// wants finer control can still reorder its fields in the builder —
	// this reads position + data_type, nothing hardcoded per module.
	const metricField = $derived(listFields.find((f) => ['MONEY', 'DECIMAL', 'PERCENT'].includes(f.data_type)));
	const subtitleField = $derived(
		listFields.find((f) => f !== metricField && ['LOOKUP', 'DATE', 'EMAIL'].includes(f.data_type))
	);
	const titleField = $derived(listFields.find((f) => f !== metricField && f !== subtitleField) ?? listFields[0]);
	const restFields = $derived(listFields.filter((f) => f !== titleField && f !== subtitleField && f !== metricField));

	const workflow = $derived(module.workflow);

	let expandedId = $state<string | null>(null);

	const STATUS_COLOR_CLASSES: Record<string, string> = {
		neutral: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
		blue: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
		green: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
		amber: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
		red: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
		purple: 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300'
	};

	function statusFor(record: RecordRow): { label: string; classes: string } | null {
		if (!workflow) return null;
		const value = record[workflow.field];
		if (value == null) return null;
		const color = workflow.states[String(value)]?.color ?? 'neutral';
		return { label: String(value), classes: STATUS_COLOR_CLASSES[color] ?? STATUS_COLOR_CLASSES.neutral };
	}

	function fieldValue(record: RecordRow, f: FieldMetadata): string {
		const format = formatterFor(f);
		const raw = record[f.name];
		const formatted = format ? format(raw) : raw;
		return String(formatted ?? '') || '—';
	}

	function toggleExpanded(id: string) {
		expandedId = expandedId === id ? null : id;
	}
</script>

<ul class="space-y-2">
	{#each records as record (record.id)}
		{@const status = statusFor(record)}
		<li class="rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
			<button type="button" class="flex w-full items-start justify-between gap-3 p-3 text-left" onclick={() => onRowClick(record)}>
				<div class="min-w-0 flex-1">
					<div class="flex items-center gap-2">
						<span class="truncate font-medium">
							{titleField ? fieldValue(record, titleField) : displayName(record, module.label)}
						</span>
						{#if status}
							<span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium {status.classes}">{status.label}</span>
						{/if}
					</div>
					{#if subtitleField}
						<p class="mt-0.5 truncate text-sm text-neutral-500">{fieldValue(record, subtitleField)}</p>
					{/if}
				</div>
				{#if metricField}
					<span class="shrink-0 pt-0.5 text-right text-sm font-medium tabular-nums">{fieldValue(record, metricField)}</span>
				{/if}
			</button>

			{#if restFields.length > 0}
				<div class="border-t border-neutral-100 px-3 py-1 dark:border-neutral-800">
					<button
						type="button"
						onclick={(e) => {
							e.stopPropagation();
							toggleExpanded(record.id);
						}}
						class="w-full py-1 text-center text-xs text-neutral-400"
					>
						{expandedId === record.id ? '▲ Less' : '▼ More'}
					</button>
					{#if expandedId === record.id}
						<dl class="grid grid-cols-2 gap-x-3 gap-y-1 pb-2 text-sm">
							{#each restFields as f (f.name)}
								<dt class="text-neutral-400">{f.label}</dt>
								<dd class="text-right">{fieldValue(record, f)}</dd>
							{/each}
						</dl>
					{/if}
				</div>
			{/if}
		</li>
	{/each}
</ul>
