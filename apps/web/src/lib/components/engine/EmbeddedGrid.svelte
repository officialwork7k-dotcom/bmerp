<script lang="ts">
	import { createGrid, type ColDef, type GridApi } from 'ag-grid-community';
	import { untrack } from 'svelte';
	import type { FieldMetadata, ModuleMetadata } from '$lib/types';
	import { evaluate_formula_safe } from '$lib/formula';
	import { pickGridTheme } from '$lib/grid/theme';
	import { themeState } from '$lib/theme.svelte';
	import { LookupCellEditor, suppressGridKeysWhileEditingLookup } from '$lib/grid/LookupCellEditor';
	import { labelCache, resolveLabel } from '$lib/lookup';
	import { formatDateDisplay, parseDateInput, todayISO } from '$lib/date';
	import { formatDecimal, formatMoney, formatPercent } from '$lib/format';

	// No ModuleRegistry.registerModules() call here: the 'ag-grid-community'
	// package is the all-in-one bundle, which auto-registers every
	// Community module internally. Calling registerModules() on top of that
	// is what AG Grid's own "you are mixing modules and packages" error
	// warns about — it left the grid registry in a broken state where
	// interactions like "+ Add row" silently did nothing.
	//
	// Theming: only the JS Theming API (`theme: mfGridTheme`) is used — the
	// container carries no `ag-theme-quartz` CSS class. Combining both is
	// unsupported in AG Grid v32+ (error #239) and was quietly producing the
	// half-styled "looks very simple" grid.

	let {
		childModule,
		fkField,
		rows = $bindable(),
		disabled = false,
		onChange,
		headerValues
	}: {
		childModule: ModuleMetadata;
		fkField: string;
		rows: Record<string, unknown>[];
		disabled?: boolean;
		onChange?: () => void;
		/** The parent document's current field values — a price-list lookup is
		 * keyed by party (vendor/customer) + item + qty, and the party lives on
		 * the header, not this line, so resolving a line's price needs it. */
		headerValues?: Record<string, unknown>;
	} = $props();

	const REMOVE_COL_ID = '__remove__';

	let container: HTMLDivElement;
	let api: GridApi | undefined;
	const removedIds = new Set<string>();
	const originalById = new Map<string, Record<string, unknown>>();
	let nextCid = 0;

	function rowId(row: Record<string, unknown>): string {
		if (row.id) return String(row.id);
		if (!row._cid) row._cid = `new-${nextCid++}`;
		return String(row._cid);
	}

	for (const r of rows) {
		if (r.id) originalById.set(String(r.id), { ...r });
	}

	const editableFields = $derived(childModule.fields.filter((f) => f.name !== fkField && f.name !== 'id'));
	const numericFields = $derived(editableFields.filter((f) => ['INTEGER', 'DECIMAL', 'MONEY'].includes(f.data_type)));

	function numberFormatter(field: FieldMetadata): (value: unknown) => string {
		if (field.data_type === 'MONEY') return (v) => formatMoney(v);
		if (field.data_type === 'PERCENT') return (v) => formatPercent(v);
		return (v) => formatDecimal(v, field.data_type === 'INTEGER' ? 0 : (field.scale ?? 2));
	}

	function colDefFor(field: FieldMetadata): ColDef {
		const isComputed = Boolean(field.formula || field.aggregate);
		const canEdit = !disabled && !field.read_only && !isComputed;
		const base: ColDef = {
			field: field.name,
			headerName: field.label,
			// `editable` was a plain boolean here before — applied identically
			// to every row AG Grid renders, *including* the pinned totals row
			// (it goes through the same colDefs, there's no separate "pinned
			// row" column config). That let the totals row's LOOKUP cell open
			// the search popup on click/tab-into even though it's a synthetic
			// summary row with no real record behind it. Row-aware function
			// instead of a static value.
			editable: (p) => canEdit && !p.node?.rowPinned,
			// Read-only/computed columns (Line Total) are visible but never
			// editable — Tab should skip straight over them to the next real
			// input instead of stopping on a dead cell. The pinned totals
			// row is never keyboard-navigable at all: there's nothing to
			// tab into on a synthetic summary row.
			suppressNavigable: (p) => Boolean(p.node?.rowPinned) || !canEdit,
			flex: 1,
			minWidth: 120,
			cellClassRules: field.required
				? { 'mf-cell-invalid': (p) => !p.node?.rowPinned && (p.value === undefined || p.value === null || p.value === '') }
				: undefined
		};
		if (field.data_type === 'LOOKUP' && field.lookup_module) {
			return {
				...base,
				cellEditor: LookupCellEditor,
				cellEditorPopup: true,
				// A function, not a static object, so it's re-evaluated fresh
				// every time editing starts on this cell — a lookup_filter's
				// dependency value (this row's own field, or a header field
				// like the parent document's vendor) may have changed since
				// the column defs were built, and there's no other reactive
				// path from a prop change back into AG Grid's static colDefs.
				cellEditorParams: (p: { data?: Record<string, unknown> }) => {
					const lf = field.lookup_filter;
					const filterValue = lf ? (p.data?.[lf.from_field] ?? headerValues?.[lf.from_field]) : undefined;
					return {
						lookupModule: field.lookup_module,
						filters: lf && filterValue != null ? { [lf.by_field]: String(filterValue) } : undefined
					};
				},
				suppressKeyboardEvent: suppressGridKeysWhileEditingLookup,
				valueFormatter: (p) =>
					p.value == null ? '' : (labelCache.get(`${field.lookup_module}:${p.value}`) ?? '…')
			};
		}
		if (field.data_type === 'ENUM') {
			return { ...base, cellEditor: 'agSelectCellEditor', cellEditorParams: { values: field.enum_values ?? [] } };
		}
		if (field.data_type === 'DATE') {
			return {
				...base,
				// Default text cell editor (no cellEditor override) — the
				// user types freely, including SAP-style shorthand ("t",
				// "1.1.26"); valueParser is where that gets turned into the
				// real `yyyy-mm-dd` that's actually stored. Unparseable
				// input falls back to the previous value instead of writing
				// garbage or silently blanking the cell.
				valueParser: (p) => parseDateInput(String(p.newValue ?? '')) ?? p.oldValue ?? null,
				valueFormatter: (p) => formatDateDisplay(p.value as string | undefined)
			};
		}
		if (['INTEGER', 'DECIMAL', 'MONEY', 'PERCENT'].includes(field.data_type)) {
			const format = numberFormatter(field);
			return {
				...base,
				cellEditor: isComputed ? undefined : 'agNumberCellEditor',
				type: 'rightAligned',
				valueParser: (p) => (p.newValue === '' || p.newValue === null ? null : Number(p.newValue)),
				// The pinned totals row must NOT re-run the formula: `p.data`
				// there is the *summed* row, so `qty * unit_price` would
				// compute sum(qty) × sum(unit_price) instead of the correct
				// Σ(line_total) that computeTotalsRow() already stamped into
				// `p.value`. Falling through to `format()` also fixes real
				// rows' formula cells never getting currency formatting
				// (they rendered "250" next to a neighbor's "$250.00").
				valueFormatter: (p) =>
					isComputed && field.formula && !p.node?.rowPinned
						? format(Number(withComputedFormulas(p.data as Record<string, unknown>)[field.name]) || 0)
						: format(p.value)
			};
		}
		if (field.data_type === 'BOOLEAN') {
			return {
				...base,
				cellEditor: 'agCheckboxCellEditor',
				// A checkbox renderer ignores valueFormatter entirely, so
				// pinned-row-awareness has to live in the renderer choice
				// itself: an unchecked-looking checkbox on the totals row
				// reads as an interactive control that does nothing.
				cellRendererSelector: (p) =>
					p.node?.rowPinned ? undefined : { component: 'agCheckboxCellRenderer' }
			};
		}
		return base;
	}

	function makeRemoveButton() {
		const btn = document.createElement('button');
		btn.type = 'button';
		btn.textContent = '✕';
		btn.setAttribute('aria-label', 'Remove row');
		btn.className =
			'flex h-6 w-6 items-center justify-center rounded text-neutral-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950';
		return btn;
	}

	function buildColumnDefs(): ColDef[] {
		const cols = editableFields.map(colDefFor);
		if (cols[0]) {
			const original = cols[0].valueFormatter;
			cols[0] = {
				...cols[0],
				valueFormatter: (p) =>
					p.node?.rowPinned ? 'Total' : typeof original === 'function' ? original(p) : String(p.value ?? '')
			};
			// Pinned so the identity column (usually a LOOKUP like "Item")
			// stays visible while scrolling right for the rest — the columns
			// most worth keeping in view are exactly the ones that would
			// otherwise scroll off-screen first on a narrow viewport.
			if (!disabled) cols[0] = { ...cols[0], pinned: 'left' };
		}
		if (!disabled) {
			cols.push({
				colId: REMOVE_COL_ID,
				headerName: 'Remove',
				headerClass: 'mf-sr-only-header',
				width: 44,
				sortable: false,
				resizable: false,
				suppressNavigable: (p) => Boolean(p.node?.rowPinned),
				pinned: 'right',
				cellRenderer: (p: { node?: { rowPinned?: string } }) => (p.node?.rowPinned ? document.createElement('span') : makeRemoveButton()),
				onCellClicked: (p) => {
					if (p.node?.rowPinned) return;
					if (p.data.id) removedIds.add(String(p.data.id));
					removeRowLocal(p.data);
				}
			});
		}
		return cols;
	}

	function computeTotalsRow(): Record<string, unknown> | null {
		// No totals row at all with zero real rows — a "$0.00" summary
		// floating under the "No lines yet" empty-state overlay reads as
		// clutter, not information.
		if (numericFields.length === 0 || rows.length === 0) return null;
		const totals: Record<string, unknown> = { id: '__totals__' };
		for (const f of numericFields) {
			totals[f.name] = rows.reduce((sum, r) => {
				// Resolve every formula field first (in declaration order) so a
				// formula depending on another formula field — tax_amount on
				// line_total — sums correctly instead of treating the
				// not-yet-computed dependency as 0.
				const raw = f.formula ? Number(withComputedFormulas(r)[f.name] ?? 0) : Number(r[f.name] ?? 0);
				return sum + (Number.isFinite(raw) ? raw : 0);
			}, 0);
		}
		return totals;
	}

	function refreshTotals() {
		const totals = computeTotalsRow();
		api?.setGridOption('pinnedBottomRowData', totals ? [totals] : []);
	}

	// Generic "copy this field's value from whatever a LOOKUP field on this
	// same row points to" — driven entirely by FieldMetadata.copy_from_lookup,
	// not hardcoded to any particular field name. Covers both a material
	// line's `description` (copied from item.description) and e.g. a line's
	// `tax_rate` (copied from tax_code_id.rate): the picker only ever sets
	// the LOOKUP id itself, so anything else a related record should
	// contribute has to be fetched and copied in explicitly. Only fills a
	// field that's still empty — never clobbers a manual edit.
	function fetchRelatedField(lookupModule: string, id: unknown, sourceField: string): Promise<unknown> {
		return fetch(`/api/data/${lookupModule}/${id}`)
			.then((r) => (r.ok ? r.json() : null))
			.then((related: Record<string, unknown> | null) => related?.[sourceField] ?? null);
	}

	function autoFillCopiedFieldsFromLookup(e: { column: { getColId: () => string }; newValue: unknown; data: Record<string, unknown>; node: { setDataValue: (col: string, value: unknown) => void } }) {
		const colId = e.column.getColId();
		if (!e.newValue) return;
		const changedField = editableFields.find((f) => f.name === colId);
		if (!changedField || changedField.data_type !== 'LOOKUP' || !changedField.lookup_module) return;
		for (const target of editableFields) {
			const cfl = target.copy_from_lookup;
			if (!cfl || cfl.lookup_field !== colId || e.data[target.name]) continue;
			fetchRelatedField(changedField.lookup_module, e.newValue, cfl.source_field).then((value) => {
				if (value !== null && value !== undefined) e.node.setDataValue(target.name, value);
			});
		}
	}

	// Price-list resolution: unlike copy_from_lookup, the party (vendor/
	// customer) this price depends on isn't a field on this row at all —
	// it's on the parent document header. Triggers whenever the changed
	// column is either the price-target field's own item_field or
	// qty_field (a qty-break changes which price list row is "most
	// specific"), and only fills a field that's still empty.
	function resolvePriceFromList(e: { column: { getColId: () => string }; data: Record<string, unknown>; node: { setDataValue: (col: string, value: unknown) => void } }) {
		const colId = e.column.getColId();
		for (const target of editableFields) {
			const pfl = target.price_from_list;
			if (!pfl || (pfl.item_field !== colId && pfl.qty_field !== colId) || e.data[target.name]) continue;
			const partyId = headerValues?.[pfl.header_party_field];
			const itemId = e.data[pfl.item_field];
			const qty = e.data[pfl.qty_field];
			if (!partyId || !itemId || qty === undefined || qty === null || qty === '') continue;
			const params = new URLSearchParams({
				price_list_module: pfl.price_list_module,
				party_field: pfl.header_party_field,
				party_id: String(partyId),
				item_field: pfl.item_field,
				item_id: String(itemId),
				qty: String(qty)
			});
			fetch(`/api/price-lists/resolve?${params}`)
				.then((r) => (r.ok ? r.json() : null))
				.then((match: { unit_price: number | null; discount_pct: number | null } | null) => {
					if (match?.unit_price !== null && match?.unit_price !== undefined) e.node.setDataValue(target.name, match.unit_price);
				});
		}
	}

	// Same backfill as `autoFillCopiedFieldsFromLookup`, but for rows that
	// never went through a cell-edit event at all — a document-flow "pull
	// lines" action, a CSV import, or any other path that hands this grid a
	// fresh `rows` array with a LOOKUP field already set but a copy-target
	// field still empty (the source row it was copied from may itself have
	// never had it filled in). Runs on every row the external-sync effect
	// below picks up, same "only if still empty" rule.
	function backfillCopiedFields(rowsToCheck: Record<string, unknown>[]) {
		const copyTargets = editableFields.filter((f) => f.copy_from_lookup);
		if (copyTargets.length === 0) return;
		for (const row of rowsToCheck) {
			for (const target of copyTargets) {
				const cfl = target.copy_from_lookup!;
				const lookupField = editableFields.find((f) => f.name === cfl.lookup_field);
				const id = lookupField && row[cfl.lookup_field];
				if (!lookupField?.lookup_module || row[target.name] || !id) continue;
				const targetId = rowId(row);
				fetchRelatedField(lookupField.lookup_module, id, cfl.source_field).then((value) => {
					if (value === null || value === undefined) return;
					const node = api?.getRowNode(targetId);
					if (node) {
						node.setDataValue(target.name, value);
					} else {
						rows = rows.map((r) => (rowId(r) === targetId ? { ...r, [target.name]: value } : r));
						lastSyncedRows = rows;
					}
				});
			}
		}
	}

	// Every internal mutation reassigns `rows` (it's a $bindable prop the
	// parent also reads) *and* applies the matching AG Grid transaction
	// directly, so the grid's own DOM/edit/scroll state is never touched.
	// `lastSyncedRows` records that this exact array reference is already
	// reflected in the grid, so the external-sync effect below — which
	// exists to pick up rows arriving from *outside* (the parent's async
	// child-row fetch, or a post-save refresh) — knows to skip it.
	let lastSyncedRows: Record<string, unknown>[] | null = null;

	function addRowLocal(row: Record<string, unknown>) {
		rows = [...rows, row];
		lastSyncedRows = rows;
		api?.applyTransaction({ add: [row] });
		refreshTotals();
		onChange?.();
	}

	function removeRowLocal(row: Record<string, unknown>) {
		rows = rows.filter((r) => rowId(r) !== rowId(row));
		lastSyncedRows = rows;
		api?.applyTransaction({ remove: [row] });
		refreshTotals();
		onChange?.();
	}

	async function warmLookupLabels() {
		const lookupFields = editableFields.filter((f) => f.data_type === 'LOOKUP' && f.lookup_module);
		if (lookupFields.length === 0) return;
		const pending: Promise<unknown>[] = [];
		for (const f of lookupFields) {
			for (const r of rows) {
				const id = r[f.name];
				if (id) pending.push(resolveLabel(f.lookup_module!, String(id)));
			}
		}
		if (pending.length === 0) return;
		await Promise.all(pending);
		api?.refreshCells({ columns: lookupFields.map((f) => f.name), force: true });
	}

	// Created exactly once per mount: everything read here is wrapped in
	// untrack() so later internal mutations (which reassign `rows` via
	// addRowLocal/removeRowLocal/onCellValueChanged) don't retrigger this
	// effect and tear the grid down mid-edit — the bug that made every
	// keystroke lose focus and scroll position.
	$effect(() => {
		untrack(() => {
			const initialTotals = computeTotalsRow();
			api = createGrid(container, {
				theme: pickGridTheme(),
				rowData: rows,
				columnDefs: buildColumnDefs(),
				getRowId: (p) => rowId(p.data as Record<string, unknown>),
				defaultColDef: { resizable: true, sortable: false },
				autoSizeStrategy: { type: 'fitGridWidth' },
				domLayout: 'autoHeight',
				rowHeight: 40,
				headerHeight: 40,
				singleClickEdit: true,
				stopEditingWhenCellsLoseFocus: true,
				enterNavigatesVertically: true,
				enterNavigatesVerticallyAfterEdit: true,
				undoRedoCellEditing: true,
				undoRedoCellEditingLimit: 20,
				pinnedBottomRowData: initialTotals ? [initialTotals] : [],
				// Default popup parent is the grid's own root div, which for a
				// short `domLayout: 'autoHeight'` grid is often shorter than
				// the LOOKUP picker itself — AG Grid clamps the popup inside
				// it rather than flipping it, so the picker gets crushed or
				// clipped. Popping it to the document lets it clamp against
				// the viewport instead, which is what "clamp within bounds"
				// should mean for a popup this size.
				popupParent: document.body,
				// Community has no built-in "Delete clears the cell" (that's
				// an Enterprise range-selection feature) — and the remove-row
				// "✕" cellRenderer only ever wired a mouse click, leaving
				// keyboard-only users with no way to act on it at all. Both
				// handled here at the grid level since colDefs can't express
				// "respond to a keypress without entering edit mode."
				onCellKeyDown: (e) => {
					if (!('column' in e) || e.node.rowPinned) return;
					const key = (e.event as KeyboardEvent | undefined)?.key;
					const colId = e.column.getColId();
					if (colId === REMOVE_COL_ID) {
						if (key !== 'Enter' && key !== 'Delete' && key !== 'Backspace') return;
						const data = e.data as Record<string, unknown>;
						if (data.id) removedIds.add(String(data.id));
						const rowIndex = e.node.rowIndex;
						removeRowLocal(data);
						if (rowIndex !== null) {
							const count = api!.getDisplayedRowCount();
							if (count > 0) api!.setFocusedCell(Math.min(rowIndex, count - 1), e.column);
						}
						return;
					}
					if (key !== 'Delete' && key !== 'Backspace') return;
					const field = editableFields.find((f) => f.name === colId);
					if (!field || field.formula || field.aggregate || field.read_only) return;
					e.node.setDataValue(colId, null);
				},
				overlayNoRowsTemplate: disabled
					? '<span class="text-sm text-neutral-400">No related records</span>'
					: '<span class="text-sm text-neutral-400">No lines yet — Add row to get started</span>',
				onCellValueChanged: (e) => {
					const id = rowId(e.data as Record<string, unknown>);
					rows = rows.map((r) => (rowId(r) === id ? { ...e.data } : r));
					lastSyncedRows = rows;
					refreshTotals();
					onChange?.();
					autoFillCopiedFieldsFromLookup(e);
				resolvePriceFromList(e);
				}
			});
			lastSyncedRows = rows;
			warmLookupLabels();
		});

		return () => {
			api?.destroy();
		};
	});

	// Re-themes the grid whenever the user switches the app theme (BM/
	// Yellow/Blue/Orange/Dark) via ThemeSwitcher — pickGridTheme() reads
	// the *current* theme's CSS custom properties each call, so this just
	// needs to know a switch happened. Skips its own first run: the
	// creation effect above already applies the initial theme once.
	let themeEffectRan = false;
	$effect(() => {
		void themeState.current;
		if (!themeEffectRan) {
			themeEffectRan = true;
			return;
		}
		api?.setGridOption('theme', pickGridTheme());
	});

	// Picks up `rows` arriving from *outside* this component after creation
	// — e.g. DetailPage's async fetch of existing child rows, which resolves
	// after this grid has already mounted with an empty array. Internal
	// mutations mark themselves synced above and are skipped here, so this
	// never fights the transaction-based updates or tears the grid down.
	$effect(() => {
		const currentRows = rows;
		if (!api || currentRows === lastSyncedRows) return;
		lastSyncedRows = currentRows;
		originalById.clear();
		for (const r of currentRows) if (r.id) originalById.set(String(r.id), { ...r });
		removedIds.clear();
		api.setGridOption('rowData', currentRows);
		refreshTotals();
		warmLookupLabels();
		backfillCopiedFields(currentRows);
	});

	export function addRow() {
		const blank: Record<string, unknown> = {};
		for (const f of editableFields) {
			if (f.default !== undefined && f.default !== null) blank[f.name] = f.default;
			// A new line in a child grid is entry mode too — same today-fill
			// as a top-level record's date field, same reasoning.
			else if (f.data_type === 'DATE') blank[f.name] = todayISO();
		}
		addRowLocal(blank);
	}

	// Formula fields (e.g. line_total = qty * unit_price) are display-only in
	// the grid — nothing ever wrote their computed value into the row, so a
	// parent aggregate summing that field always saw NULL/0. Compute and
	// stamp them in here, the one place every row passes through on save.
	//
	// Built from `editableFields` rather than `{ ...row }`: an existing row's
	// `rows` entry is the raw GET response, which carries system columns
	// (created_at, updated_at, version, ...) alongside the editable ones. The
	// backend writes back whatever keys it's given, and it doesn't coerce
	// those timestamp strings the way it does for a module's own declared
	// date fields — sending them through on every save 500s on the write.
	function withComputedFormulas(row: Record<string, unknown>): Record<string, unknown> {
		const out: Record<string, unknown> = {};
		if (row.id) out.id = row.id;
		for (const f of editableFields) {
			// Evaluated against `out`, not `row` — a formula field can depend
			// on another formula field computed earlier in this same pass
			// (e.g. tax_amount = line_total * tax_rate / 100), and fields are
			// declared in dependency order, same fix as the backend's
			// apply_formulas.
			out[f.name] = f.formula
				? (() => {
						const value = evaluate_formula_safe(f.formula!, out);
						return value === '' ? null : Number(value);
					})()
				: row[f.name];
		}
		return out;
	}

	// A brand-new row (no `id` yet) where nothing was ever entered — e.g. the
	// row left behind by clicking "+ Add row" and then not filling it in.
	// Never counts as an error and never reaches the server: silently
	// dropped, the same way an empty trailing row in a spreadsheet is just
	// ignored rather than flagged.
	function isRowBlank(row: Record<string, unknown>): boolean {
		return !row.id && editableFields.every((f) => f.formula || f.aggregate || row[f.name] == null || row[f.name] === '');
	}

	// Required-field validation the grid can't fully express visually: the
	// per-cell `mf-cell-invalid` styling shows something is missing, but
	// nothing previously stopped Save from sending an incomplete row anyway
	// — the backend has NOT NULL columns for required fields, so that always
	// surfaced as an opaque 500 instead of a message telling the user what
	// to fix. Called from DetailPage before the actual save request.
	export function validate(): string | null {
		for (const row of rows) {
			if (isRowBlank(row)) continue;
			for (const f of editableFields) {
				if (!f.required || f.formula || f.aggregate) continue;
				const value = row[f.name];
				if (value === undefined || value === null || value === '') {
					return `${childModule.label}: "${f.label}" is required.`;
				}
			}
		}
		return null;
	}

	export function getChanges() {
		// Drop any never-touched blank rows before diffing — both from the
		// payload and from the grid itself, so a successful save doesn't
		// leave a stray empty row sitting in the UI with nothing backing it.
		const blanks = rows.filter(isRowBlank);
		if (blanks.length > 0) {
			rows = rows.filter((r) => !blanks.includes(r));
			lastSyncedRows = rows;
			api?.applyTransaction({ remove: blanks });
			refreshTotals();
		}

		const create: Record<string, unknown>[] = [];
		const update: Record<string, unknown>[] = [];
		for (const row of rows) {
			const computed = withComputedFormulas(row);
			if (!row.id) {
				create.push(computed);
				continue;
			}
			const original = originalById.get(String(row.id));
			if (!original || JSON.stringify(original) !== JSON.stringify(row)) {
				update.push(computed);
			}
		}
		return { create, update, remove: Array.from(removedIds) };
	}
</script>

<div class="rounded-md border border-neutral-200 dark:border-neutral-800">
	<div bind:this={container}></div>
	{#if !disabled}
		<div class="border-t border-neutral-200 p-2 dark:border-neutral-800">
			<button
				type="button"
				class="rounded-md border border-neutral-300 px-3 py-1 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
				onclick={addRow}
			>
				+ Add row
			</button>
		</div>
	{/if}
</div>
