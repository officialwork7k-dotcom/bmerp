import { mount, unmount } from 'svelte';
import type { ICellEditorComp, ICellEditorParams } from 'ag-grid-community';
import { labelCache } from '$lib/lookup';
import LookupEditorPanel from './LookupEditorPanel.svelte';

export interface LookupCellEditorParams extends ICellEditorParams {
	lookupModule: string;
	/** Narrows candidates to rows matching a sibling field already selected
	 * on this row or the parent document — see FieldMetadata.lookup_filter. */
	filters?: Record<string, string>;
}

/** AG Grid Community custom cell editor bridging into a Svelte 5 component
 * via mount/unmount — AG Grid editors are plain classes (ICellEditorComp),
 * not part of the normal Svelte component tree, so there's no way to render
 * one as a template child; this is the documented escape hatch. */
export class LookupCellEditor implements ICellEditorComp {
	private el = document.createElement('div');
	private value: string | null = null;
	private module = '';
	private app: Record<string, unknown> | null = null;
	private panelInstance: { focus: () => void } | null = null;
	private params!: LookupCellEditorParams;

	init(params: LookupCellEditorParams) {
		this.params = params;
		this.module = params.lookupModule;
		this.value = (params.value as string | null | undefined) ?? null;
		const initialLabel = this.value ? (labelCache.get(`${this.module}:${this.value}`) ?? '') : '';
		// A single printable character starting the edit (typed directly on
		// the cell, not via Enter/F2) should seed the search box already
		// filtering, matching how AG Grid's built-in text editor behaves.
		const initialQuery = params.eventKey && params.eventKey.length === 1 ? params.eventKey : '';

		this.app = mount(LookupEditorPanel, {
			target: this.el,
			props: {
				module: this.module,
				initialValue: this.value,
				initialLabel,
				initialQuery,
				filters: params.filters,
				commit: (value: string | null, label: string) => {
					this.value = value;
					if (value) labelCache.set(`${this.module}:${value}`, label);
					params.stopEditing();
				},
				cancel: () => params.stopEditing(true)
			}
		}) as unknown as Record<string, unknown>;
		this.panelInstance = this.app as unknown as { focus: () => void };
	}

	getGui() {
		return this.el;
	}

	getValue() {
		return this.value;
	}

	isPopup() {
		return true;
	}

	getPopupPosition(): 'under' {
		return 'under';
	}

	afterGuiAttached() {
		this.panelInstance?.focus();
	}

	destroy() {
		if (this.app) unmount(this.app as never);
	}
}

/** While a LOOKUP cell is editing, arrow/enter/paging keys must reach the
 * dropdown panel, not AG Grid's own cell navigation — otherwise the two
 * fight over the keypress and the picker feels broken. */
export function suppressGridKeysWhileEditingLookup(p: { editing: boolean; event: KeyboardEvent }): boolean {
	return p.editing && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Enter', 'PageUp', 'PageDown'].includes(p.event.key);
}
