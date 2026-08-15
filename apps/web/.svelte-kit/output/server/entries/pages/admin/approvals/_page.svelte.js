import { c as ensure_array_like, a as attr, e as escape_html } from "../../../../chunks/index2.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data } = $$props;
    let approvals = data.approvals;
    let decidingId = null;
    $$renderer2.push(`<div class="mx-auto max-w-3xl space-y-6 p-6"><div><h1 class="text-xl font-semibold">Approvals</h1> <p class="text-sm text-neutral-500">Pending status-transition requests awaiting an admin decision.</p></div> `);
    if (approvals.length === 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex flex-col items-center gap-2 rounded-lg border border-dashed border-neutral-200 py-16 text-center dark:border-neutral-800"><p class="text-sm font-medium text-neutral-700 dark:text-neutral-300">Nothing pending</p> <p class="max-w-sm text-sm text-neutral-400">Requests made from a record's workflow panel show up here.</p></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<ul class="space-y-2"><!--[-->`);
      const each_array = ensure_array_like(approvals);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let a = each_array[$$index];
        $$renderer2.push(`<li class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900"><div class="flex items-center justify-between"><div><p class="text-sm font-medium"><a${attr("href", `/${a.module}/${a.record_id}`)} class="hover:underline">${escape_html(a.module)}</a> : ${escape_html(a.from_status)} → ${escape_html(a.to_status)}</p> `);
        if (a.note) {
          $$renderer2.push("<!--[0-->");
          $$renderer2.push(`<p class="mt-0.5 text-sm text-neutral-500">${escape_html(a.note)}</p>`);
        } else {
          $$renderer2.push("<!--[-1-->");
        }
        $$renderer2.push(`<!--]--> <p class="mt-0.5 text-xs text-neutral-400">Requested ${escape_html(new Date(a.created_at).toLocaleString())}</p></div> <div class="flex items-center gap-2"><button type="button"${attr("disabled", decidingId === a.id, true)} class="rounded-md border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-900 dark:hover:bg-red-950">Reject</button> <button type="button"${attr("disabled", decidingId === a.id, true)} class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">Approve</button></div></div></li>`);
      }
      $$renderer2.push(`<!--]--></ul>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
