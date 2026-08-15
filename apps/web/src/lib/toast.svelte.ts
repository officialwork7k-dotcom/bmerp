import { localization } from './localization.svelte';

export interface Toast {
	id: number;
	kind: 'success' | 'error' | 'info' | 'warning';
	message: string;
	/** Errors are sticky by default — a validation failure or save error is
	 * something the user needs time to actually read, not something that
	 * should vanish on the same fixed timer as a "Saved" confirmation. */
	sticky: boolean;
	/** ms remaining when a hover pause snapshot was taken; null while running. */
	remainingMs: number | null;
	deadline: number | null;
	timer: ReturnType<typeof setTimeout> | null;
}

let nextId = 1;
const toasts = $state<Toast[]>([]);

function remove(id: number) {
	const idx = toasts.findIndex((t) => t.id === id);
	if (idx !== -1) toasts.splice(idx, 1);
}

function arm(t: Toast, ms: number) {
	t.deadline = Date.now() + ms;
	t.timer = setTimeout(() => remove(t.id), ms);
}

function push(kind: Toast['kind'], message: string, opts?: { sticky?: boolean }) {
	const id = nextId++;
	const sticky = opts?.sticky ?? kind === 'error';
	const t: Toast = { id, kind, message, sticky, remainingMs: null, deadline: null, timer: null };
	toasts.push(t);
	if (!sticky) arm(t, localization.notification_duration_seconds * 1000);
}

function pause(id: number) {
	const t = toasts.find((x) => x.id === id);
	if (!t || t.sticky || !t.timer) return;
	clearTimeout(t.timer);
	t.timer = null;
	t.remainingMs = Math.max(0, (t.deadline ?? Date.now()) - Date.now());
}

function resume(id: number) {
	const t = toasts.find((x) => x.id === id);
	if (!t || t.sticky || t.remainingMs === null) return;
	arm(t, t.remainingMs);
	t.remainingMs = null;
}

export const toast = {
	success: (message: string) => push('success', message),
	error: (message: string) => push('error', message),
	info: (message: string) => push('info', message),
	warning: (message: string) => push('warning', message),
	list: () => toasts,
	dismiss: (id: number) => remove(id),
	pause,
	resume
};
