import { c as createApi } from "../../../../chunks/api.js";
const load = async ({ fetch, parent }) => {
  const { modules } = await parent();
  const api = createApi(fetch);
  const [roles, users] = await Promise.all([api.listRoles(), api.listUsers()]);
  return { roles, users, modules };
};
export {
  load
};
