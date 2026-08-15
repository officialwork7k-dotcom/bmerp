import "clsx";
import { c as createApi } from "./api.js";
const DEFAULTS = {
  date_format: "DD/MM/YYYY",
  time_format: "24-hour",
  timezone: "UTC",
  first_day_of_week: "Monday",
  decimal_separator: ".",
  thousands_separator: ",",
  currency_code: "USD",
  currency_symbol_position: "before",
  negative_number_format: "-1,234.56",
  fiscal_year_start_month: 1,
  notification_position: "bottom-center",
  notification_duration_seconds: 4
};
const localization = { ...DEFAULTS };
let loadPromise = null;
function loadLocalization(fetchImpl = fetch) {
  if (loadPromise) return loadPromise;
  loadPromise = createApi(fetchImpl).listRecords("localization_settings", { is_default: "true", limit: "1" }).then(async (rows) => {
    let row = Array.isArray(rows) ? rows[0] : void 0;
    if (!row) {
      const fallback = await createApi(fetchImpl).listRecords("localization_settings", { limit: "1" });
      row = Array.isArray(fallback) ? fallback[0] : void 0;
    }
    if (!row) return;
    for (const key of Object.keys(DEFAULTS)) {
      const value = row[key];
      if (typeof value === typeof DEFAULTS[key]) localization[key] = value;
    }
  }).catch(() => {
  });
  return loadPromise;
}
export {
  loadLocalization as a,
  localization as l
};
