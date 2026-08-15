function createApi(fetchImpl = fetch) {
  async function request(path, init) {
    const res = await fetchImpl(`/api${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      credentials: "include"
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${body}`);
    }
    if (res.status === 204) return void 0;
    return res.json();
  }
  return {
    listModules: () => request("/modules"),
    getModule: (name) => request(`/modules/${name}`),
    saveModule: (name, body) => request(
      `/modules/${name}`,
      { method: "PUT", body: JSON.stringify(body) }
    ),
    getRecord: (module, id) => request(`/data/${module}/${id}`),
    listRecords: (module, params = {}) => request(`/data/${module}${new URLSearchParams(params).toString() ? "?" + new URLSearchParams(params).toString() : ""}`),
    createRecord: (module, data, children = {}) => request(`/data/${module}`, { method: "POST", body: JSON.stringify({ data, children }) }),
    updateRecord: (module, id, data, children = {}) => request(`/data/${module}/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ data, children })
    }),
    deleteRecord: (module, id) => request(`/data/${module}/${id}`, { method: "DELETE" }),
    transitionRecord: (module, id, to, note) => request(`/data/${module}/${id}/transition`, { method: "POST", body: JSON.stringify({ to, note }) }),
    getRecordHistory: (module, id) => request(`/data/${module}/${id}/history`),
    listRoles: () => request("/admin/roles"),
    createRole: (body) => request("/admin/roles", { method: "POST", body: JSON.stringify(body) }),
    updateRole: (id, body) => request(`/admin/roles/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    deleteRole: (id) => request(`/admin/roles/${id}`, { method: "DELETE" }),
    listUsers: () => request("/admin/users"),
    createUser: (body) => request("/admin/users", { method: "POST", body: JSON.stringify(body) }),
    updateUser: (id, body) => request(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    forceLogoutUser: (id) => request(`/admin/users/${id}/force-logout`, { method: "POST" }),
    setTheme: (theme) => request("/auth/theme", { method: "PUT", body: JSON.stringify({ theme }) }),
    requestApproval: (module, recordId, fromStatus, toStatus, note) => request("/approvals", {
      method: "POST",
      body: JSON.stringify({ module, record_id: recordId, from_status: fromStatus, to_status: toStatus, note })
    }),
    listPendingApprovals: () => request("/approvals/pending"),
    decideApproval: (id, approve, note) => request(`/approvals/${id}/decide`, { method: "POST", body: JSON.stringify({ approve, note }) }),
    listNotifications: () => request("/notifications"),
    unreadNotificationCount: () => request("/notifications/unread-count"),
    markNotificationRead: (id) => request(`/notifications/${id}/read`, { method: "POST" }),
    markAllNotificationsRead: () => request("/notifications/read-all", { method: "POST" }),
    getNumberSeries: (module, field) => request(
      `/admin/number-series/${module}/${field}`
    ),
    setNumberSeries: (module, field, body) => request(
      `/admin/number-series/${module}/${field}`,
      { method: "PUT", body: JSON.stringify(body) }
    ),
    listDeleted: (module) => request(`/data/${module}/deleted`),
    restoreRecord: (module, id) => request(`/data/${module}/${id}/restore`, { method: "POST" }),
    exportRecords: async (module) => {
      const res = await fetchImpl(`/api/data/${module}/export`, { method: "POST", credentials: "include" });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
      return res.blob();
    },
    importRecords: async (module, file) => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetchImpl(`/api/data/${module}/import`, { method: "POST", body: form, credentials: "include" });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
      return res.json();
    }
  };
}
const api = createApi();
export {
  api as a,
  createApi as c
};
