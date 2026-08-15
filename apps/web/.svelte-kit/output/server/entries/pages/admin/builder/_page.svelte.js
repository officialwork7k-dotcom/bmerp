import { c as ensure_array_like, b as attr_class, e as escape_html, a as attr, m as clsx } from "../../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../../chunks/exports.js";
import "../../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../../chunks/root.js";
import "../../../../chunks/state.svelte.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data } = $$props;
    let modules = data.modules;
    let selectedName = modules[0]?.name ?? null;
    let draft = structuredCloneModule(modules[0]);
    let activeTab = "settings";
    let newModuleName = "";
    let saving = false;
    function structuredCloneModule(m) {
      return m ? JSON.parse(JSON.stringify(m)) : null;
    }
    const inputClass = "h-9 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900";
    $$renderer2.push(`<div class="flex min-h-screen flex-col md:flex-row"><aside class="w-full shrink-0 border-b border-neutral-200 p-4 md:w-56 md:border-b-0 md:border-r dark:border-neutral-800"><h2 class="mb-3 text-xs font-semibold uppercase text-neutral-500">Modules</h2> <ul class="space-y-1"><!--[-->`);
    const each_array = ensure_array_like(modules);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let m = each_array[$$index];
      $$renderer2.push(`<li><button type="button"${attr_class(`w-full rounded-md px-2 py-1.5 text-left text-sm ${selectedName === m.name ? "bg-primary-50 font-medium text-primary-700 dark:bg-primary-950 dark:text-primary-300" : "hover:bg-neutral-100 dark:hover:bg-neutral-800"}`)}>${escape_html(m.label)} <span class="ml-1 text-xs text-neutral-400">${escape_html(m.relationships.length)} rel</span></button></li>`);
    }
    $$renderer2.push(`<!--]--></ul> <div class="mt-4 flex gap-1"><input${attr_class(clsx(inputClass))} placeholder="new_module_name"${attr("value", newModuleName)}/> <button type="button" class="rounded-md bg-neutral-900 px-2 text-sm text-white dark:bg-neutral-100 dark:text-neutral-900">+</button></div></aside> <main class="flex-1 p-6">`);
    if (draft) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="mb-4 flex items-center justify-between"><h1 class="text-xl font-semibold">${escape_html(draft.label || draft.name)}</h1> <button type="button"${attr("disabled", saving, true)} class="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">${escape_html("Save module")}</button></div> `);
      {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--> `);
      {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--> <div class="mb-4 flex gap-4 border-b border-neutral-200 dark:border-neutral-800"><!--[-->`);
      const each_array_2 = ensure_array_like([
        ["settings", "Settings"],
        ["fields", "Fields"],
        ["relationships", "Relationships"],
        ["workflow", "Workflow"]
      ]);
      for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
        let [key, label] = each_array_2[$$index_2];
        $$renderer2.push(`<button type="button"${attr_class(`border-b-2 px-1 pb-2 text-sm ${activeTab === key ? "border-primary-600 font-medium text-primary-700 dark:text-primary-400" : "border-transparent text-neutral-500"}`)}>${escape_html(label)}</button>`);
      }
      $$renderer2.push(`<!--]--></div> `);
      {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<div class="max-w-md space-y-3"><div><label class="mb-1 block text-sm font-medium" for="mod-name">Name</label> <input id="mod-name"${attr_class(clsx(inputClass))}${attr("value", draft.name)}${attr("disabled", draft.version > 0, true)}/></div> <div><label class="mb-1 block text-sm font-medium" for="mod-label">Label</label> <input id="mod-label"${attr_class(clsx(inputClass))}${attr("value", draft.label)}/></div></div>`);
      }
      $$renderer2.push(`<!--]-->`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<p class="text-neutral-500">Select or create a module.</p>`);
    }
    $$renderer2.push(`<!--]--></main></div>`);
  });
}
export {
  _page as default
};
