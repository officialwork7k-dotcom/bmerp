import { c as createApi } from "../../../chunks/api.js";
import { d as displayName } from "../../../chunks/types.js";
const load = async ({ params, fetch, parent }) => {
  await parent();
  const api = createApi(fetch);
  const [module, records] = await Promise.all([
    api.getModule(params.module),
    api.listRecords(params.module, { limit: "100" })
  ]);
  const lookupFields = module.fields.filter((f) => f.name !== "id" && f.data_type === "LOOKUP" && f.lookup_module);
  const lookupEntries = await Promise.all(
    lookupFields.map(async (field) => {
      const relatedRecords = await api.listRecords(field.lookup_module, { limit: "500" });
      return [field.name, Object.fromEntries(relatedRecords.map((r) => [r.id, displayName(r)]))];
    })
  );
  const lookupLabels = Object.fromEntries(lookupEntries);
  return { module, records, lookupLabels };
};
export {
  load
};
