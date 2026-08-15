import { c as ensure_array_like, a as attr, e as escape_html } from "../../chunks/index2.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data } = $$props;
    $$renderer2.push(`<div class="mx-auto max-w-5xl p-8"><h1 class="mb-1 text-2xl font-semibold">Modules</h1> <p class="mb-6 text-sm text-neutral-500">Every module defined in the builder, generated into a full CRUD app.</p> `);
    if (data.modules.length === 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-neutral-200 py-16 text-center dark:border-neutral-800"><p class="text-sm font-medium text-neutral-700 dark:text-neutral-300">No modules yet</p> <p class="max-w-sm text-sm text-neutral-400">Define your first module — its fields, relationships, and embedded grids — in the builder.</p> <a href="/admin/builder" class="mt-2 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700">Open builder</a></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"><!--[-->`);
      const each_array = ensure_array_like(data.modules);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let m = each_array[$$index];
        $$renderer2.push(`<a${attr("href", `/${m.name}`)} class="rounded-lg border border-neutral-200 bg-white p-4 hover:border-neutral-300 hover:shadow-sm dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-neutral-700"><p class="font-medium">${escape_html(m.label)}</p> <p class="mt-1 text-sm text-neutral-400">${escape_html(m.fields.length)} ${escape_html(m.fields.length === 1 ? "field" : "fields")} `);
        if (m.relationships.length) {
          $$renderer2.push("<!--[0-->");
          $$renderer2.push(`· ${escape_html(m.relationships.length)} ${escape_html(m.relationships.length === 1 ? "relation" : "relations")}`);
        } else {
          $$renderer2.push("<!--[-1-->");
        }
        $$renderer2.push(`<!--]--></p></a>`);
      }
      $$renderer2.push(`<!--]--> <a href="/admin/builder" class="flex items-center justify-center rounded-lg border border-dashed border-neutral-300 p-4 text-sm text-neutral-400 hover:border-neutral-400 hover:text-neutral-600 dark:border-neutral-700 dark:hover:border-neutral-600 dark:hover:text-neutral-300">+ New module</a></div>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
