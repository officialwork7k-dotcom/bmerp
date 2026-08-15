import { c as createApi } from "../../../../chunks/api.js";
const load = async ({ params, fetch, parent }) => {
  await parent();
  const api = createApi(fetch);
  const [module, record] = await Promise.all([
    api.getModule(params.module),
    params.id === "new" ? Promise.resolve(void 0) : api.getRecord(params.module, params.id)
  ]);
  const embeddedRels = module.relationships.filter((r) => r.embedded);
  const childModuleEntries = await Promise.all(
    embeddedRels.map(async (rel) => [rel.related_module, await api.getModule(rel.related_module)])
  );
  const childModules = Object.fromEntries(childModuleEntries);
  return { module, record, childModules };
};
export {
  load
};
