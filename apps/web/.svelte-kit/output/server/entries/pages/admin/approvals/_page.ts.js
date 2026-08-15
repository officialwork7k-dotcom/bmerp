import { c as createApi } from "../../../../chunks/api.js";
const load = async ({ fetch, parent }) => {
  await parent();
  const api = createApi(fetch);
  const approvals = await api.listPendingApprovals();
  return { approvals };
};
export {
  load
};
