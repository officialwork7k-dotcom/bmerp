import { c as createApi } from "../../../../chunks/api.js";
const load = async ({ fetch, parent }) => {
  await parent();
  const modules = await createApi(fetch).listModules();
  return { modules };
};
export {
  load
};
