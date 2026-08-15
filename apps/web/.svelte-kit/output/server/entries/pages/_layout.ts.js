import { redirect } from "@sveltejs/kit";
import { c as createApi } from "../../chunks/api.js";
import { f as fetchCurrentUser } from "../../chunks/auth.svelte.js";
import { a as loadLocalization } from "../../chunks/localization.svelte.js";
const ssr = false;
const load = async ({ fetch, depends, url }) => {
  depends("app:modules");
  depends("app:localization");
  depends("app:auth");
  const user = await fetchCurrentUser(fetch);
  if (!user) {
    if (url.pathname !== "/login") {
      const redirectTo = url.pathname === "/" ? "" : `?redirect=${encodeURIComponent(url.pathname + url.search)}`;
      throw redirect(303, `/login${redirectTo}`);
    }
    return { modules: [], user: null };
  }
  const [modules] = await Promise.all([createApi(fetch).listModules(), loadLocalization(fetch)]);
  return { modules, user };
};
export {
  load,
  ssr
};
