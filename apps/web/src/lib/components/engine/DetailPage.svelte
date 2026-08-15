<script module lang="ts">
	import type EmbeddedGridComponentType from './EmbeddedGrid.svelte';
	// Shared across every DetailPage instance in this session, so the AG
	// Grid chunk is fetched at most once even when navigating between
	// several modules that each have embedded relationships.
	let _cachedEmbeddedGrid: typeof EmbeddedGridComponentType | null = null;
</script>

<script lang="ts">
	import { beforeNavigate, goto } from '$app/navigation';
	import { DropdownMenu } from 'bits-ui';
	import { api, ConflictError } from '$lib/api';
	import { displayName, embeddedChildren, emptyChildDiff } from '$lib/types';
	import type { ModuleMetadata, RecordRow } from '$lib/types';
	import { toast } from '$lib/toast.svelte';
	import DataForm from './DataForm.svelte';
	import HistoryPanel from './HistoryPanel.svelte';
	import WorkflowBar from './WorkflowBar.svelte';
	import DocumentFlowActions from './DocumentFlowActions.svelte';
	import PullLinesAction from './PullLinesAction.svelte';
	import ConfirmDialog from '$lib/components/ui/ConfirmDialog.svelte';
	// Type-only import — erased at compile time, so it doesn't pull AG Grid
	// into every detail page's bundle. The runtime component is loaded via
	// dynamic import() below, only when this module actually has an
	// embedded relationship (see the AG Grid perf note further down).
	import type EmbeddedGridComponent from './EmbeddedGrid.svelte';

	let {
		module,
		childModules,
		record,
		onCreated
	}: {
		module: ModuleMetadata;
		/** Metadata for every embedded child module, keyed by module name. */
		childModules: Record<string, ModuleMetadata>;
		record?: RecordRow;
		/** Only fired on create — edit-mode save stays on the page (see save()). */
		onCreated?: (record: RecordRow) => void;
	} = $props();

	const mode = $derived(record ? 'edit' : 'create');
	// Mirrors the server's _check_not_locked_for_delete: a posted/approved
	// document (may already have a GL posting or payments against it) must
	// never be deletable, only reversible via a status transition. This is
	// a UX affordance only — the server is the real enforcement point.
	const isLocked = $derived.by(() => {
		if (!module.workflow) return false;
		const current = values[module.workflow.field] as string | undefined;
		return !!(current && module.workflow.states[current]?.locked);
	});
	// Record-lifecycle actions (New/Save & New/Save & Close/Duplicate) are
	// framework-level defaults — every module gets them with zero config.
	// `module.detail_actions.disable` is opt-*out* only, never opt-in; see
	// the field's doc comment in domain/metadata.py.
	function actionEnabled(name: 'new' | 'save_and_new' | 'save_and_close' | 'duplicate'): boolean {
		return !module.detail_actions?.disable?.includes(name);
	}

	// svelte-ignore state_referenced_locally -- this instance's module never changes (a module switch remounts via the parent route's {#key})
	const DUPLICATE_SEED_KEY = `mf:duplicate:${module.name}`;

	// svelte-ignore state_referenced_locally -- intentional one-time seed of local editable state from the initial prop
	let values = $state<Record<string, unknown>>(
		record
			? { ...record }
			: // A pending Duplicate (see duplicate() below) leaves its blanked-out
				// copy here for exactly the next "/new" page to pick up — read-and-
				// clear so a later, unrelated "/new" visit never inherits it.
				(() => {
					if (typeof sessionStorage === 'undefined') return {};
					const raw = sessionStorage.getItem(DUPLICATE_SEED_KEY);
					if (!raw) return {};
					sessionStorage.removeItem(DUPLICATE_SEED_KEY);
					try {
						return JSON.parse(raw);
					} catch {
						return {};
					}
				})()
	);
	let errors = $state<Record<string, string>>({});
	let formRef: DataForm | undefined;
	let saving = $state(false);
	let saveError = $state<string | null>(null);
	let deleteOpen = $state(false);

	// Dirty tracking: snapshot the last-saved state, compare current values
	// against it. Lets the save bar show "Unsaved changes", disable Save
	// when there's nothing to save, and guard against navigating away with
	// unsaved edits. Edit mode only: in create mode, `DataForm` seeds field
	// defaults into `values` in its own effect *after* this component's
	// initial snapshot is taken, which made every fresh "New X" page report
	// dirty=true before the user had touched anything.
	// svelte-ignore state_referenced_locally
	let savedSnapshot = $state(JSON.stringify(record ?? {}));
	let childrenDirty = $state(false);
	const dirty = $derived(mode === 'edit' && (JSON.stringify(values) !== savedSnapshot || childrenDirty));

	const rels = $derived(embeddedChildren(module));

	// AG Grid Community is a large dependency (the single biggest chunk in
	// the app). Most modules (Customers, Vendors, ...) have no embedded
	// child grid at all, so importing EmbeddedGrid statically made every
	// detail-page navigation pay AG Grid's load cost even when nothing on
	// the page uses it. Load it only when this module actually has an
	// embedded relationship, and only once per session (module-level cache).
	let EmbeddedGrid = $state<typeof EmbeddedGridComponent | null>(_cachedEmbeddedGrid);
	$effect(() => {
		if (rels.length > 0 && !EmbeddedGrid) {
			import('./EmbeddedGrid.svelte').then((m) => {
				_cachedEmbeddedGrid = m.default;
				EmbeddedGrid = m.default;
			});
		}
	});

	// Each embedded relationship gets its own child-row array + grid instance ref,
	// fetched once when a `record` (edit mode) is present.
	const childRows = $state<Record<string, Record<string, unknown>[]>>({});
	const gridRefs: Record<string, EmbeddedGridComponent> = {};

	$effect.pre(() => {
		for (const rel of rels) {
			if (!(rel.name in childRows)) childRows[rel.name] = [];
		}
	});

	$effect(() => {
		if (!record) return;
		for (const rel of rels) {
			fetch(`/api/data/${rel.related_module}?${rel.foreign_key}=${record.id}`)
				.then((r) => (r.ok ? r.json() : []))
				.then((data) => {
					childRows[rel.name] = Array.isArray(data) ? data : (data.items ?? []);
				});
		}
	});

	beforeNavigate((nav) => {
		if (!dirty) return;
		if (!confirm('You have unsaved changes. Leave without saving?')) {
			nav.cancel();
		}
	});

	function discard() {
		values = JSON.parse(savedSnapshot);
		childrenDirty = false;
		errors = {};
	}

	/** `after` picks what happens once the save itself succeeds:
	 *  - 'stay' (default): create → the newly-created record's own page
	 *    (via onCreated, unchanged); edit → stays put, refreshed from the
	 *    server response.
	 *  - 'new': Save & New — jump straight to a blank create form for this
	 *    same module, the fix for rapid consecutive data entry.
	 *  - 'close': Save & Close — back to the list.
	 * All three mark the record clean *before* navigating so the dirty-edit
	 * guard in beforeNavigate never asks "leave without saving?" about
	 * changes that were, in fact, just saved. */
	async function save(after: 'stay' | 'new' | 'close' = 'stay') {
		saveError = null;
		if (!formRef?.validate()) return;
		// Embedded grids can't fully express "this row is missing a required
		// field" as a blocking error the way the flat form's Zod schema does
		// — a row with some but not all required fields filled in used to
		// sail straight through to the backend's NOT NULL columns and come
		// back as an opaque 500. Check every grid before ever calling the
		// API, matching formRef.validate()'s "stop before the network call"
		// contract.
		for (const rel of rels) {
			const gridError = gridRefs[rel.name]?.validate();
			if (gridError) {
				saveError = gridError;
				toast.error(gridError);
				return;
			}
		}
		saving = true;
		try {
			const children: Record<string, ReturnType<EmbeddedGridComponent['getChanges']>> = {};
			for (const rel of rels) {
				children[rel.name] = gridRefs[rel.name]?.getChanges() ?? emptyChildDiff();
			}
			const saved =
				mode === 'create'
					? await api.createRecord(module.name, values, children)
					: await api.updateRecord(module.name, record!.id, values, children);

			values = { ...saved };
			savedSnapshot = JSON.stringify(saved);
			childrenDirty = false;
			toast.success(mode === 'create' ? `${module.label} created` : 'Saved');

			if (after === 'new') {
				await goto(`/${module.name}/new`);
				// Navigating create -> create keeps the same route (`.../new`
				// before and after), so the parent route's {#key} never
				// changes and this component instance survives instead of
				// remounting — unlike edit -> create, which does get a fresh
				// instance for free. Reset local state explicitly so both
				// paths land on a genuinely blank form either way.
				values = {};
				errors = {};
				saveError = null;
				savedSnapshot = JSON.stringify({});
				childrenDirty = false;
				for (const rel of rels) childRows[rel.name] = [];
				return;
			}
			if (after === 'close') {
				await goto(`/${module.name}`);
				return;
			}
			if (mode === 'create') {
				// Default create-mode landing: the new record's own page, via
				// the parent route's callback (unchanged from before this
				// feature — see routes/[module]/[id]/+page.svelte).
				onCreated?.(saved);
			}
			// Edit-mode 'stay' falls through to here with nothing left to do —
			// values/savedSnapshot are already refreshed above.
		} catch (e) {
			if (e instanceof ConflictError) {
				// Someone else saved this record first. Discard this edit and
				// load the server's current version rather than risk the user
				// re-saving over it — they can redo their change from there.
				if (e.current) {
					values = { ...e.current };
					savedSnapshot = JSON.stringify(e.current);
					childrenDirty = false;
				}
				saveError = e.message;
				toast.error(`${e.message} Your edit was not saved — please reapply it.`);
				return;
			}
			const message = e instanceof Error ? e.message : 'Save failed';
			saveError = message;
			toast.error(message);
		} finally {
			saving = false;
		}
	}

	function onTransitioned(updated: RecordRow) {
		values = { ...updated };
		savedSnapshot = JSON.stringify(updated);
	}

	async function confirmDelete() {
		if (!record) return;
		try {
			await api.deleteRecord(module.name, record.id);
			toast.success(`${module.label} deleted`);
			await goto(`/${module.name}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Delete failed');
		}
	}

	/** The workflow state a duplicate should start in — never the source
	 * record's own current status (a duplicate of a posted invoice is a new
	 * draft, not a second posted invoice). Heuristic: the state nothing else
	 * ever transitions *into* is the entry point; every module's workflow
	 * this framework has (draft → ... ) fits that shape. Falls back to the
	 * first unlocked state if every state has an incoming transition (a
	 * workflow with a cycle, which none currently have, but this shouldn't
	 * throw on one). */
	function initialWorkflowState(): string | undefined {
		const workflow = module.workflow;
		if (!workflow) return undefined;
		const targets = new Set(Object.values(workflow.transitions).flat());
		const root = Object.keys(workflow.states).find((s) => !targets.has(s));
		if (root) return root;
		return Object.entries(workflow.states).find(([, cfg]) => !cfg.locked)?.[0];
	}

	/** Duplicate: seeds a blank create form with this record's field values
	 * (minus anything that can't or shouldn't carry over), then hands off to
	 * "/new" via sessionStorage — see the `values` initializer above for the
	 * read side. Deliberately does NOT persist anything itself; the user
	 * reviews/edits the copy before it's ever saved, unlike a
	 * duplicate-and-immediately-save pattern. */
	function duplicate() {
		if (!record) return;
		const seed: Record<string, unknown> = {};
		for (const f of module.fields) {
			if (f.read_only || f.data_type === 'AUTO_NUMBER') continue; // server-owned or regenerated
			if (f.unique) continue; // would collide with the source record — user must retype
			if (f.is_default_flag) {
				seed[f.name] = false; // only one record may hold the default flag
				continue;
			}
			seed[f.name] = values[f.name];
		}
		const initialStatus = initialWorkflowState();
		if (module.workflow && initialStatus) seed[module.workflow.field] = initialStatus;
		sessionStorage.setItem(DUPLICATE_SEED_KEY, JSON.stringify(seed));
		toast.success(`Duplicating ${displayName(values, module.label)} — review and save the copy`);
		goto(`/${module.name}/new`);
	}
</script>

<div class="mx-auto max-w-4xl space-y-6 p-6 pb-24">
	<div class="flex items-center justify-between gap-3">
		<div class="flex min-w-0 items-center gap-2">
			<!-- Explicit "back to list" — the breadcrumb link in the topbar
			     covers the same navigation but is easy to miss; every ERP this
			     framework is modeled on (SAP/Odoo/NetSuite) gives it its own
			     affordance right next to the record title. Plain <a> so
			     SvelteKit's beforeNavigate dirty-edit guard (already wired
			     above) covers it for free — no separate confirm needed here. -->
			<a
				href={`/${module.name}`}
				aria-label={`Back to ${module.label}`}
				title={`Back to ${module.label}`}
				class="shrink-0 rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
			>
				←
			</a>
			<h1 class="min-w-0 truncate text-xl font-semibold">
				{mode === 'create' ? `New ${module.label}` : displayName(values, module.label)}
			</h1>
		</div>
		{#if mode === 'edit'}
			<div class="flex shrink-0 items-center gap-2">
				{#if actionEnabled('new')}
					<!-- Plain <a>, not a goto() button, for the same dirty-guard-for-free reason as Back. -->
					<a
						href={`/${module.name}/new`}
						class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
					>
						New
					</a>
				{/if}
				<!-- Delete lives here unconditionally — the overflow menu itself
				     isn't a disableable action, only the Duplicate entry inside it. -->
				<DropdownMenu.Root>
						<DropdownMenu.Trigger
							aria-label="More actions"
							class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
						>
							⋯
						</DropdownMenu.Trigger>
						<DropdownMenu.Portal>
							<DropdownMenu.Content
								class="z-50 w-44 rounded-md border border-neutral-200 bg-white p-1 shadow-xl dark:border-neutral-800 dark:bg-neutral-900"
								align="end"
								sideOffset={6}
							>
								{#if actionEnabled('duplicate')}
									<button
										type="button"
										onclick={duplicate}
										class="flex w-full items-center rounded-md px-2 py-1.5 text-left text-sm text-neutral-700 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
									>
										Duplicate
									</button>
								{/if}
								<button
									type="button"
									disabled={isLocked}
									onclick={() => (deleteOpen = true)}
									title={isLocked ? 'Locked — this record cannot be deleted once posted/approved' : undefined}
									class="flex w-full items-center rounded-md px-2 py-1.5 text-left text-sm text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent dark:hover:bg-red-950"
								>
									Delete
								</button>
							</DropdownMenu.Content>
					</DropdownMenu.Portal>
				</DropdownMenu.Root>
			</div>
		{/if}
	</div>

	{#if mode === 'edit' && module.workflow}
		<WorkflowBar {module} record={values as RecordRow} {onTransitioned} />
	{/if}

	{#if mode === 'edit' && module.document_flows?.length}
		<DocumentFlowActions {module} record={values as RecordRow} />
	{/if}

	{#if rels.length > 0 && !isLocked}
		<PullLinesAction {module} {values} {childRows} />
	{/if}

	<div class="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
		<h2 class="mb-4 text-sm font-semibold text-neutral-500">Details</h2>
		<DataForm bind:this={formRef} {module} {values} bind:errors {childRows} {childModules} />
	</div>

	{#each rels as rel (rel.name)}
		{@const childModule = childModules[rel.related_module]}
		{#if childModule}
			<div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
				<h2 class="mb-3 text-sm font-semibold text-neutral-500">
					{childModule.label} <span class="font-normal text-neutral-400">({childRows[rel.name]?.length ?? 0})</span>
				</h2>
				{#if EmbeddedGrid}
					<EmbeddedGrid
						bind:this={gridRefs[rel.name]}
						{childModule}
						fkField={rel.foreign_key}
						bind:rows={childRows[rel.name]}
						onChange={() => (childrenDirty = true)}
						headerValues={values}
					/>
				{:else}
					<p class="text-sm text-neutral-400">Loading grid…</p>
				{/if}
			</div>
		{/if}
	{/each}

	{#if mode === 'edit' && record}
		<HistoryPanel module={module.name} recordId={record.id} />
	{/if}

	{#if saveError}
		<p class="text-sm text-red-600">{saveError}</p>
	{/if}
</div>

<div
	class="sticky bottom-0 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white/90 px-6 py-3 backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/90"
>
	{#if dirty}
		<span class="mr-auto text-sm text-amber-600 dark:text-amber-400">Unsaved changes</span>
		{#if mode === 'edit'}
			<button type="button" onclick={discard} class="rounded-md px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800">
				Discard
			</button>
		{/if}
	{/if}
	{#if actionEnabled('save_and_close')}
		<button
			type="button"
			disabled={saving || (mode === 'edit' && !dirty)}
			class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
			onclick={() => save('close')}
		>
			Save & Close
		</button>
	{/if}
	{#if actionEnabled('save_and_new')}
		<button
			type="button"
			disabled={saving || (mode === 'edit' && !dirty)}
			class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
			onclick={() => save('new')}
		>
			Save & New
		</button>
	{/if}
	<button
		type="button"
		disabled={saving || (mode === 'edit' && !dirty)}
		class="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
		onclick={() => save()}
	>
		{saving ? 'Saving…' : mode === 'create' ? 'Create' : 'Save changes'}
	</button>
</div>

<ConfirmDialog
	bind:open={deleteOpen}
	title={`Delete ${displayName(values, module.label)}?`}
	description="This cannot be undone."
	confirmLabel="Delete"
	danger
	onConfirm={confirmDelete}
/>
