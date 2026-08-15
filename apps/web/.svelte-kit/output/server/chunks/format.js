import { l as localization } from "./localization.svelte.js";
const FORMAT_ORDERS = {
  "DD/MM/YYYY": ["D", "M", "Y"],
  "MM/DD/YYYY": ["M", "D", "Y"],
  "YYYY-MM-DD": ["Y", "M", "D"],
  "DD.MM.YYYY": ["D", "M", "Y"],
  "DD-MM-YYYY": ["D", "M", "Y"]
};
const FORMAT_SEPARATORS = {
  "DD/MM/YYYY": "/",
  "MM/DD/YYYY": "/",
  "YYYY-MM-DD": "-",
  "DD.MM.YYYY": ".",
  "DD-MM-YYYY": "-"
};
function formatDateDisplay(iso, format = localization.date_format) {
  if (!iso) return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return String(iso);
  const [, y, mo, d] = m;
  const sep = FORMAT_SEPARATORS[format] ?? "/";
  const order = FORMAT_ORDERS[format] ?? FORMAT_ORDERS["DD/MM/YYYY"];
  const map = { D: d, M: mo, Y: y };
  return order.map((token) => map[token]).join(sep);
}
const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  INR: "₹",
  JPY: "¥",
  AUD: "A$",
  CAD: "C$",
  CNY: "¥"
};
function formatNumber(value, decimals, decimalSep = localization.decimal_separator, thousandsSep = localization.thousands_separator) {
  const fixed = Math.abs(value).toFixed(decimals);
  const [intPart, fracPart] = fixed.split(".");
  const grouped = thousandsSep === "none" ? intPart : intPart.replace(/\B(?=(\d{3})+(?!\d))/g, thousandsSep);
  const magnitude = grouped + (fracPart ? decimalSep + fracPart : "");
  if (value >= 0) return magnitude;
  return localization.negative_number_format.startsWith("(") ? `(${magnitude})` : `-${magnitude}`;
}
function formatMoney(value, currencyCode = localization.currency_code) {
  if (value === void 0 || value === null || value === "") return "";
  const symbol = CURRENCY_SYMBOLS[currencyCode] ?? currencyCode + " ";
  const num = Number(value);
  const body = formatNumber(num, 2);
  if (localization.currency_symbol_position === "after") return `${body} ${symbol}`;
  return num < 0 && body.startsWith("-") ? `-${symbol}${body.slice(1)}` : `${symbol}${body}`;
}
function formatDecimal(value, decimals = 2) {
  if (value === void 0 || value === null || value === "") return "";
  return formatNumber(Number(value), decimals);
}
function formatPercent(value) {
  if (value === void 0 || value === null || value === "") return "";
  return formatNumber(Number(value), 2) + "%";
}
export {
  CURRENCY_SYMBOLS as C,
  formatMoney as a,
  formatPercent as b,
  formatDecimal as c,
  formatDateDisplay as f
};
