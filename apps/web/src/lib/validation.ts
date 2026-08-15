import { z } from 'zod';
import type { FieldMetadata, ModuleMetadata } from './types';
import { todayISO } from './date';

function schemaForField(field: FieldMetadata): z.ZodTypeAny {
	let schema: z.ZodTypeAny;
	switch (field.data_type) {
		case 'INTEGER':
		case 'DECIMAL':
		case 'MONEY':
		case 'PERCENT':
			schema = z.number();
			break;
		case 'BOOLEAN':
			schema = z.boolean();
			break;
		case 'JSON':
			schema = z.unknown();
			break;
		default:
			schema = z.string();
			if (field.max_length) schema = (schema as z.ZodString).max(field.max_length);
	}
	if (!field.required) schema = schema.optional().nullable();
	return schema;
}

export function moduleValidationSchema(module: ModuleMetadata) {
	const shape: Record<string, z.ZodTypeAny> = {};
	for (const field of module.fields) {
		if (field.read_only || field.formula || field.aggregate) continue;
		shape[field.name] = schemaForField(field);
	}
	return z.object(shape);
}

export function evaluateCondition(field: FieldMetadata, values: Record<string, unknown>, kind: 'then_visible' | 'then_read_only' | 'then_required'): boolean | undefined {
	for (const cond of field.conditions) {
		if (values[cond.when_field] === cond.equals) {
			const result = cond[kind];
			if (result !== undefined) return result;
		}
	}
	return undefined;
}

export function defaultsOf(module: ModuleMetadata): Record<string, unknown> {
	const d: Record<string, unknown> = {};
	for (const field of module.fields) {
		// Metadata comes from JSON over HTTP, so an unset default always
		// arrives as `null`, never `undefined` — treating null as "has a
		// default of null" made every field with no configured default
		// (i.e. nearly all of them) get force-reset to null on every mount.
		if (field.default !== undefined && field.default !== null) d[field.name] = field.default;
		else if (field.data_type === 'BOOLEAN') d[field.name] = false;
		else if (field.data_type === 'PERCENT') d[field.name] = 0;
		// Every date field on a new record starts pre-filled with today —
		// only reachable in create mode: DataForm's seeding effect only
		// ever fills a key that's `undefined`, and an existing record's
		// value (even an intentionally empty one) is never `undefined`.
		// Except a field with `default_from_lookup` (e.g. an invoice's
		// due_date, computed from the selected vendor's payment terms) —
		// pre-filling that with today would send an explicit value to the
		// server, and the server only computes the smart default when the
		// field arrives empty. Leaving it out here is what lets that happen.
		else if (field.data_type === 'DATE' && !field.default_from_lookup) d[field.name] = todayISO();
	}
	return d;
}
