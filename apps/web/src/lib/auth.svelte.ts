export interface CurrentUser {
	id: string;
	username: string;
	display_name: string;
	is_admin: boolean;
	// Values are usually {read?/create?/update?/delete?} for business
	// modules, but a "system.<capability>" key (see api/deps.py's
	// require_system) uses {manage?: boolean} instead — same map, a
	// different action vocabulary for that reserved key prefix.
	module_permissions: Record<string, { read?: boolean; create?: boolean; update?: boolean; delete?: boolean; manage?: boolean }>;
	theme: string;
	/** Active SAP-MANDT-style tenant for this session — see api/deps.py. */
	client_code: string;
	/** Display name of the active client_code — e.g. "Acme Inc" for "C0002". */
	client_name: string;
	/** Every client this user is assigned to — more than one entry means the
	 * org switcher in Topbar has something to switch between. */
	available_clients: string[];
	/** Same set as available_clients, paired with display names for the UI. */
	organizations: { code: string; name: string }[];
}

/**
 * Reactive singleton, populated once from the root layout's `load` (same
 * pattern as localization.svelte.ts) so every component can read the
 * signed-in user synchronously without threading it through props.
 */
export const auth: { user: CurrentUser | null } = $state({ user: null });

export class ClientSelectionRequiredError extends Error {
	availableClients: string[];
	constructor(availableClients: string[]) {
		super('Multiple organizations are available for this account — choose one to continue.');
		this.availableClients = availableClients;
	}
}

export async function fetchCurrentUser(fetchImpl: typeof fetch = fetch): Promise<CurrentUser | null> {
	const res = await fetchImpl('/api/auth/me', { credentials: 'include' });
	if (!res.ok) {
		auth.user = null;
		return null;
	}
	auth.user = await res.json();
	return auth.user;
}

export async function login(
	username: string,
	password: string,
	fetchImpl: typeof fetch = fetch,
	clientCode?: string
): Promise<CurrentUser> {
	const res = await fetchImpl('/api/auth/login', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		credentials: 'include',
		body: JSON.stringify({ username, password, client_code: clientCode })
	});
	if (!res.ok) {
		if (res.status === 401) throw new Error('Invalid username or password');
		if (res.status === 400) {
			const body = await res.json().catch(() => null);
			const detail = body?.detail;
			if (detail?.error === 'client_selection_required' && Array.isArray(detail.available_clients)) {
				throw new ClientSelectionRequiredError(detail.available_clients);
			}
			throw new Error(detail?.message || detail || 'Bad request');
		}
		const body = await res.text().catch(() => '');
		throw new Error(body || `${res.status} ${res.statusText}`);
	}
	const user: CurrentUser = await res.json();
	auth.user = user;
	return user;
}

export async function switchClient(clientCode: string, fetchImpl: typeof fetch = fetch): Promise<CurrentUser> {
	const res = await fetchImpl('/api/auth/switch-client', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		credentials: 'include',
		body: JSON.stringify({ client_code: clientCode })
	});
	if (!res.ok) {
		const body = await res.text().catch(() => '');
		throw new Error(body || `${res.status} ${res.statusText}`);
	}
	const user: CurrentUser = await res.json();
	auth.user = user;
	return user;
}

export async function logout(fetchImpl: typeof fetch = fetch): Promise<void> {
	await fetchImpl('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
	auth.user = null;
}

export function canRead(module: string): boolean {
	if (!auth.user) return false;
	return auth.user.is_admin || !!auth.user.module_permissions[module]?.read;
}
export function canCreate(module: string): boolean {
	if (!auth.user) return false;
	return auth.user.is_admin || !!auth.user.module_permissions[module]?.create;
}
export function canUpdate(module: string): boolean {
	if (!auth.user) return false;
	return auth.user.is_admin || !!auth.user.module_permissions[module]?.update;
}
export function canDelete(module: string): boolean {
	if (!auth.user) return false;
	return auth.user.is_admin || !!auth.user.module_permissions[module]?.delete;
}
