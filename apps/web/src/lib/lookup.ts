export interface LookupOption {
	value: string;
	label: string;
}

/** `${module}:${id}` -> resolved display label. Shared app-wide so a grid
 * with many rows referencing the same record only resolves it once, and so
 * a label resolved in one place (e.g. FieldControl) is already warm for
 * another (e.g. an embedded grid's LOOKUP column). */
export const labelCache = new Map<string, string>();

const inFlight = new Map<string, Promise<string>>();

// Mirrors the backend's _SYSTEM_COLUMNS (repository.py) plus the FK columns
// _apply_children stamps onto embedded-child rows — none of these are ever
// what a human would recognize a record by, so labelOf() must skip past
// all of them to reach the first real field.
const _NON_LABEL_KEYS = new Set([
	'id',
	'created_at',
	'updated_at',
	'created_by',
	'deleted_at',
	'version',
	'client_code'
]);

// A module's own identifying code — `account_code`, `code`, `sku`,
// `determination_key` — versus a field that merely *references* another
// record's code (`gl_account_code` on tax_codes, pointing at a *different*
// module's account). The two are indistinguishable by name pattern alone;
// what separates them is field position — every code-like field surveyed
// across the framework's modules that names *this* record sits first
// (account_code, code, determination_key), while a reference to someone
// else's code never does. So only the first field is ever treated as this
// record's own code.
const _CODE_PATTERN = /(^|_)(code|key|sku)$/i;
const _NAME_PATTERN = /(^|_)(name|title|description)$/i;

export function labelOf(row: Record<string, unknown>): string {
	const keys = Object.keys(row).filter((k) => !_NON_LABEL_KEYS.has(k) && !k.endsWith('_id'));
	if (keys.length === 0) return String(row.id);
	const first = keys[0];
	if (_CODE_PATTERN.test(first)) {
		const nameKey = keys.find((k) => k !== first && _NAME_PATTERN.test(k));
		if (nameKey !== undefined) {
			const code = row[first];
			const name = row[nameKey];
			if (code !== undefined && code !== null && code !== '' && name !== undefined && name !== null && name !== '') {
				return `${code} — ${name}`;
			}
		}
	}
	return String(row[first] ?? row.id);
}

export async function searchLookup(
	module: string,
	query: string,
	limit = 20,
	signal?: AbortSignal,
	filters?: Record<string, string>
): Promise<LookupOption[]> {
	const params = new URLSearchParams({ search: query, limit: String(limit) });
	if (filters) for (const [k, v] of Object.entries(filters)) params.set(k, v);
	const res = await fetch(`/api/data/${module}?${params}`, { signal });
	const rows = res.ok ? await res.json() : [];
	const list: Record<string, unknown>[] = Array.isArray(rows) ? rows : (rows.items ?? []);
	const options = list.map((r) => ({ value: String(r.id), label: labelOf(r) }));
	for (const opt of options) labelCache.set(`${module}:${opt.value}`, opt.label);
	return options;
}

/** Debounced *and* race-safe lookup search, for any component that lets a
 * user type into a search box backed by `searchLookup`.
 *
 * `debounced()` alone only delays *starting* a request — it does nothing
 * once two requests are in flight at the same time, which happens the
 * moment someone types faster than the debounce window (very easy at
 * 200-250ms). If an earlier, shorter query's response happens to resolve
 * *after* a later, longer one's (completely plausible over a real network,
 * where response order isn't guaranteed to match request order), the
 * on-screen results silently regress to matches for text the user already
 * typed past — indistinguishable from "search is broken" to whoever's
 * typing. This is the bug behind "search doesn't work if you type before
 * the results catch up," reported against the grid's item picker and
 * present identically in every other component that rolled its own
 * `debounced(async () => { options = await searchLookup(...) })` — both
 * known instances (the grid cell editor and the header-field lookup
 * popover) now go through this one controller instead of duplicating (and
 * separately re-breaking) the same logic.
 *
 * Each call cancels the previous pending call's timer *and* aborts its
 * in-flight fetch via AbortController, so only ever the most recent
 * keystroke's request can resolve and reach `onResult`. */
export function createSearchController(ms = 200) {
	let timer: ReturnType<typeof setTimeout> | undefined;
	let controller: AbortController | undefined;
	return {
		run(
			module: string,
			query: string,
			onResult: (options: LookupOption[]) => void,
			onLoading: (loading: boolean) => void,
			filters?: Record<string, string>
		) {
			clearTimeout(timer);
			controller?.abort();
			onLoading(true);
			timer = setTimeout(() => {
				const myController = new AbortController();
				controller = myController;
				searchLookup(module, query, 20, myController.signal, filters)
					.then((options) => {
						if (myController.signal.aborted) return;
						onResult(options);
						onLoading(false);
					})
					.catch((err) => {
						// AbortError is the expected shape of "a newer search
						// superseded this one" — silently ignored. Anything else
						// is a real failure; it shouldn't leave the caller stuck
						// on `loading: true` forever, but there's no useful
						// per-call error channel here (callers fire-and-forget),
						// so it's logged rather than thrown into an unhandled
						// rejection.
						if (myController.signal.aborted) return;
						onLoading(false);
						if (!(err instanceof DOMException && err.name === 'AbortError')) console.error('lookup search failed', err);
					});
			}, ms);
		},
		/** Call on component teardown so an in-flight request from a closed
		 * popup can't still land and call back into unmounted state. */
		dispose() {
			clearTimeout(timer);
			controller?.abort();
		}
	};
}

/** Resolves and caches a single record's display label, de-duping
 * concurrent requests for the same module+id (e.g. many grid rows pointing
 * at the same vendor resolving on first paint). */
export function resolveLabel(module: string, id: string): Promise<string> {
	const key = `${module}:${id}`;
	const cached = labelCache.get(key);
	if (cached !== undefined) return Promise.resolve(cached);
	const pending = inFlight.get(key);
	if (pending) return pending;

	const promise = fetch(`/api/data/${module}/${id}`)
		.then((r) => (r.ok ? r.json() : null))
		.then((row) => {
			const label = row ? labelOf(row) : id;
			labelCache.set(key, label);
			return label;
		})
		.finally(() => inFlight.delete(key));
	inFlight.set(key, promise);
	return promise;
}

export function debounced<Args extends unknown[]>(fn: (...args: Args) => void, ms = 250): (...args: Args) => void {
	let handle: ReturnType<typeof setTimeout>;
	return (...args: Args) => {
		clearTimeout(handle);
		handle = setTimeout(() => fn(...args), ms);
	};
}
