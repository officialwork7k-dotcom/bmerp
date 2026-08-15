import { createTable, type RowData, type Table, type TableOptions, type TableOptionsResolved, type TableState } from '@tanstack/table-core';

/**
 * Standard Svelte 5 runes wrapper for `@tanstack/table-core` (there is no
 * official Svelte 5 adapter — `@tanstack/svelte-table` only supports
 * Svelte 4). This is the shadcn-svelte / TanStack-community pattern.
 *
 * The load-bearing trick is `mergeObjects`: it merges option objects using
 * LAZY GETTERS rather than copying values. That means when the template
 * calls `table.getRowModel()`, it reads `data`/`columns`/`state` through
 * these getters AT READ TIME, inside the render effect — so Svelte's
 * fine-grained reactivity registers the real dependencies itself. There is
 * no manual "snapshot the options, call setOptions, bump a version counter
 * to force a re-render" step anywhere, which is exactly the shape that
 * caused an infinite update loop previously (see DataTable.svelte's
 * history): TanStack's `autoResetExpanded` reassigning `expanded` to a new
 * `{}` on every row-model computation fed back into an effect that bumped
 * a `version` state, which re-triggered a `{#key version}` block, which
 * recomputed the row model, which triggered another auto-reset — forever,
 * via queued microtasks, until Svelte's own scheduler gave up and threw
 * (which in turn stalled reactivity for the whole page, including
 * SvelteKit's own client-side router trying to swap in a new route).
 */
function isFunction<T>(d: unknown): d is (old: T) => T {
	return typeof d === 'function';
}

function functionalUpdate<T>(updater: T | ((old: T) => T), old: T): T {
	return isFunction<T>(updater) ? updater(old) : updater;
}

/** Merges plain objects via lazy per-key getters. Typed loosely (the exact
 * shape is only known at each call site) — callers cast the result back to
 * the TanStack type they know it structurally satisfies. */
function mergeObjects(...sources: Record<string, unknown>[]): Record<string, unknown> {
	const target: Record<string, unknown> = {};
	for (const source of sources) {
		if (!source) continue;
		for (const key of Object.keys(source)) {
			Object.defineProperty(target, key, {
				get() {
					return source[key];
				},
				enumerable: true,
				configurable: true
			});
		}
	}
	return target;
}

export function createSvelteTable<TData extends RowData>(options: TableOptions<TData>): Table<TData> {
	const resolvedOptions = mergeObjects(
		{
			state: {},
			onStateChange: () => {},
			renderFallbackValue: null,
			mergeOptions: (defaultOptions: Record<string, unknown>, opts: Record<string, unknown>) =>
				mergeObjects(defaultOptions, opts)
		},
		options as unknown as Record<string, unknown>
	) as unknown as TableOptionsResolved<TData>;

	const table = createTable(resolvedOptions);
	let state = $state<Partial<TableState>>(table.initialState);

	function updateOptions() {
		table.setOptions(
			(prev) =>
				mergeObjects(prev as unknown as Record<string, unknown>, options as unknown as Record<string, unknown>, {
					state: mergeObjects(state as Record<string, unknown>, (options.state ?? {}) as Record<string, unknown>),
					onStateChange: (updater: unknown) => {
						state = functionalUpdate(updater as Partial<TableState> | ((old: Partial<TableState>) => Partial<TableState>), state);
						options.onStateChange?.(updater as never);
					}
				}) as unknown as TableOptionsResolved<TData>
		);
	}

	updateOptions();
	// `$effect.pre` (not `$effect`): options re-sync BEFORE the DOM render
	// pass, never after — the thing that prevents a write-after-render loop.
	$effect.pre(updateOptions);

	return table;
}
