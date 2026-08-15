<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { api } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import type { FieldDataType, FieldMetadata, ModuleMetadata, ModuleRelationship, RelationshipType } from '$lib/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// svelte-ignore state_referenced_locally -- intentional one-time seed from the initial load() result
	let modules = $state<ModuleMetadata[]>(data.modules);
	// svelte-ignore state_referenced_locally
	let selectedName = $state<string | null>(modules[0]?.name ?? null);
	// svelte-ignore state_referenced_locally
	let draft = $state<ModuleMetadata | null>(structuredCloneModule(modules[0]));
	let activeTab = $state<'settings' | 'fields' | 'relationships' | 'workflow'>('settings');

	const WORKFLOW_COLORS = ['neutral', 'blue', 'green', 'amber', 'red', 'purple'] as const;

	function enumFields(): FieldMetadata[] {
		return draft?.fields.filter((f) => f.data_type === 'ENUM' && f.enum_values?.length) ?? [];
	}

	function enableWorkflow() {
		if (!draft) return;
		const firstEnum = enumFields()[0];
		draft.workflow = { field: firstEnum?.name ?? '', states: {}, transitions: {} };
		if (firstEnum) syncWorkflowStates(firstEnum.name);
	}

	function disableWorkflow() {
		if (!draft) return;
		draft.workflow = null;
	}

	/** Reconciles workflow.states/transitions with the chosen status field's
	 * current enum_values — adding defaults for new values, dropping ones
	 * that no longer exist, so the builder never holds a transition pointing
	 * at a value the enum was since edited to remove. */
	function syncWorkflowStates(fieldName: string) {
		if (!draft?.workflow) return;
		const field = draft.fields.find((f) => f.name === fieldName);
		const values = field?.enum_values ?? [];
		draft.workflow.field = fieldName;
		const states: Record<string, { color: string; locked: boolean }> = {};
		for (const v of values) {
			states[v] = draft.workflow.states[v] ?? { color: 'neutral', locked: false };
		}
		draft.workflow.states = states;
		const transitions: Record<string, string[]> = {};
		for (const v of values) {
			transitions[v] = (draft.workflow.transitions[v] ?? []).filter((t) => values.includes(t));
		}
		draft.workflow.transitions = transitions;
	}

	function toggleTransition(from: string, to: string) {
		if (!draft?.workflow) return;
		const current = draft.workflow.transitions[from] ?? [];
		draft.workflow.transitions[from] = current.includes(to) ? current.filter((t) => t !== to) : [...current, to];
	}
	let newModuleName = $state('');
	let saving = $state(false);
	let saveResult = $state<{ warnings: string[]; migration_written: string | null } | null>(null);
	let saveError = $state<string | null>(null);

	function structuredCloneModule(m?: ModuleMetadata): ModuleMetadata | null {
		return m ? JSON.parse(JSON.stringify(m)) : null;
	}

	function selectModule(name: string) {
		selectedName = name;
		draft = structuredCloneModule(modules.find((m) => m.name === name));
		saveResult = null;
		saveError = null;
	}

	function createModule() {
		const name = newModuleName.trim();
		if (!name) return;
		draft = { name, label: name, fields: [], relationships: [], version: 0 };
		selectedName = name;
		newModuleName = '';
		saveResult = null;
	}

	const DATA_TYPES: FieldDataType[] = [
		'TEXT', 'LONG_TEXT', 'RICH_TEXT', 'INTEGER', 'DECIMAL', 'MONEY', 'PERCENT',
		'DATE', 'TIME', 'DATETIME', 'BOOLEAN', 'ENUM', 'LOOKUP',
		'EMAIL', 'PHONE', 'URL', 'JSON', 'FILE', 'IMAGE', 'AUTO_NUMBER'
	];
	const REL_TYPES: RelationshipType[] = ['ONE_TO_MANY', 'ONE_TO_ONE', 'MANY_TO_MANY'];

	function addField() {
		if (!draft) return;
		draft.fields.push({
			name: `field_${draft.fields.length + 1}`,
			label: 'New field',
			data_type: 'TEXT',
			control_type: '',
			required: false,
			unique: false,
			read_only: false,
			is_default_flag: false,
			conditions: []
		} satisfies FieldMetadata);
	}
	function removeField(i: number) {
		draft?.fields.splice(i, 1);
	}

	type SeriesConfig = { prefix: string; pad_width: number; reset_policy: string; next_value: number };
	const seriesConfigs = $state<Record<string, SeriesConfig>>({});
	const seriesLoading = $state<Record<string, boolean>>({});
	const seriesSaving = $state<Record<string, boolean>>({});

	async function loadNumberSeries(fieldName: string) {
		if (!draft || seriesConfigs[fieldName] || seriesLoading[fieldName]) return;
		seriesLoading[fieldName] = true;
		try {
			seriesConfigs[fieldName] = await api.getNumberSeries(draft.name, fieldName);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to load number series config');
		} finally {
			seriesLoading[fieldName] = false;
		}
	}

	async function saveNumberSeries(fieldName: string) {
		if (!draft) return;
		const config = seriesConfigs[fieldName];
		if (!config) return;
		seriesSaving[fieldName] = true;
		try {
			seriesConfigs[fieldName] = await api.setNumberSeries(draft.name, fieldName, {
				prefix: config.prefix,
				pad_width: config.pad_width,
				reset_policy: config.reset_policy
			});
			toast.success(`Number series for "${fieldName}" saved`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save number series config');
		} finally {
			seriesSaving[fieldName] = false;
		}
	}

	function addRelationship() {
		if (!draft) return;
		draft.relationships.push({
			name: `relationship_${draft.relationships.length + 1}`,
			type: 'ONE_TO_MANY',
			related_module: '',
			foreign_key: `${draft.name}_id`,
			embedded: true,
			cascade_delete: true
		} satisfies ModuleRelationship);
	}
	function removeRelationship(i: number) {
		draft?.relationships.splice(i, 1);
	}

	async function save() {
		if (!draft) return;
		saving = true;
		saveError = null;
		saveResult = null;
		try {
			const result = await api.saveModule(draft.name, {
				name: draft.name,
				label: draft.label,
				fields: draft.fields,
				relationships: draft.relationships,
				workflow: draft.workflow ?? null,
				// Round-tripped even though this UI has no editor for them yet —
				// dropping these on every save would silently wipe FI posting,
				// clearing, stock, and document-flow config configured outside
				// the builder (e.g. via seed scripts) the moment anyone edits
				// even just a field label here.
				posting_rules: draft.posting_rules ?? null,
				clearing_config: draft.clearing_config ?? null,
				stock_rules: draft.stock_rules ?? null,
				document_flows: draft.document_flows ?? null,
				detail_actions: draft.detail_actions ?? null,
				create_guards: draft.create_guards ?? null,
				hidden: draft.hidden ?? false
			});
			saveResult = { warnings: result.warnings, migration_written: result.migration_written };
			modules = [...modules.filter((m) => m.name !== draft!.name), result.module];
			draft = structuredCloneModule(result.module);
			toast.success(`${result.module.label} saved`);
			// Refreshes the sidebar's module list (from the root +layout.ts
			// load) so a new/renamed module shows up in nav immediately.
			await invalidate('app:modules');
		} catch (e) {
			const message = e instanceof Error ? e.message : 'Save failed';
			saveError = message;
			toast.error(message);
		} finally {
			saving = false;
		}
	}

	const inputClass =
		'h-9 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900';
</script>

<div class="flex min-h-screen flex-col md:flex-row">
	<aside class="w-full shrink-0 border-b border-neutral-200 p-4 md:w-56 md:border-b-0 md:border-r dark:border-neutral-800">
		<h2 class="mb-3 text-xs font-semibold uppercase text-neutral-500">Modules</h2>
		<ul class="space-y-1">
			{#each modules as m (m.name)}
				<li>
					<button
						type="button"
						class="w-full rounded-md px-2 py-1.5 text-left text-sm {selectedName === m.name
							? 'bg-primary-50 font-medium text-primary-700 dark:bg-primary-950 dark:text-primary-300'
							: 'hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
						onclick={() => selectModule(m.name)}
					>
						{m.label}
						<span class="ml-1 text-xs text-neutral-400">{m.relationships.length} rel</span>
						{#if m.hidden}<span class="ml-1 text-xs text-neutral-400" title="Hidden from navigation">(hidden)</span>{/if}
					</button>
				</li>
			{/each}
		</ul>
		<div class="mt-4 flex gap-1">
			<input class={inputClass} placeholder="new_module_name" bind:value={newModuleName} />
			<button type="button" class="rounded-md bg-neutral-900 px-2 text-sm text-white dark:bg-neutral-100 dark:text-neutral-900" onclick={createModule}>+</button>
		</div>
	</aside>

	<main class="flex-1 p-6">
		{#if draft}
			<div class="mb-4 flex items-center justify-between">
				<h1 class="text-xl font-semibold">{draft.label || draft.name}</h1>
				<button
					type="button"
					disabled={saving}
					class="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
					onclick={save}
				>
					{saving ? 'Saving…' : 'Save module'}
				</button>
			</div>

			{#if saveError}<p class="mb-3 text-sm text-red-600">{saveError}</p>{/if}
			{#if saveResult}
				<div class="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950">
					{#if saveResult.migration_written}
						<p>Migration applied: <code>{saveResult.migration_written}</code></p>
					{/if}
					{#if saveResult.warnings.length}
						<p class="mt-1 font-medium text-amber-800 dark:text-amber-300">Not auto-applied — needs a manual migration:</p>
						<ul class="list-inside list-disc">
							{#each saveResult.warnings as w (w)}<li>{w}</li>{/each}
						</ul>
					{/if}
				</div>
			{/if}

			<div class="mb-4 flex gap-4 border-b border-neutral-200 dark:border-neutral-800">
				{#each [['settings', 'Settings'], ['fields', 'Fields'], ['relationships', 'Relationships'], ['workflow', 'Workflow']] as [key, label] (key)}
					<button
						type="button"
						class="border-b-2 px-1 pb-2 text-sm {activeTab === key
							? 'border-primary-600 font-medium text-primary-700 dark:text-primary-400'
							: 'border-transparent text-neutral-500'}"
						onclick={() => (activeTab = key as typeof activeTab)}
					>
						{label}
					</button>
				{/each}
			</div>

			{#if activeTab === 'settings'}
				<div class="max-w-md space-y-3">
					<div>
						<label class="mb-1 block text-sm font-medium" for="mod-name">Name</label>
						<input id="mod-name" class={inputClass} bind:value={draft.name} disabled={draft.version > 0} />
					</div>
					<div>
						<label class="mb-1 block text-sm font-medium" for="mod-label">Label</label>
						<input id="mod-label" class={inputClass} bind:value={draft.label} />
					</div>
					<label class="flex items-center gap-2 text-sm">
						<input type="checkbox" bind:checked={draft.hidden} />
						Hidden from navigation
					</label>
					<p class="text-xs text-neutral-400">
						Hides this module from the sidebar and the top-level Modules list. The module and its data stay fully
						functional — use this for child-only modules (line items) or reference data nobody browses directly.
					</p>
				</div>
			{:else if activeTab === 'fields'}
				<div class="space-y-2">
					{#each draft.fields as field, i (i)}
						<div class="grid grid-cols-12 items-center gap-2 rounded-md border border-neutral-200 p-2 dark:border-neutral-800">
							<input class={inputClass + ' col-span-2'} placeholder="name" bind:value={field.name} />
							<input class={inputClass + ' col-span-2'} placeholder="label" bind:value={field.label} />
							<select class={inputClass + ' col-span-2'} bind:value={field.data_type}>
								{#each DATA_TYPES as t (t)}<option value={t}>{t}</option>{/each}
							</select>
							{#if field.data_type === 'LOOKUP'}
								<input class={inputClass + ' col-span-2'} placeholder="lookup_module" bind:value={field.lookup_module} />
							{:else if field.data_type === 'ENUM'}
								<input
									class={inputClass + ' col-span-2'}
									placeholder="a,b,c"
									value={(field.enum_values ?? []).join(',')}
									oninput={(e) => (field.enum_values = e.currentTarget.value.split(',').map((s) => s.trim()).filter(Boolean))}
								/>
							{:else}
								<div class="col-span-2"></div>
							{/if}
							<label class="col-span-2 flex items-center gap-1 text-xs">
								<input type="checkbox" bind:checked={field.required} /> required
							</label>
							<button type="button" class="col-span-2 text-right text-xs text-red-600 hover:underline" onclick={() => removeField(i)}>
								Remove
							</button>
							{#if field.data_type === 'BOOLEAN'}
								<label class="col-span-12 flex items-center gap-1 text-xs text-neutral-500">
									<input type="checkbox" bind:checked={field.is_default_flag} />
									Default flag — only one record in this module may have this set; saving one unsets the previous default
								</label>
							{/if}
							{#if field.data_type === 'AUTO_NUMBER'}
								<div class="col-span-12 rounded-md border border-neutral-200 bg-neutral-50 p-2 dark:border-neutral-800 dark:bg-neutral-900">
									{#if !seriesConfigs[field.name] && !seriesLoading[field.name]}
										<button
											type="button"
											class="text-xs text-primary-600 hover:underline"
											onclick={() => loadNumberSeries(field.name)}
										>
											Configure number series (prefix / padding / reset)
										</button>
									{:else if seriesLoading[field.name]}
										<p class="text-xs text-neutral-400">Loading…</p>
									{:else if seriesConfigs[field.name]}
										{@const config = seriesConfigs[field.name]}
										<div class="flex flex-wrap items-end gap-3">
											<label class="text-xs">
												<span class="mb-0.5 block text-neutral-500">Prefix</span>
												<input class={inputClass + ' w-24'} bind:value={config.prefix} placeholder="PO-" />
											</label>
											<label class="text-xs">
												<span class="mb-0.5 block text-neutral-500">Pad width</span>
												<input type="number" min="1" max="12" class={inputClass + ' w-20'} bind:value={config.pad_width} />
											</label>
											<label class="text-xs">
												<span class="mb-0.5 block text-neutral-500">Reset</span>
												<select class={inputClass + ' w-28'} bind:value={config.reset_policy}>
													<option value="never">Never</option>
													<option value="yearly">Yearly</option>
													<option value="monthly">Monthly</option>
												</select>
											</label>
											<span class="text-xs text-neutral-400">
												Next: {config.prefix}{String(config.next_value).padStart(config.pad_width, '0')}
											</span>
											<button
												type="button"
												disabled={seriesSaving[field.name]}
												onclick={() => saveNumberSeries(field.name)}
												class="rounded-md bg-primary-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-primary-700 disabled:opacity-50"
											>
												{seriesSaving[field.name] ? 'Saving…' : 'Save series'}
											</button>
										</div>
										<p class="mt-1 text-xs text-neutral-400">
											Applies once this module and field are saved — new records get "{config.prefix}00001"-style values automatically.
										</p>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
					<button type="button" class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700" onclick={addField}>
						+ Add field
					</button>
				</div>
			{:else if activeTab === 'relationships'}
				<div class="space-y-2">
					{#each draft.relationships as rel, i (i)}
						<div class="grid grid-cols-12 items-center gap-2 rounded-md border border-neutral-200 p-2 dark:border-neutral-800">
							<input class={inputClass + ' col-span-2'} placeholder="name" bind:value={rel.name} />
							<select class={inputClass + ' col-span-2'} bind:value={rel.type}>
								{#each REL_TYPES as t (t)}<option value={t}>{t}</option>{/each}
							</select>
							<input class={inputClass + ' col-span-2'} placeholder="related_module" bind:value={rel.related_module} />
							<input class={inputClass + ' col-span-2'} placeholder="foreign_key (e.g. order_id)" bind:value={rel.foreign_key} />
							<label class="col-span-2 flex items-center gap-1 text-xs">
								<input type="checkbox" bind:checked={rel.embedded} /> embedded grid
							</label>
							<label class="col-span-1 flex items-center gap-1 text-xs">
								<input type="checkbox" bind:checked={rel.cascade_delete} /> cascade
							</label>
							<button type="button" class="col-span-1 text-right text-xs text-red-600 hover:underline" onclick={() => removeRelationship(i)}>
								Remove
							</button>
						</div>
					{/each}
					<button type="button" class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700" onclick={addRelationship}>
						+ Add relationship
					</button>
					<p class="text-xs text-neutral-500">
						An embedded ONE_TO_MANY relationship renders as an inline line-item grid on the parent's detail page
						(e.g. Order → Order Items) and adds a typed <code>foreign_key</code> column with a real FK constraint
						on the related module's table when saved.
					</p>
				</div>
			{:else if activeTab === 'workflow'}
				<div class="max-w-3xl space-y-4">
					{#if !draft.workflow}
						{#if enumFields().length === 0}
							<p class="text-sm text-neutral-500">
								Add an ENUM field first (e.g. "status") — workflows track transitions between that field's values.
							</p>
						{:else}
							<button type="button" class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700" onclick={enableWorkflow}>
								+ Enable workflow
							</button>
						{/if}
					{:else}
						{@const wf = draft.workflow}
						<div class="flex items-center gap-3">
							<label class="text-sm">
								<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Status field</span>
								<select class={inputClass} value={wf.field} onchange={(e) => syncWorkflowStates(e.currentTarget.value)}>
									{#each enumFields() as f (f.name)}
										<option value={f.name}>{f.label} ({f.name})</option>
									{/each}
								</select>
							</label>
							<button type="button" class="mt-5 text-xs text-red-600 hover:underline" onclick={disableWorkflow}>
								Disable workflow
							</button>
						</div>

						<div>
							<h3 class="mb-2 text-xs font-semibold uppercase text-neutral-500">States</h3>
							<div class="space-y-2">
								{#each Object.keys(wf.states) as stateName (stateName)}
									<div class="flex items-center gap-3 rounded-md border border-neutral-200 p-2 dark:border-neutral-800">
										<span class="w-32 text-sm font-medium">{stateName}</span>
										<label class="flex items-center gap-1 text-xs text-neutral-500">
											Color
											<select class="rounded-md border border-neutral-300 px-2 py-1 text-xs dark:border-neutral-700 dark:bg-neutral-900" bind:value={wf.states[stateName].color}>
												{#each WORKFLOW_COLORS as c (c)}<option value={c}>{c}</option>{/each}
											</select>
										</label>
										<label class="flex items-center gap-1 text-xs text-neutral-500">
											<input type="checkbox" bind:checked={wf.states[stateName].locked} />
											Locked (blocks editing other fields)
										</label>
									</div>
								{/each}
							</div>
						</div>

						<div>
							<h3 class="mb-2 text-xs font-semibold uppercase text-neutral-500">Transitions</h3>
							<p class="mb-2 text-xs text-neutral-500">For each state, which states can it move to?</p>
							<div class="space-y-2">
								{#each Object.keys(wf.states) as fromState (fromState)}
									<div class="rounded-md border border-neutral-200 p-2 dark:border-neutral-800">
										<span class="mb-1 block text-sm font-medium">{fromState} →</span>
										<div class="flex flex-wrap gap-2">
											{#each Object.keys(wf.states).filter((s) => s !== fromState) as toState (toState)}
												<label class="flex items-center gap-1 text-xs">
													<input
														type="checkbox"
														checked={(wf.transitions[fromState] ?? []).includes(toState)}
														onchange={() => toggleTransition(fromState, toState)}
													/>
													{toState}
												</label>
											{/each}
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}
		{:else}
			<p class="text-neutral-500">Select or create a module.</p>
		{/if}
	</main>
</div>
