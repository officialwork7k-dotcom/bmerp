import "clsx";
const auth = { user: null };
async function fetchCurrentUser(fetchImpl = fetch) {
  const res = await fetchImpl("/api/auth/me", { credentials: "include" });
  if (!res.ok) {
    auth.user = null;
    return null;
  }
  auth.user = await res.json();
  return auth.user;
}
function canCreate(module) {
  if (!auth.user) return false;
  return auth.user.is_admin || !!auth.user.module_permissions[module]?.create;
}
function canDelete(module) {
  if (!auth.user) return false;
  return auth.user.is_admin || !!auth.user.module_permissions[module]?.delete;
}
export {
  auth as a,
  canCreate as b,
  canDelete as c,
  fetchCurrentUser as f
};
