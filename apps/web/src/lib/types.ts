// Hand-maintained mirror of apps/api/src/metaforge_api/domain/metadata.py.
// No shared package across the Python/TS boundary (see plan's "open item") —
// keep these two in sync by hand when the domain model changes.

import { labelOf } from './lookup';

export type FieldDataType =
	| 'TEXT' | 'LONG_TEXT' | 'RICH_TEXT'
	| 'INTEGER' | 'DECIMAL' | 'MONEY' | 'PERCENT'
	| 'DATE' | 'TIME' | 'DATETIME'
	| 'BOOLEAN' | 'ENUM' | 'LOOKUP'
	| 'EMAIL' | 'PHONE' | 'URL' | 'JSON' | 'FILE' | 'IMAGE' | 'AUTO_NUMBER';

export type RelationshipType = 'ONE_TO_MANY' | 'ONE_TO_ONE' | 'MANY_TO_MANY';
export type AggregateOp = 'sum' | 'count' | 'min' | 'max' | 'avg';

export interface FieldAggregate {
	from_module: string;
	foreign_key: string;
	source_field: string;
	op: AggregateOp;
	filter_field?: string | null;
	filter_value?: unknown;
}

export interface FieldCondition {
	when_field: string;
	equals: unknown;
	then_visible?: boolean;
	then_read_only?: boolean;
	then_required?: boolean;
}

export interface FieldMetadata {
	name: string;
	label: string;
	data_type: FieldDataType;
	control_type: string;
	required: boolean;
	unique: boolean;
	read_only: boolean;
	/** BOOLEAN-only: "at most one record in this module may have this set" —
	 * enforced by a DB partial unique index, with the previous default
	 * automatically unset in the same transaction when a new one is saved. */
	is_default_flag: boolean;
	default?: unknown;
	enum_values?: string[];
	lookup_module?: string;
	formula?: string;
	aggregate?: FieldAggregate;
	conditions: FieldCondition[];
	max_length?: number;
	precision?: number;
	scale?: number;
	/** Server-computed "smart default" (e.g. an invoice due_date from the
	 * selected vendor's payment terms) — resolved at create time in
	 * `repository.py`, only when this field is left empty. See the domain
	 * dataclass of the same name for the full shape. */
	default_from_lookup?: {
		lookup_field: string;
		term_field: string;
		term_days: Record<string, number>;
		base_date_field: string;
	};
	/** Declarative "copy this field's value from whatever `lookup_field`
	 * (another field on the same row) points to" — e.g. a line's
	 * `description` copied from `item.description`, or `tax_rate` from
	 * `tax_code_id.rate`. Applied live in EmbeddedGrid, only when this
	 * field is still empty. */
	copy_from_lookup?: {
		lookup_field: string;
		source_field: string;
	};
	/** Declarative "resolve my value from a price list" — party+item+qty
	 * most-specific-match. `header_party_field` names a field on the
	 * *parent document*, not this line, since a line only knows its own
	 * item/qty. See the domain dataclass of the same name. */
	price_from_list?: {
		price_list_module: string;
		header_party_field: string;
		item_field: string;
		qty_field: string;
	};
	/** Declarative "narrow this LOOKUP's candidates to ones matching a
	 * sibling field already selected on this same record" — e.g. a Vendor
	 * Invoice's Purchase Order picker only offers POs for the vendor
	 * already chosen. `by_field` names a column on the lookup_module's own
	 * table; `from_field` names the field on this record whose current
	 * value that column must equal. See the domain dataclass of the same
	 * name. */
	lookup_filter?: {
		by_field: string;
		from_field: string;
	};
	/** Form-layout hint only: fields sharing the same `group` render together
	 * under one titled section instead of one flat list. `undefined`/null =
	 * "General" section (rendered first, unchanged from today). Section
	 * order follows first-encountered field order, not alphabetic. */
	group?: string | null;
}

export interface ModuleRelationship {
	name: string;
	type: RelationshipType;
	related_module: string;
	foreign_key: string;
	embedded: boolean;
	cascade_delete: boolean;
	join_module?: string;
	left_field?: string;
	right_field?: string;
}

export interface WorkflowState {
	color: string;
	locked: boolean;
}

export interface WorkflowMetadata {
	field: string;
	states: Record<string, WorkflowState>;
	transitions: Record<string, string[]>;
}

export interface DocumentFlow {
	name: string;
	target_module: string;
	header_field_map: Record<string, string>;
	source_line_relation: string;
	target_line_relation: string;
	line_field_map: Record<string, string>;
	source_qty_field: string;
	target_qty_field: string;
	tolerance_pct: number;
}

export interface ModuleMetadata {
	name: string;
	label: string;
	fields: FieldMetadata[];
	relationships: ModuleRelationship[];
	version: number;
	workflow?: WorkflowMetadata | null;
	posting_rules?: Record<string, unknown> | null;
	clearing_config?: Record<string, unknown> | null;
	stock_rules?: Record<string, unknown> | null;
	document_flows?: DocumentFlow[] | null;
	/** Opt-out only, per DetailPage's record-lifecycle actions (New/Save &
	 * New/Save & Close/Duplicate) — every action defaults on with zero
	 * config; this exists so a module can suppress one (e.g. a GL journal
	 * that shouldn't be duplicated). `null`/absent = everything enabled. */
	detail_actions?: {
		disable?: ('new' | 'save_and_new' | 'save_and_close' | 'duplicate')[];
		duplicate?: { copy_lines?: boolean };
	} | null;
	/** Engine-level "reject create when a related record is blocked" rule —
	 * e.g. a Purchase Order whose vendor has `purchasing_blocked = true`.
	 * Enforced server-side in repository.create_record; this is metadata
	 * only, never per-module code. See the field's doc comment in
	 * domain/metadata.py for the full shape. */
	create_guards?: { lookup_field: string; flag_field: string; message: string }[] | null;
	/** Hides this module from the sidebar and the top-level Modules list.
	 * The module/table/API are unaffected — only navigation. */
	hidden?: boolean;
}

export type RecordRow = Record<string, unknown> & { id: string };

export interface ChildDiff {
	create: Record<string, unknown>[];
	update: Record<string, unknown>[];
	remove: string[];
}

export function emptyChildDiff(): ChildDiff {
	return { create: [], update: [], remove: [] };
}

export function embeddedChildren(module: ModuleMetadata): ModuleRelationship[] {
	return module.relationships.filter((r) => r.embedded && r.type === 'ONE_TO_MANY');
}

/** A record's best human-readable label — used in breadcrumbs, page titles,
 * and lookup-field displays. Falls back through common label field names,
 * then a shortened id, rather than ever showing a raw UUID as the primary
 * label. */
export function displayName(record: Record<string, unknown> | undefined | null, fallback = 'Record'): string {
	if (!record) return fallback;
	const candidate = record.name ?? record.title ?? record.label;
	if (candidate !== undefined && candidate !== null && candidate !== '') return String(candidate);
	// Most business modules (POs, invoices, GRs, ...) have no literal
	// name/title/label field — fall back to the same "first real field"
	// heuristic used everywhere else lookups resolve a label, instead of
	// dropping straight to a truncated, meaningless UUID prefix.
	return labelOf(record) || fallback;
}
