<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { FieldMetadata, ModuleMetadata } from '$lib/types';
	import { defaultsOf, evaluateCondition, moduleValidationSchema } from '$lib/validation';
	import { evaluate_formula_safe } from '$lib/formula';
	import { formatDecimal, formatMoney, formatPercent } from '$lib/format';
	import FieldControl from './FieldControl.svelte';

	let {
		module,
		values = $bindable(),
		readOnly = false,
		errors = $bindable({}),
		embeddedGrids,
		childRows,
		childModules
	}: {
		module: ModuleMetadata;
		values: Record<string, unknown>;
		readOnly?: boolean;
		errors?: Record<string, string>;
		embeddedGrids?: Snippet;
		/** Current (possibly unsaved) rows for each embedded child relationship, keyed
		 * by relationship name — lets a header aggregate field (e.g. "Subtotal") show a
		 * live total computed from the grid instead of sitting empty until the record
		 * is actually saved and the server recomputes it. */
		childRows?: Record<string, Record<string, unknown>[]>;
		childModules?: Record<string, ModuleMetadata>;
	} = $props();

	// Seed defaults exactly once. Gating on `values` being empty doesn't
	// terminate: when a module's fields have no defaults at all,
	// `defaultsOf()` returns `{}`, so `Object.assign(values, {})` still
	// writes to the $state proxy every run and re-triggers this effect
	// forever (effect_update_depth_exceeded). A plain non-reactive flag
	// guarantees it only ever runs on mount.
	let seeded = false;
	$effect.pre(() => {
		if (!seeded) {
			seeded = true;
			// Only fill in keys the record doesn't already have a value for —
			// edit mode seeds `values` from the saved record before this runs,
			// and a default must never clobber an already-saved value.
			for (const [key, value] of Object.entries(defaultsOf(module))) {
				if (values[key] === undefined) values[key] = value;
			}
		}
	});

	function isVisible(field: FieldMetadata): boolean {
		return evaluateCondition(field, values, 'then_visible') ?? true;
	}
	// A workflow's status field must only ever change via WorkflowBar's
	// transition action (which runs posting_rules/stock_rules/three-way-
	// match) — the server now rejects a plain update() that touches it (see
	// repository._check_workflow_lock). Rendering it as an ordinary editable
	// ENUM select on an existing record invited exactly that: pick "posted"
	// from the dropdown, hit Save, and the record ends up in its
	// trigger_status with none of the side effects the status is supposed
	// to guarantee (a posted GR with no GR/IR journal entry, not a
	// posting-config bug). `values.id` is only set once a record is loaded
	// from the server — a fresh create-mode draft still needs to set its
	// own initial status.
	function isWorkflowStatusField(field: FieldMetadata): boolean {
		return module.workflow?.field === field.name && values.id !== undefined;
	}
	function isReadOnly(field: FieldMetadata): boolean {
		return (
			field.read_only ||
			readOnly ||
			isWorkflowStatusField(field) ||
			(evaluateCondition(field, values, 'then_read_only') ?? false)
		);
	}
	function isRequired(field: FieldMetadata): boolean {
		return field.required && (evaluateCondition(field, values, 'then_required') ?? true);
	}

	export function validate(): boolean {
		const schema = moduleValidationSchema(module);
		const result = schema.safeParse(values);
		if (result.success) {
			errors = {};
			return true;
		}
		const next: Record<string, string> = {};
		for (const issue of result.error.issues) {
			next[String(issue.path[0])] = issue.message;
		}
		errors = next;
		return false;
	}

	// A statically computed field — AUTO_NUMBER, a formula, an aggregate, or
	// anything the builder marked permanently read_only — is reference
	// info, not something a user fills in. Interleaved among real inputs
	// (worse, first in field order, as Invoice No. was) it makes the form
	// look like it starts with a locked field blocking data entry. Fields a
	// user actually needs to type into always render first; computed ones
	// move to their own de-emphasized section below, in original order
	// within each group so a builder-authored ordering still means
	// something.
	function isSystemField(f: FieldMetadata): boolean {
		return f.data_type === 'AUTO_NUMBER' || !!f.formula || !!f.aggregate || f.read_only;
	}
	const allFields = $derived(module.fields.filter((f) => f.name !== 'id'));
	const fields = $derived(allFields.filter((f) => !isSystemField(f)));
	const systemFields = $derived(allFields.filter((f) => isSystemField(f)));

	// Layout only (see FieldMetadata.group's doc comment): ungrouped fields
	// stay in today's single flat list; grouped fields bucket into titled
	// sections below it, in first-encountered order so the builder's field
	// ordering still controls section order, not an alphabetized one.
	const ungroupedFields = $derived(fields.filter((f) => !f.group));
	const groupedSections = $derived.by(() => {
		const order: string[] = [];
		const buckets = new Map<string, FieldMetadata[]>();
		for (const f of fields) {
			if (!f.group) continue;
			if (!buckets.has(f.group)) {
				buckets.set(f.group, []);
				order.push(f.group);
			}
			buckets.get(f.group)!.push(f);
		}
		return order.map((name) => ({ name, fields: buckets.get(name)! }));
	});

	/** Resolves every formula field on a child row into an accumulating
	 * object, in module-field-declaration order, so a formula that depends
	 * on another formula field (tax_amount = line_total * tax_rate / 100,
	 * where line_total = qty * unit_price) sees the dependency's computed
	 * value instead of undefined. Mirrors EmbeddedGrid's own
	 * withComputedFormulas so this live header preview agrees with what the
	 * grid displays. */
	function resolveChildFormulas(childModule: ModuleMetadata | undefined, row: Record<string, unknown>): Record<string, unknown> {
		if (!childModule) return row;
		const out: Record<string, unknown> = { ...row };
		for (const f of childModule.fields) {
			if (!f.formula) continue;
			const value = evaluate_formula_safe(f.formula, out);
			out[f.name] = value === '' ? null : Number(value);
		}
		return out;
	}

	/** Live-computes a header aggregate field (e.g. Subtotal = sum of the
	 * embedded lines' line_total) from the grid's current in-memory rows,
	 * the same way EmbeddedGrid's own pinned totals row does — so the
	 * header field reflects what's actually in the grid right now instead
	 * of sitting empty/stale until the record round-trips through a save. */
	function liveAggregateValue(field: FieldMetadata): number | undefined {
		const agg = field.aggregate;
		if (!agg || !childRows) return undefined;
		const rel = module.relationships.find((r) => r.related_module === agg.from_module && r.foreign_key === agg.foreign_key);
		if (!rel) return undefined;
		const rows = childRows[rel.name];
		if (!rows) return undefined;
		const filtered = agg.filter_field
			? rows.filter((r) => String(r[agg.filter_field!]) === String(agg.filter_value))
			: rows;
		if (agg.op === 'count') return filtered.length;
		const childModule = childModules?.[agg.from_module];
		const nums = filtered.map((r) => {
			// A source field can itself be a formula that depends on *another*
			// formula field on the same line (tax_amount = line_total *
			// tax_rate / 100, where line_total = qty * unit_price) — resolving
			// every formula field on the row first, in declaration order,
			// mirrors EmbeddedGrid's own withComputedFormulas so this preview
			// agrees with what the grid itself displays instead of treating
			// an unresolved dependency as 0. Same root cause as the
			// backend's apply_formulas fix, just the client-side twin of it.
			const resolved = resolveChildFormulas(childModule, r);
			const raw = Number(resolved[agg.source_field] ?? 0);
			return Number.isFinite(raw) ? raw : 0;
		});
		if (nums.length === 0) return agg.op === 'sum' ? 0 : undefined;
		switch (agg.op) {
			case 'sum':
				return nums.reduce((a, b) => a + b, 0);
			case 'avg':
				return nums.reduce((a, b) => a + b, 0) / nums.length;
			case 'min':
				return Math.min(...nums);
			case 'max':
				return Math.max(...nums);
			default:
				return undefined;
		}
	}

	/** Resolves every system-generated field (aggregate or formula) into an
	 * accumulating object, in module-field-declaration order, before any of
	 * them are displayed. A header formula field can depend on an aggregate
	 * field declared earlier (grand_total = total + tax_total, where total
	 * and tax_total are both aggregates) — evaluating it against the raw
	 * `values` object misses that, since aggregates are computed live and
	 * never written back into `values`. Same bug class as
	 * resolveChildFormulas/withComputedFormulas, one level up. */
	const liveSystemValues = $derived.by(() => {
		const out: Record<string, unknown> = { ...values };
		for (const f of systemFields) {
			if (f.aggregate) {
				out[f.name] = liveAggregateValue(f) ?? values[f.name];
			} else if (f.formula) {
				const v = evaluate_formula_safe(f.formula, out);
				out[f.name] = v === '' ? null : v;
			}
		}
		return out;
	});

	function formatComputed(field: FieldMetadata, value: unknown): string {
		if (value === undefined || value === null || value === '') return '';
		if (field.data_type === 'MONEY') return formatMoney(value);
		if (field.data_type === 'PERCENT') return formatPercent(value);
		if (field.data_type === 'DECIMAL') return formatDecimal(value, field.scale ?? 2);
		return String(value);
	}
</script>

{#snippet fieldInput(field: FieldMetadata)}
	<div class="col-span-1">
		<label for={field.name} class="mb-1.5 block text-sm font-medium">
			{field.label}
			{#if isRequired(field)}<span class="ml-0.5 text-red-600">*</span>{/if}
		</label>
		<FieldControl {field} bind:value={values[field.name]} disabled={isReadOnly(field)} siblingValues={values} />
		{#if errors[field.name]}
			<p class="mt-1 text-xs text-red-600">{errors[field.name]}</p>
		{/if}
	</div>
{/snippet}

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
	{#each ungroupedFields as field (field.name)}
		{#if isVisible(field)}
			{@render fieldInput(field)}
		{/if}
	{/each}
</div>

{#each groupedSections as section (section.name)}
	{#if section.fields.some(isVisible)}
		<div class="mt-5 border-t border-neutral-100 pt-4 dark:border-neutral-800">
			<p class="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">{section.name}</p>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				{#each section.fields as field (field.name)}
					{#if isVisible(field)}
						{@render fieldInput(field)}
					{/if}
				{/each}
			</div>
		</div>
	{/if}
{/each}

{#if systemFields.some(isVisible)}
	<div class="mt-5 border-t border-neutral-100 pt-4 dark:border-neutral-800">
		<p class="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">System-generated</p>
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
			{#each systemFields as field (field.name)}
				{#if isVisible(field)}
					<div class="col-span-1">
						<span class="mb-1 block text-xs text-neutral-500">{field.label}</span>
						{#if field.formula || field.aggregate}
							<div class="flex h-8 items-center rounded-md border border-neutral-200 bg-neutral-50 px-2.5 text-sm text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-400">
								{formatComputed(field, liveSystemValues[field.name])}
							</div>
						{:else}
							<!-- AUTO_NUMBER or a plain read_only field (e.g. a locked LOOKUP) —
							     still goes through FieldControl so LOOKUP labels/dates/etc.
							     resolve and render exactly like they would in the main section. -->
							<FieldControl {field} bind:value={values[field.name]} disabled={true} />
						{/if}
					</div>
				{/if}
			{/each}
		</div>
	</div>
{/if}

{#if embeddedGrids}
	<div class="mt-6">
		{@render embeddedGrids()}
	</div>
{/if}
