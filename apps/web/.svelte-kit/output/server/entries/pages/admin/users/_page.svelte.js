import { b as attr_class, c as ensure_array_like, e as escape_html, a as attr, m as clsx } from "../../../../chunks/index2.js";
import { C as ConfirmDialog } from "../../../../chunks/ConfirmDialog.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data } = $$props;
    let roles = data.roles;
    data.users;
    const modules = data.modules;
    const ACTIONS = ["read", "create", "update", "delete"];
    function emptyRole() {
      return { id: "", name: "", is_admin: false, module_permissions: {} };
    }
    let roleDraft = emptyRole();
    let roleSaving = false;
    let roleDeleteOpen = false;
    async function confirmDeleteRole() {
      return;
    }
    const inputClass = "h-9 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900";
    let $$settled = true;
    let $$inner_renderer;
    function $$render_inner($$renderer3) {
      $$renderer3.push(`<div class="mx-auto max-w-5xl space-y-6 p-6"><div><h1 class="text-xl font-semibold">Users &amp; Roles</h1> <p class="text-sm text-neutral-500">Manage who can sign in and what each role can do. Not a generic module — the permission matrix is shaped
			against the live module list, which field metadata can't express.</p></div> <div class="flex gap-1 border-b border-neutral-200 dark:border-neutral-800"><button type="button"${attr_class(`border-b-2 px-3 py-2 text-sm font-medium ${"border-primary-600 text-primary-600"}`)}>Roles</button> <button type="button"${attr_class(`border-b-2 px-3 py-2 text-sm font-medium ${"border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"}`)}>Users</button></div> `);
      {
        $$renderer3.push("<!--[0-->");
        $$renderer3.push(`<div class="grid grid-cols-1 gap-6 md:grid-cols-[14rem_1fr]"><div><button type="button" class="mb-2 w-full rounded-md border border-dashed border-neutral-300 px-3 py-1.5 text-sm text-neutral-500 hover:border-neutral-400 hover:text-neutral-700 dark:border-neutral-700 dark:hover:text-neutral-300">+ New role</button> <ul class="space-y-1"><!--[-->`);
        const each_array = ensure_array_like(roles);
        for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
          let r = each_array[$$index];
          $$renderer3.push(`<li><button type="button"${attr_class(`w-full rounded-md px-3 py-1.5 text-left text-sm ${roleDraft.id === r.id ? "bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300" : "hover:bg-neutral-100 dark:hover:bg-neutral-800"}`)}>${escape_html(r.name)} `);
          if (r.is_admin) {
            $$renderer3.push("<!--[0-->");
            $$renderer3.push(`<span class="ml-1 text-xs text-neutral-400">(admin)</span>`);
          } else {
            $$renderer3.push("<!--[-1-->");
          }
          $$renderer3.push(`<!--]--></button></li>`);
        }
        $$renderer3.push(`<!--]--></ul></div> <div class="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900"><label class="mb-3 block text-sm"><span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Role name</span> <input${attr("value", roleDraft.name)}${attr_class(clsx(inputClass))}/></label> <label class="mb-4 flex items-center gap-2 text-sm"><input type="checkbox"${attr("checked", roleDraft.is_admin, true)} class="h-4 w-4"/> <span>Administrator (bypasses all permission checks)</span></label> `);
        {
          $$renderer3.push("<!--[0-->");
          $$renderer3.push(`<h3 class="mb-2 text-xs font-semibold uppercase text-neutral-500">Module permissions</h3> <div class="overflow-x-auto rounded-md border border-neutral-200 dark:border-neutral-800"><table class="w-full text-sm"><thead class="bg-neutral-50 dark:bg-neutral-800/50"><tr><th class="px-3 py-2 text-left font-medium">Module</th><!--[-->`);
          const each_array_1 = ensure_array_like(ACTIONS);
          for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
            let action = each_array_1[$$index_1];
            $$renderer3.push(`<th class="px-3 py-2 text-center font-medium capitalize">${escape_html(action)}</th>`);
          }
          $$renderer3.push(`<!--]--></tr></thead><tbody><!--[-->`);
          const each_array_2 = ensure_array_like(modules);
          for (let $$index_3 = 0, $$length = each_array_2.length; $$index_3 < $$length; $$index_3++) {
            let m = each_array_2[$$index_3];
            $$renderer3.push(`<tr class="border-t border-neutral-100 dark:border-neutral-800"><td class="px-3 py-1.5">${escape_html(m.label)}</td><!--[-->`);
            const each_array_3 = ensure_array_like(ACTIONS);
            for (let $$index_2 = 0, $$length2 = each_array_3.length; $$index_2 < $$length2; $$index_2++) {
              let action = each_array_3[$$index_2];
              $$renderer3.push(`<td class="px-3 py-1.5 text-center"><input type="checkbox"${attr("checked", !!roleDraft.module_permissions[m.name]?.[action], true)} class="h-4 w-4"/></td>`);
            }
            $$renderer3.push(`<!--]--></tr>`);
          }
          $$renderer3.push(`<!--]--></tbody></table></div>`);
        }
        $$renderer3.push(`<!--]--> <div class="mt-4 flex items-center gap-3"><button type="button"${attr("disabled", roleSaving, true)} class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">${escape_html("Create role")}</button> `);
        {
          $$renderer3.push("<!--[-1-->");
        }
        $$renderer3.push(`<!--]--></div></div></div>`);
      }
      $$renderer3.push(`<!--]--></div> `);
      ConfirmDialog($$renderer3, {
        title: `Delete role "${roleDraft.name}"?`,
        description: "Users assigned to this role will lose its permissions.",
        confirmLabel: "Delete",
        danger: true,
        onConfirm: confirmDeleteRole,
        get open() {
          return roleDeleteOpen;
        },
        set open($$value) {
          roleDeleteOpen = $$value;
          $$settled = false;
        }
      });
      $$renderer3.push(`<!---->`);
    }
    do {
      $$settled = true;
      $$inner_renderer = $$renderer2.copy();
      $$render_inner($$inner_renderer);
    } while (!$$settled);
    $$renderer2.subsume($$inner_renderer);
  });
}
export {
  _page as default
};
