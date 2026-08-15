import { a as attr, e as escape_html } from "../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/root.js";
import "../../../chunks/state.svelte.js";
import "../../../chunks/client2.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let username = "";
    let password = "";
    let submitting = false;
    $$renderer2.push(`<div class="flex min-h-screen items-center justify-center bg-neutral-50 dark:bg-neutral-950"><form class="w-full max-w-sm rounded-lg border border-neutral-200 bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-900"><h1 class="mb-1 text-lg font-semibold text-neutral-900 dark:text-neutral-100">MetaForge</h1> <p class="mb-6 text-sm text-neutral-500 dark:text-neutral-400">Sign in to continue</p> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <label class="mb-3 block text-sm"><span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Username</span> <input${attr("value", username)} name="username" autocomplete="username" required="" class="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-800"/></label> <label class="mb-6 block text-sm"><span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Password</span> <input${attr("value", password)} name="password" type="password" autocomplete="current-password" required="" class="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-800"/></label> <button type="submit"${attr("disabled", submitting, true)} class="w-full rounded-md bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-60 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-200">${escape_html("Sign in")}</button></form></div>`);
  });
}
export {
  _page as default
};
