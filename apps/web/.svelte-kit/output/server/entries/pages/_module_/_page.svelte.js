import "clsx";
import { p as props_id, g as attributes, h as bind_props, d as derived, c as ensure_array_like, b as attr_class, a as attr, e as escape_html, i as await_block } from "../../../chunks/index2.js";
import { g as goto } from "../../../chunks/client.js";
import { d as displayName, e as embeddedChildren } from "../../../chunks/types.js";
import { createTable, getCoreRowModel, getGroupedRowModel, getExpandedRowModel, getSortedRowModel } from "@tanstack/table-core";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/root.js";
import "../../../chunks/state.svelte.js";
import { b as Dialog, c as Dialog_content, M as Menu, a as Menu_trigger, D as Dropdown_menu_content } from "../../../chunks/menu-trigger.js";
import { c as createId, a as DialogCloseState, b as boxWith, m as mergeProps, P as Portal, D as Dialog_overlay } from "../../../chunks/dialog-overlay.js";
import { D as Dialog_title, a as Dialog_description } from "../../../chunks/dialog-description.js";
import { f as formatDateDisplay, a as formatMoney, b as formatPercent, c as formatDecimal } from "../../../chunks/format.js";
import { c as canDelete, b as canCreate } from "../../../chunks/auth.svelte.js";
function Dialog_close($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const uid = props_id($$renderer2);
    let {
      children,
      child,
      id = createId(uid),
      ref = null,
      disabled = false,
      $$slots,
      $$events,
      ...restProps
    } = $$props;
    const closeState = DialogCloseState.create({
      variant: boxWith(() => "close"),
      id: boxWith(() => id),
      ref: boxWith(() => ref, (v) => ref = v),
      disabled: boxWith(() => Boolean(disabled))
    });
    const mergedProps = derived(() => mergeProps(restProps, closeState.props));
    if (child) {
      $$renderer2.push("<!--[0-->");
      child($$renderer2, { props: mergedProps() });
      $$renderer2.push(`<!---->`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<button${attributes({ ...mergedProps() })}>`);
      children?.($$renderer2);
      $$renderer2.push(`<!----></button>`);
    }
    $$renderer2.push(`<!--]-->`);
    bind_props($$props, { ref });
  });
}
function isFunction(d) {
  return typeof d === "function";
}
function functionalUpdate(updater, old) {
  return isFunction(updater) ? updater(old) : updater;
}
function mergeObjects(...sources) {
  const target = {};
  for (const source of sources) {
    if (!source) continue;
    for (const key of Object.keys(source)) {
      Object.defineProperty(target, key, {
        get() {
          return source[key];
        },
        enumerable: true,
        configurable: true
      });
    }
  }
  return target;
}
function createSvelteTable(options) {
  const resolvedOptions = mergeObjects(
    {
      state: {},
      onStateChange: () => {
      },
      renderFallbackValue: null,
      mergeOptions: (defaultOptions, opts) => mergeObjects(defaultOptions, opts)
    },
    options
  );
  const table = createTable(resolvedOptions);
  let state = table.initialState;
  function updateOptions() {
    table.setOptions((prev) => mergeObjects(prev, options, {
      state: mergeObjects(state, options.state ?? {}),
      onStateChange: (updater) => {
        state = functionalUpdate(updater, state);
        options.onStateChange?.(updater);
      }
    }));
  }
  updateOptions();
  return table;
}
function DataTable($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let {
      data,
      columns,
      groupBy = null,
      expandable = false,
      subRow,
      onRowClick
      /** One-way: DataTable never writes this back. Grouping is derived
       * from it via a `state.grouping` getter, not synced through an
       * effect — see create-svelte-table.svelte.ts for why that matters. */
    } = $$props;
    const coreRowModel = getCoreRowModel();
    const groupedRowModel = getGroupedRowModel();
    const expandedRowModel = getExpandedRowModel();
    const sortedRowModel = getSortedRowModel();
    const getRowId = (row) => row.id;
    let sorting = [];
    const table = createSvelteTable({
      get data() {
        return data;
      },
      get columns() {
        return columns;
      },
      state: {
        get grouping() {
          return groupBy ? [groupBy] : [];
        },
        get sorting() {
          return sorting;
        }
      },
      onSortingChange: (updater) => {
        sorting = typeof updater === "function" ? updater(sorting) : updater;
      },
      getCoreRowModel: coreRowModel,
      getGroupedRowModel: groupedRowModel,
      getExpandedRowModel: expandedRowModel,
      getSortedRowModel: sortedRowModel,
      getRowId,
      // Without this, toggleExpanded() is a silent no-op: TanStack's
      // default expandability check looks for real `subRows` data, which
      // we don't have — the sub-row content here is our own `subRow`
      // snippet, not TanStack's subRow rendering.
      getRowCanExpand: () => expandable,
      groupedColumnMode: false,
      // The actual root cause of the earlier infinite-loop bug: this
      // defaults to on whenever getExpandedRowModel is provided, and
      // resets `expanded` to a fresh {} via a queued microtask whenever it
      // detects data/grouping changes — feeding a new object identity back
      // through onExpandedChange on every row-model computation. Expansion
      // reset, if ever needed, should be an explicit call
      // (table.resetExpanded()) at the point the intent actually lives,
      // not an implicit background loop.
      autoResetExpanded: false
    });
    $$renderer2.push(`<div class="max-h-[70vh] overflow-auto"><table class="w-full border-collapse text-sm"><thead><tr class="text-left">`);
    if (expandable) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<th class="sticky top-0 z-10 w-8 border-b border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900"></th>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--><!--[-->`);
    const each_array = ensure_array_like(table.getHeaderGroups()[0]?.headers ?? []);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let header = each_array[$$index];
      const sort = header.column.getIsSorted();
      $$renderer2.push(`<th${attr_class(`sticky top-0 z-10 border-b border-neutral-200 bg-white px-3 py-2 font-medium text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900 ${header.column.getCanSort() ? "cursor-pointer select-none hover:text-neutral-700 dark:hover:text-neutral-300" : ""}`)}${attr("aria-sort", sort === "asc" ? "ascending" : sort === "desc" ? "descending" : "none")}><span class="inline-flex items-center gap-1">${escape_html(typeof header.column.columnDef.header === "string" ? header.column.columnDef.header : header.id)} `);
      if (sort === "asc") {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<span class="text-neutral-400">▲</span>`);
      } else if (sort === "desc") {
        $$renderer2.push("<!--[1-->");
        $$renderer2.push(`<span class="text-neutral-400">▼</span>`);
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--></span></th>`);
    }
    $$renderer2.push(`<!--]--></tr></thead><tbody><!--[-->`);
    const each_array_1 = ensure_array_like(table.getRowModel().rows);
    for (let i = 0, $$length = each_array_1.length; i < $$length; i++) {
      let row = each_array_1[i];
      if (row.getIsGrouped()) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<tr class="bg-neutral-50 dark:bg-neutral-900"><td${attr("colspan", columns.length + (expandable ? 1 : 0))} class="px-3 py-2 font-medium"><button type="button" class="mr-1">${escape_html(row.getIsExpanded() ? "▾" : "▸")}</button> ${escape_html(String(row.getValue(row.groupingColumnId ?? "")))} <span class="ml-2 text-neutral-400">(${escape_html(row.subRows.length)})</span></td></tr>`);
      } else {
        $$renderer2.push("<!--[-1-->");
        $$renderer2.push(`<tr${attr_class(`border-b border-neutral-100 dark:border-neutral-900 ${i % 2 === 1 ? "bg-neutral-50/60 dark:bg-neutral-900/40" : ""} ${onRowClick ? "cursor-pointer hover:bg-primary-50/60 dark:hover:bg-primary-950/30" : ""}`)}>`);
        if (expandable) {
          $$renderer2.push("<!--[0-->");
          $$renderer2.push(`<td class="px-2"><button type="button">${escape_html(row.getIsExpanded() ? "▾" : "▸")}</button></td>`);
        } else {
          $$renderer2.push("<!--[-1-->");
        }
        $$renderer2.push(`<!--]--><!--[-->`);
        const each_array_2 = ensure_array_like(row.getVisibleCells());
        for (let $$index_1 = 0, $$length2 = each_array_2.length; $$index_1 < $$length2; $$index_1++) {
          let cell = each_array_2[$$index_1];
          const meta = cell.column.columnDef.meta;
          $$renderer2.push(`<td${attr_class(`px-3 py-2 ${meta?.align === "right" ? "text-right tabular-nums" : ""}`)}>${escape_html(meta?.format ? meta.format(cell.getValue()) : String(cell.getValue() ?? ""))}</td>`);
        }
        $$renderer2.push(`<!--]--></tr> `);
        if (expandable && row.getIsExpanded() && subRow) {
          $$renderer2.push("<!--[0-->");
          $$renderer2.push(`<tr><td${attr("colspan", columns.length + 1)} class="bg-neutral-50 px-6 py-3 dark:bg-neutral-950">`);
          subRow($$renderer2, row.original);
          $$renderer2.push(`<!----></td></tr>`);
        } else {
          $$renderer2.push("<!--[-1-->");
        }
        $$renderer2.push(`<!--]-->`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></tbody></table></div>`);
  });
}
function EmptyState($$renderer, $$props) {
  let { title, description, actionLabel, actionHref } = $$props;
  $$renderer.push(`<div class="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-neutral-200 py-16 text-center dark:border-neutral-800"><p class="text-sm font-medium text-neutral-700 dark:text-neutral-300">${escape_html(title)}</p> `);
  if (description) {
    $$renderer.push("<!--[0-->");
    $$renderer.push(`<p class="max-w-sm text-sm text-neutral-400">${escape_html(description)}</p>`);
  } else {
    $$renderer.push("<!--[-1-->");
  }
  $$renderer.push(`<!--]--> `);
  if (actionLabel && actionHref) {
    $$renderer.push("<!--[0-->");
    $$renderer.push(`<a${attr("href", actionHref)} class="mt-2 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700">${escape_html(actionLabel)}</a>`);
  } else {
    $$renderer.push("<!--[-1-->");
  }
  $$renderer.push(`<!--]--></div>`);
}
function RecycleBinDialog($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { open = false, module } = $$props;
    let rows = [];
    let restoringId = null;
    let $$settled = true;
    let $$inner_renderer;
    function $$render_inner($$renderer3) {
      if (Dialog) {
        $$renderer3.push("<!--[-->");
        Dialog($$renderer3, {
          get open() {
            return open;
          },
          set open($$value) {
            open = $$value;
            $$settled = false;
          },
          children: ($$renderer4) => {
            if (Portal) {
              $$renderer4.push("<!--[-->");
              Portal($$renderer4, {
                children: ($$renderer5) => {
                  if (Dialog_overlay) {
                    $$renderer5.push("<!--[-->");
                    Dialog_overlay($$renderer5, { class: "fixed inset-0 z-50 bg-black/40" });
                    $$renderer5.push("<!--]-->");
                  } else {
                    $$renderer5.push("<!--[!-->");
                    $$renderer5.push("<!--]-->");
                  }
                  $$renderer5.push(` `);
                  if (Dialog_content) {
                    $$renderer5.push("<!--[-->");
                    Dialog_content($$renderer5, {
                      class: "fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border border-neutral-200 bg-white p-5 shadow-xl dark:border-neutral-800 dark:bg-neutral-900",
                      children: ($$renderer6) => {
                        if (Dialog_title) {
                          $$renderer6.push("<!--[-->");
                          Dialog_title($$renderer6, {
                            class: "text-base font-semibold",
                            children: ($$renderer7) => {
                              $$renderer7.push(`<!---->${escape_html(module.label)} — Recycle Bin`);
                            },
                            $$slots: { default: true }
                          });
                          $$renderer6.push("<!--]-->");
                        } else {
                          $$renderer6.push("<!--[!-->");
                          $$renderer6.push("<!--]-->");
                        }
                        $$renderer6.push(` `);
                        if (Dialog_description) {
                          $$renderer6.push("<!--[-->");
                          Dialog_description($$renderer6, {
                            class: "mt-1 text-sm text-neutral-500",
                            children: ($$renderer7) => {
                              $$renderer7.push(`<!---->Deleted records, most recent first. Restoring puts a record back exactly as it was.`);
                            },
                            $$slots: { default: true }
                          });
                          $$renderer6.push("<!--]-->");
                        } else {
                          $$renderer6.push("<!--[!-->");
                          $$renderer6.push("<!--]-->");
                        }
                        $$renderer6.push(` <div class="mt-4 max-h-80 overflow-y-auto">`);
                        if (rows.length === 0) {
                          $$renderer6.push("<!--[1-->");
                          $$renderer6.push(`<p class="py-6 text-center text-sm text-neutral-400">Nothing in the recycle bin.</p>`);
                        } else {
                          $$renderer6.push("<!--[-1-->");
                          $$renderer6.push(`<ul class="divide-y divide-neutral-100 dark:divide-neutral-800"><!--[-->`);
                          const each_array = ensure_array_like(rows);
                          for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
                            let row = each_array[$$index];
                            $$renderer6.push(`<li class="flex items-center justify-between py-2"><span class="text-sm">${escape_html(displayName(row, row.id))}</span> <button type="button"${attr("disabled", restoringId === row.id, true)} class="rounded-md border border-neutral-300 px-2.5 py-1 text-xs font-medium hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-800">${escape_html(restoringId === row.id ? "Restoring…" : "Restore")}</button></li>`);
                          }
                          $$renderer6.push(`<!--]--></ul>`);
                        }
                        $$renderer6.push(`<!--]--></div> <div class="mt-4 flex justify-end">`);
                        if (Dialog_close) {
                          $$renderer6.push("<!--[-->");
                          Dialog_close($$renderer6, {
                            class: "rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800",
                            children: ($$renderer7) => {
                              $$renderer7.push(`<!---->Close`);
                            },
                            $$slots: { default: true }
                          });
                          $$renderer6.push("<!--]-->");
                        } else {
                          $$renderer6.push("<!--[!-->");
                          $$renderer6.push("<!--]-->");
                        }
                        $$renderer6.push(`</div>`);
                      },
                      $$slots: { default: true }
                    });
                    $$renderer5.push("<!--]-->");
                  } else {
                    $$renderer5.push("<!--[!-->");
                    $$renderer5.push("<!--]-->");
                  }
                }
              });
              $$renderer4.push("<!--]-->");
            } else {
              $$renderer4.push("<!--[!-->");
              $$renderer4.push("<!--]-->");
            }
          },
          $$slots: { default: true }
        });
        $$renderer3.push("<!--]-->");
      } else {
        $$renderer3.push("<!--[!-->");
        $$renderer3.push("<!--]-->");
      }
    }
    do {
      $$settled = true;
      $$inner_renderer = $$renderer2.copy();
      $$render_inner($$inner_renderer);
    } while (!$$settled);
    $$renderer2.subsume($$inner_renderer);
    bind_props($$props, { open });
  });
}
function ListPage($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let {
      module,
      records,
      lookupLabels = {}
      /** field name -> { foreign id -> display label }, resolved once in `load()`. */
    } = $$props;
    const listFields = derived(() => module.fields.filter((f) => f.name !== "id").slice(0, 6));
    const rels = derived(() => embeddedChildren(module));
    const hasChildren = derived(() => rels().length > 0);
    let groupBy = null;
    let search = "";
    let recycleBinOpen = false;
    let exporting = false;
    let importing = false;
    const filteredRecords = derived(() => {
      const term = search.trim().toLowerCase();
      if (!term) return records;
      return records.filter((r) => listFields().some((f) => {
        const raw = r[f.name];
        const format = formatterFor(f);
        const displayed = format ? format(raw) : raw;
        return String(displayed ?? "").toLowerCase().includes(term);
      }));
    });
    const numericTypes = /* @__PURE__ */ new Set(["INTEGER", "DECIMAL", "MONEY", "PERCENT"]);
    function formatterFor(f) {
      if (f.data_type === "LOOKUP") {
        const labelMap = lookupLabels[f.name];
        return labelMap ? (v) => labelMap[String(v)] ?? String(v ?? "") : void 0;
      }
      if (f.data_type === "DATE") return (v) => formatDateDisplay(v);
      if (f.data_type === "MONEY") return (v) => formatMoney(v);
      if (f.data_type === "PERCENT") return (v) => formatPercent(v);
      if (f.data_type === "DECIMAL") return (v) => formatDecimal(v, f.precision ?? 2);
      if (f.data_type === "BOOLEAN") {
        if (f.is_default_flag) return (v) => v ? "★ Default" : "";
        return (v) => v ? "Yes" : "No";
      }
      return void 0;
    }
    const columns = derived(() => listFields().map((f) => {
      const format = formatterFor(f);
      const align = numericTypes.has(f.data_type) ? "right" : void 0;
      return {
        id: f.name,
        accessorKey: f.name,
        header: f.label,
        enableGrouping: f.data_type === "ENUM" || f.data_type === "LOOKUP" || f.data_type === "BOOLEAN",
        meta: format || align ? { format, align } : void 0
      };
    }));
    const groupableFields = derived(() => listFields().filter((f) => f.data_type === "ENUM" || f.data_type === "BOOLEAN"));
    const childRowsByParent = {};
    async function loadChildren(parentId) {
      if (childRowsByParent[parentId]) return;
      const all = [];
      for (const rel of rels()) {
        const res = await fetch(`/api/data/${rel.related_module}?${rel.foreign_key}=${parentId}`);
        if (res.ok) {
          const rows = await res.json();
          all.push(...Array.isArray(rows) ? rows : rows.items ?? []);
        }
      }
      childRowsByParent[parentId] = all;
    }
    function openRecord(record) {
      goto(`/${module.name}/${record.id}`);
    }
    function childrenPreview($$renderer3, record) {
      await_block(
        $$renderer3,
        loadChildren(record.id),
        () => {
          $$renderer3.push(`<span class="text-xs text-neutral-400">Loading…</span>`);
        },
        () => {
          if (childRowsByParent[record.id]?.length) {
            $$renderer3.push("<!--[0-->");
            $$renderer3.push(`<ul class="space-y-1 text-xs text-neutral-600 dark:text-neutral-400"><!--[-->`);
            const each_array = ensure_array_like(childRowsByParent[record.id]);
            for (let $$index_2 = 0, $$length = each_array.length; $$index_2 < $$length; $$index_2++) {
              let child = each_array[$$index_2];
              $$renderer3.push(`<li>${escape_html(Object.values(child).slice(1, 4).join(" · "))}</li>`);
            }
            $$renderer3.push(`<!--]--></ul>`);
          } else {
            $$renderer3.push("<!--[-1-->");
            $$renderer3.push(`<span class="text-xs text-neutral-400">No related records</span>`);
          }
          $$renderer3.push(`<!--]-->`);
        }
      );
      $$renderer3.push(`<!--]-->`);
    }
    let $$settled = true;
    let $$inner_renderer;
    function $$render_inner($$renderer3) {
      $$renderer3.push(`<div class="p-4 sm:p-6"><div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h1 class="text-xl font-semibold">${escape_html(module.label)}</h1> <p class="text-sm text-neutral-400">${escape_html(records.length)} ${escape_html(records.length === 1 ? "record" : "records")}</p></div> <div class="flex flex-wrap items-center gap-2 sm:gap-3">`);
      if (records.length > 0) {
        $$renderer3.push("<!--[0-->");
        $$renderer3.push(`<input type="search" placeholder="Search…"${attr("value", search)} class="h-9 w-full flex-1 rounded-md border border-neutral-300 px-3 text-sm outline-none focus:ring-2 focus:ring-primary-500 sm:w-48 sm:flex-none dark:border-neutral-700 dark:bg-neutral-900"/>`);
      } else {
        $$renderer3.push("<!--[-1-->");
      }
      $$renderer3.push(`<!--]--> `);
      if (groupableFields().length) {
        $$renderer3.push("<!--[0-->");
        $$renderer3.push(`<label class="hidden text-sm text-neutral-500 sm:inline-flex sm:items-center">Group by `);
        $$renderer3.select(
          {
            value: groupBy,
            class: "ml-1 rounded-md border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          },
          ($$renderer4) => {
            $$renderer4.option({ value: null }, ($$renderer5) => {
              $$renderer5.push(`None`);
            });
            $$renderer4.push(`<!--[-->`);
            const each_array_1 = ensure_array_like(groupableFields());
            for (let $$index = 0, $$length = each_array_1.length; $$index < $$length; $$index++) {
              let f = each_array_1[$$index];
              $$renderer4.option({ value: f.name }, ($$renderer5) => {
                $$renderer5.push(`${escape_html(f.label)}`);
              });
            }
            $$renderer4.push(`<!--]-->`);
          }
        );
        $$renderer3.push(`</label>`);
      } else {
        $$renderer3.push("<!--[-1-->");
      }
      $$renderer3.push(`<!--]--> <div class="sm:hidden">`);
      if (Menu) {
        $$renderer3.push("<!--[-->");
        Menu($$renderer3, {
          children: ($$renderer4) => {
            if (Menu_trigger) {
              $$renderer4.push("<!--[-->");
              Menu_trigger($$renderer4, {
                class: "flex h-9 w-9 items-center justify-center rounded-md border border-neutral-300 text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800",
                "aria-label": "More actions",
                children: ($$renderer5) => {
                  $$renderer5.push(`<!---->⋯`);
                },
                $$slots: { default: true }
              });
              $$renderer4.push("<!--]-->");
            } else {
              $$renderer4.push("<!--[!-->");
              $$renderer4.push("<!--]-->");
            }
            $$renderer4.push(` `);
            if (Portal) {
              $$renderer4.push("<!--[-->");
              Portal($$renderer4, {
                children: ($$renderer5) => {
                  if (Dropdown_menu_content) {
                    $$renderer5.push("<!--[-->");
                    Dropdown_menu_content($$renderer5, {
                      class: "z-50 w-52 rounded-md border border-neutral-200 bg-white p-1 shadow-xl dark:border-neutral-800 dark:bg-neutral-900",
                      align: "end",
                      sideOffset: 6,
                      children: ($$renderer6) => {
                        if (groupableFields().length) {
                          $$renderer6.push("<!--[0-->");
                          $$renderer6.push(`<label class="block px-2 py-1.5 text-sm text-neutral-500">Group by `);
                          $$renderer6.select(
                            {
                              value: groupBy,
                              class: "mt-1 w-full rounded-md border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
                            },
                            ($$renderer7) => {
                              $$renderer7.option({ value: null }, ($$renderer8) => {
                                $$renderer8.push(`None`);
                              });
                              $$renderer7.push(`<!--[-->`);
                              const each_array_2 = ensure_array_like(groupableFields());
                              for (let $$index_1 = 0, $$length = each_array_2.length; $$index_1 < $$length; $$index_1++) {
                                let f = each_array_2[$$index_1];
                                $$renderer7.option({ value: f.name }, ($$renderer8) => {
                                  $$renderer8.push(`${escape_html(f.label)}`);
                                });
                              }
                              $$renderer7.push(`<!--]-->`);
                            }
                          );
                          $$renderer6.push(`</label>`);
                        } else {
                          $$renderer6.push("<!--[-1-->");
                        }
                        $$renderer6.push(`<!--]--> `);
                        if (canDelete(module.name)) {
                          $$renderer6.push("<!--[0-->");
                          $$renderer6.push(`<button type="button" class="block w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800">Recycle bin</button>`);
                        } else {
                          $$renderer6.push("<!--[-1-->");
                        }
                        $$renderer6.push(`<!--]--> <button type="button"${attr("disabled", exporting, true)} class="block w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-neutral-100 disabled:opacity-50 dark:hover:bg-neutral-800">${escape_html("Export CSV")}</button> `);
                        if (canCreate(module.name)) {
                          $$renderer6.push("<!--[0-->");
                          $$renderer6.push(`<button type="button"${attr("disabled", importing, true)} class="block w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-neutral-100 disabled:opacity-50 dark:hover:bg-neutral-800">${escape_html("Import CSV")}</button>`);
                        } else {
                          $$renderer6.push("<!--[-1-->");
                        }
                        $$renderer6.push(`<!--]-->`);
                      },
                      $$slots: { default: true }
                    });
                    $$renderer5.push("<!--]-->");
                  } else {
                    $$renderer5.push("<!--[!-->");
                    $$renderer5.push("<!--]-->");
                  }
                }
              });
              $$renderer4.push("<!--]-->");
            } else {
              $$renderer4.push("<!--[!-->");
              $$renderer4.push("<!--]-->");
            }
          },
          $$slots: { default: true }
        });
        $$renderer3.push("<!--]-->");
      } else {
        $$renderer3.push("<!--[!-->");
        $$renderer3.push("<!--]-->");
      }
      $$renderer3.push(`</div> <div class="hidden items-center gap-2 sm:flex sm:gap-3">`);
      if (canDelete(module.name)) {
        $$renderer3.push("<!--[0-->");
        $$renderer3.push(`<button type="button" class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800">Recycle bin</button>`);
      } else {
        $$renderer3.push("<!--[-1-->");
      }
      $$renderer3.push(`<!--]--> <button type="button"${attr("disabled", exporting, true)} class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800">${escape_html("Export CSV")}</button> `);
      if (canCreate(module.name)) {
        $$renderer3.push("<!--[0-->");
        $$renderer3.push(`<button type="button"${attr("disabled", importing, true)} class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800">${escape_html("Import CSV")}</button>`);
      } else {
        $$renderer3.push("<!--[-1-->");
      }
      $$renderer3.push(`<!--]--></div> <input type="file" accept=".csv,text/csv" class="hidden"/> <a${attr("href", `/${module.name}/new`)} class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium whitespace-nowrap text-white hover:bg-primary-700">New ${escape_html(module.label)}</a></div></div> `);
      if (canDelete(module.name)) {
        $$renderer3.push("<!--[0-->");
        RecycleBinDialog($$renderer3, {
          module,
          get open() {
            return recycleBinOpen;
          },
          set open($$value) {
            recycleBinOpen = $$value;
            $$settled = false;
          }
        });
      } else {
        $$renderer3.push("<!--[-1-->");
      }
      $$renderer3.push(`<!--]--> `);
      if (records.length === 0) {
        $$renderer3.push("<!--[0-->");
        EmptyState($$renderer3, {
          title: `No ${module.label.toLowerCase()} yet`,
          description: `Create the first ${module.label.toLowerCase()} record to get started.`,
          actionLabel: `New ${module.label}`,
          actionHref: `/${module.name}/new`
        });
      } else if (filteredRecords().length === 0) {
        $$renderer3.push("<!--[1-->");
        EmptyState($$renderer3, {
          title: "No matches",
          description: `Nothing matches "${search}".`
        });
      } else {
        $$renderer3.push("<!--[-1-->");
        $$renderer3.push(`<div class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">`);
        DataTable($$renderer3, {
          data: filteredRecords(),
          columns: columns(),
          groupBy,
          expandable: hasChildren(),
          subRow: hasChildren() ? childrenPreview : void 0,
          onRowClick: openRecord
        });
        $$renderer3.push(`<!----></div>`);
      }
      $$renderer3.push(`<!--]--></div>`);
    }
    do {
      $$settled = true;
      $$inner_renderer = $$renderer2.copy();
      $$render_inner($$inner_renderer);
    } while (!$$settled);
    $$renderer2.subsume($$inner_renderer);
  });
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data } = $$props;
    ListPage($$renderer2, {
      module: data.module,
      records: data.records,
      lookupLabels: data.lookupLabels
    });
  });
}
export {
  _page as default
};
