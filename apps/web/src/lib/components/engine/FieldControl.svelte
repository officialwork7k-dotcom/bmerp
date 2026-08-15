<script lang="ts">
	import { Checkbox, Popover, Select, Switch } from 'bits-ui';
	import type { FieldMetadata } from '$lib/types';
	import { createSearchController, resolveLabel } from '$lib/lookup';
	import { formatDateDisplay, parseDateInput } from '$lib/date';
	import { localization } from '$lib/localization.svelte';
	import { CURRENCY_SYMBOLS } from '$lib/format';

	let {
		field,
		value = $bindable(),
		disabled = false,
		siblingValues
	}: {
		field: FieldMetadata;
		value: unknown;
		disabled?: boolean;
		/** The rest of the current record's field values, keyed by field
		 * name — only needed for a LOOKUP field that declares
		 * `lookup_filter` (e.g. Vendor Invoice's Purchase Order picker
		 * narrowed to the already-selected vendor). Not required for any
		 * other control type. */
		siblingValues?: Record<string, unknown>;
	} = $props();

	const control = $derived(field.control_type || defaultControlFor(field.data_type));

	function defaultControlFor(dataType: FieldMetadata['data_type']): string {
		switch (dataType) {
			case 'LONG_TEXT':
			case 'RICH_TEXT':
				return 'textarea';
			case 'INTEGER':
			case 'DECIMAL':
			case 'MONEY':
			case 'PERCENT':
				return 'number';
			case 'DATE':
				return 'date';
			case 'TIME':
				return 'time';
			case 'DATETIME':
				return 'datetime';
			case 'BOOLEAN':
				return 'checkbox';
			case 'ENUM':
				return 'select';
			case 'LOOKUP':
				return 'lookup';
			case 'FILE':
				return 'file';
			case 'IMAGE':
				return 'image';
			case 'JSON':
				return 'json';
			default:
				return 'input';
		}
	}

	// --- lookup search state ---
	let lookupOpen = $state(false);
	let lookupSearch = $state('');
	let lookupOptions = $state<{ value: string; label: string }[]>([]);
	let lookupLoading = $state(false);
	let lookupSelectedLabel = $state<string | null>(null);

	// Resolve the current value's display label as soon as it's known, not
	// only once the popover is opened — otherwise an existing record's
	// lookup field shows the raw foreign-key UUID until the user clicks in.
	let resolvedFor: unknown = null;
	$effect(() => {
		if (!field.lookup_module || !value || resolvedFor === value) return;
		resolvedFor = value;
		resolveLabel(field.lookup_module, String(value)).then((label) => (lookupSelectedLabel = label));
	});

	// Narrows this LOOKUP's candidates to ones matching a sibling field
	// already selected on this record (e.g. only POs for the chosen
	// vendor). `undefined` filterValue (nothing selected yet upstream)
	// deliberately still searches unfiltered rather than blocking the
	// picker — the field just isn't narrowed until its dependency is set.
	const lookupFilterValue = $derived(
		field.lookup_filter ? siblingValues?.[field.lookup_filter.from_field] : undefined
	);
	const lookupFilters = $derived(
		field.lookup_filter && lookupFilterValue != null
			? { [field.lookup_filter.by_field]: String(lookupFilterValue) }
			: undefined
	);

	// Race-safe: see createSearchController's docstring — a plain debounce
	// alone doesn't stop an earlier, shorter query's response from landing
	// after a later one's and clobbering the list with stale results, which
	// is very reachable at normal typing speed.
	const searchController = createSearchController(250);
	$effect(() => {
		if (!lookupOpen || !field.lookup_module) return;
		searchController.run(
			field.lookup_module,
			lookupSearch,
			(results) => (lookupOptions = results),
			(l) => (lookupLoading = l),
			lookupFilters
		);
	});
	$effect(() => () => searchController.dispose());

	// If this field's filter dependency (e.g. Vendor) changes to a
	// different value, the currently-selected candidate (e.g. a PO) may no
	// longer be valid for it — clear it rather than silently leaving a
	// stale, now-mismatched selection in place.
	let lastFilterValue: unknown;
	let filterInitialized = false;
	$effect(() => {
		if (!field.lookup_filter) return;
		if (!filterInitialized) {
			filterInitialized = true;
			lastFilterValue = lookupFilterValue;
			return;
		}
		if (lookupFilterValue !== lastFilterValue) {
			lastFilterValue = lookupFilterValue;
			value = undefined;
			lookupSelectedLabel = null;
		}
	});

	// --- date quick-entry buffer ---
	// Typing over a native <input type="date"> can't accept SAP-style
	// shorthand ("1.1.26", "t" for today) — it only accepts real date
	// keystrokes per the browser's own locale. A plain text input with a
	// buffer that only gets parsed on commit (blur/Enter) is what makes
	// that shorthand possible; the stored `value` is always a real
	// `yyyy-mm-dd` ISO string, same as before, so nothing downstream needs
	// to know quick entry happened.
	let dateEditing = $state(false);
	let dateBuffer = $state('');

	function beginDateEdit() {
		dateEditing = true;
		dateBuffer = formatDateDisplay(value as string | undefined);
	}

	function commitDateEdit() {
		dateEditing = false;
		if (dateBuffer.trim() === '') {
			value = undefined;
			return;
		}
		const parsed = parseDateInput(dateBuffer);
		// Unparseable input is dropped rather than stored as garbage or
		// silently cleared — the field just reverts to showing its last
		// good value, same as leaving a spreadsheet cell with a typo.
		if (parsed) value = parsed;
	}

	// --- json text buffer ---
	let jsonText = $state(value ? JSON.stringify(value, null, 2) : '');
	let jsonError = $state<string | null>(null);
	function onJsonInput(text: string) {
		jsonText = text;
		if (text.trim() === '') {
			value = undefined;
			jsonError = null;
			return;
		}
		try {
			value = JSON.parse(text);
			jsonError = null;
		} catch {
			jsonError = 'Invalid JSON';
		}
	}

	// --- file upload ---
	let uploading = $state(false);
	async function onFileSelected(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		uploading = true;
		try {
			const fd = new FormData();
			fd.append('file', file);
			const res = await fetch('/api/uploads', { method: 'POST', body: fd });
			const up = await res.json();
			value = { id: up.id, name: up.filename, url: up.url };
		} finally {
			uploading = false;
		}
	}

	// A permanently system-managed field (AUTO_NUMBER, a locked LOOKUP, any
	// other field the builder marked read_only) gets a visibly different
	// look from a merely-disabled one — a flat opacity fade reads the same
	// whether a field is "computed, never editable" or "temporarily
	// disabled by a condition," and users kept trying to type into the
	// former assuming it'd unlock once some other field was filled in.
	const inputClass = $derived(
		'h-9 w-full rounded-md border px-3 text-sm outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed ' +
			(field.read_only
				? 'border-neutral-200 bg-neutral-100 text-neutral-500 dark:border-neutral-800 dark:bg-neutral-800/70 dark:text-neutral-400'
				: 'border-neutral-300 bg-white disabled:opacity-50 dark:border-neutral-700 dark:bg-neutral-900')
	);
</script>

{#if control === 'textarea' || control === 'richtext'}
	<textarea
		class={inputClass + ' min-h-24 py-2'}
		{disabled}
		bind:value
		maxlength={field.max_length}
	></textarea>
{:else if control === 'number'}
	<div class="relative">
		{#if field.data_type === 'MONEY'}
			<span class="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-neutral-500">
				{CURRENCY_SYMBOLS[localization.currency_code] ?? localization.currency_code}
			</span>
		{/if}
		<input
			type="number"
			step={field.data_type === 'INTEGER' ? 1 : 0.01}
			class={inputClass + (field.data_type === 'MONEY' ? ' pl-8' : '')}
			{disabled}
			value={value === undefined || value === null ? '' : String(value)}
			oninput={(e) => (value = e.currentTarget.value === '' ? undefined : Number(e.currentTarget.value))}
		/>
	</div>
{:else if control === 'date'}
	<input
		type="text"
		class={inputClass}
		{disabled}
		placeholder={localization.date_format.toLowerCase()}
		value={dateEditing ? dateBuffer : formatDateDisplay(value as string | undefined)}
		onfocus={beginDateEdit}
		oninput={(e) => (dateBuffer = e.currentTarget.value)}
		onblur={commitDateEdit}
		onkeydown={(e) => {
			if (e.key === 'Enter') e.currentTarget.blur();
		}}
	/>
{:else if control === 'time' || control === 'datetime'}
	<input
		type={control === 'datetime' ? 'datetime-local' : control}
		class={inputClass}
		{disabled}
		value={String(value ?? '')}
		oninput={(e) => (value = e.currentTarget.value || undefined)}
	/>
{:else if control === 'checkbox'}
	<Checkbox.Root
		checked={Boolean(value)}
		{disabled}
		onCheckedChange={(v) => (value = v)}
		class="flex h-5 w-5 items-center justify-center rounded border border-neutral-300 data-[state=checked]:bg-primary-600 dark:border-neutral-700"
	>
		{#snippet children({ checked })}
			{#if checked}<span class="text-xs text-white">✓</span>{/if}
		{/snippet}
	</Checkbox.Root>
{:else if control === 'switch'}
	<Switch.Root
		checked={Boolean(value)}
		{disabled}
		onCheckedChange={(v) => (value = v)}
		class="relative h-5 w-9 rounded-full bg-neutral-300 data-[state=checked]:bg-primary-600 dark:bg-neutral-700"
	>
		<Switch.Thumb class="block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-4" />
	</Switch.Root>
{:else if control === 'select'}
	<Select.Root
		type="single"
		value={value === undefined || value === null ? '' : String(value)}
		{disabled}
		onValueChange={(v) => (value = v || undefined)}
	>
		<Select.Trigger class={inputClass + ' flex items-center justify-between'}>
			{value ?? 'Select…'}
		</Select.Trigger>
		<Select.Portal>
			<Select.Content class="z-50 rounded-md border border-neutral-200 bg-white shadow-lg dark:border-neutral-700 dark:bg-neutral-900">
				{#each field.enum_values ?? [] as opt (opt)}
					<Select.Item value={opt} label={opt} class="cursor-pointer px-3 py-1.5 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800">
						{opt}
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Portal>
	</Select.Root>
{:else if control === 'lookup'}
	<Popover.Root bind:open={lookupOpen}>
		<Popover.Trigger
			class={inputClass + ' flex items-center justify-between text-left'}
			disabled={disabled || (!!field.lookup_filter && lookupFilterValue == null)}
		>
			<span class="truncate">
				{lookupSelectedLabel ??
					(value
						? String(value)
						: field.lookup_filter && lookupFilterValue == null
							? 'Select above first…'
							: 'Select…')}
			</span>
		</Popover.Trigger>
		<Popover.Portal>
			<Popover.Content class="z-50 w-72 rounded-md border border-neutral-200 bg-white p-1 shadow-lg dark:border-neutral-700 dark:bg-neutral-900">
				<input
					class="mb-1 h-8 w-full border-b border-neutral-200 px-2 text-sm outline-none dark:border-neutral-700"
					placeholder="Search…"
					bind:value={lookupSearch}
				/>
				<div class="max-h-64 overflow-y-auto">
					{#if lookupLoading}
						<div class="px-2 py-1.5 text-sm text-neutral-500">Loading…</div>
					{:else if lookupOptions.length === 0}
						<div class="px-2 py-1.5 text-sm text-neutral-500">No matches</div>
					{/if}
					{#each lookupOptions as opt (opt.value)}
						<button
							type="button"
							class="block w-full truncate rounded px-2 py-1.5 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
							onclick={() => {
								value = opt.value;
								lookupSelectedLabel = opt.label;
								lookupOpen = false;
							}}
						>
							{opt.label}
						</button>
					{/each}
				</div>
			</Popover.Content>
		</Popover.Portal>
	</Popover.Root>
{:else if control === 'file' || control === 'image'}
	<div class="flex items-center gap-2">
		{#if value && typeof value === 'object'}
			<span class="truncate text-sm">{(value as { name?: string }).name}</span>
			{#if !disabled}
				<button type="button" class="text-xs text-neutral-500 hover:text-red-600" onclick={() => (value = undefined)}>Remove</button>
			{/if}
		{:else}
			<label class="cursor-pointer rounded-md border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700">
				{uploading ? 'Uploading…' : control === 'image' ? 'Upload image' : 'Upload file'}
				<input type="file" class="hidden" accept={control === 'image' ? 'image/*' : undefined} {disabled} onchange={onFileSelected} />
			</label>
		{/if}
	</div>
{:else if control === 'json'}
	<div>
		<textarea
			class={inputClass + ' min-h-24 py-2 font-mono text-xs'}
			{disabled}
			value={jsonText}
			oninput={(e) => onJsonInput(e.currentTarget.value)}
		></textarea>
		{#if jsonError}<p class="mt-1 text-xs text-red-600">{jsonError}</p>{/if}
	</div>
{:else}
	<input
		type="text"
		class={inputClass}
		{disabled}
		maxlength={field.max_length}
		value={String(value ?? '')}
		oninput={(e) => (value = e.currentTarget.value)}
	/>
{/if}
