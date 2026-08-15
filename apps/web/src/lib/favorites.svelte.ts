const STORAGE_KEY = 'mf:favorites';

function load(): Set<string> {
	if (typeof localStorage === 'undefined') return new Set();
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		return raw ? new Set(JSON.parse(raw)) : new Set();
	} catch {
		return new Set();
	}
}

function save(names: Set<string>) {
	localStorage.setItem(STORAGE_KEY, JSON.stringify([...names]));
}

class FavoritesStore {
	// Loaded once at module-eval time (not lazily inside a derived, which
	// Svelte 5 forbids mutating state from) — safe because this module is a
	// singleton re-evaluated fresh per client page load.
	names = $state<Set<string>>(load());

	isFavorite(name: string): boolean {
		return this.names.has(name);
	}

	toggle(name: string) {
		const next = new Set(this.names);
		if (next.has(name)) next.delete(name);
		else next.add(name);
		this.names = next;
		save(next);
	}
}

export const favorites = new FavoritesStore();
