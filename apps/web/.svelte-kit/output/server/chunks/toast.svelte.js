import "clsx";
import { l as localization } from "./localization.svelte.js";
let nextId = 1;
const toasts = [];
function remove(id) {
  const idx = toasts.findIndex((t) => t.id === id);
  if (idx !== -1) toasts.splice(idx, 1);
}
function arm(t, ms) {
  t.deadline = Date.now() + ms;
  t.timer = setTimeout(() => remove(t.id), ms);
}
function push(kind, message, opts) {
  const id = nextId++;
  const sticky = kind === "error";
  const t = {
    id,
    kind,
    message,
    sticky,
    remainingMs: null,
    deadline: null,
    timer: null
  };
  toasts.push(t);
  if (!sticky) arm(t, localization.notification_duration_seconds * 1e3);
}
function pause(id) {
  const t = toasts.find((x) => x.id === id);
  if (!t || t.sticky || !t.timer) return;
  clearTimeout(t.timer);
  t.timer = null;
  t.remainingMs = Math.max(0, (t.deadline ?? Date.now()) - Date.now());
}
function resume(id) {
  const t = toasts.find((x) => x.id === id);
  if (!t || t.sticky || t.remainingMs === null) return;
  arm(t, t.remainingMs);
  t.remainingMs = null;
}
const toast = {
  success: (message) => push("success", message),
  error: (message) => push("error", message),
  info: (message) => push("info", message),
  warning: (message) => push("warning", message),
  list: () => toasts,
  dismiss: (id) => remove(id),
  pause,
  resume
};
export {
  toast as t
};
