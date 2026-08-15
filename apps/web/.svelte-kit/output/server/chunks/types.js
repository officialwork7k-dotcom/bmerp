function embeddedChildren(module) {
  return module.relationships.filter((r) => r.embedded && r.type === "ONE_TO_MANY");
}
function displayName(record, fallback = "Record") {
  if (!record) return fallback;
  const candidate = record.name ?? record.title ?? record.label;
  if (candidate !== void 0 && candidate !== null && candidate !== "") return String(candidate);
  if (typeof record.id === "string") return record.id.slice(0, 8);
  return fallback;
}
export {
  displayName as d,
  embeddedChildren as e
};
