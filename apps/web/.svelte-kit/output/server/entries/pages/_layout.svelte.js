import "clsx";
import { p as page } from "../../chunks/index.js";
import { a as attr, b as attr_class, e as escape_html, c as ensure_array_like, d as derived, f as attr_style, s as stringify } from "../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../chunks/exports.js";
import "../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../chunks/root.js";
import "../../chunks/state.svelte.js";
import { a as auth } from "../../chunks/auth.svelte.js";
import { d as displayName } from "../../chunks/types.js";
import { a as api } from "../../chunks/api.js";
import { t as toast } from "../../chunks/toast.svelte.js";
import { M as Menu, a as Menu_trigger, D as Dropdown_menu_content, b as Dialog, c as Dialog_content } from "../../chunks/menu-trigger.js";
import { P as Portal, D as Dialog_overlay } from "../../chunks/dialog-overlay.js";
import { l as localization } from "../../chunks/localization.svelte.js";
function SidebarItem($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { href, label, active, collapsed = false } = $$props;
    $$renderer2.push(`<a${attr("href", href)}${attr("aria-current", active ? "page" : void 0)}${attr("title", collapsed ? label : void 0)}${attr_class(`relative flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors ${active ? "bg-primary-50 font-medium text-primary-900 dark:bg-primary-950 dark:text-primary-100" : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-900"}`)}>`);
    if (active) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<span class="absolute inset-y-1 left-0 w-[3px] rounded-full bg-primary-600"></span>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (collapsed) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<span class="mx-auto flex h-6 w-6 items-center justify-center rounded bg-neutral-200 text-[10px] font-semibold dark:bg-neutral-800">${escape_html(label.slice(0, 2).toUpperCase())}</span>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<span class="truncate">${escape_html(label)}</span>`);
    }
    $$renderer2.push(`<!--]--></a>`);
  });
}
function Sidebar($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { modules, collapsed = false, onToggleCollapse } = $$props;
    const path = derived(() => page.url.pathname);
    function isModuleActive(name) {
      return path() === `/${name}` || path().startsWith(`/${name}/`);
    }
    const builderActive = derived(() => path().startsWith("/admin/builder"));
    $$renderer2.push(`<nav class="flex h-full flex-col gap-4 overflow-y-auto p-3"><div class="flex items-center justify-between px-1"><a href="/" class="flex items-center gap-2 font-semibold" title="MetaForge"><span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary-600 text-sm text-white">M</span> `);
    if (!collapsed) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<span>MetaForge</span>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></a> `);
    if (onToggleCollapse) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<button type="button" class="hidden rounded-md p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 lg:block dark:hover:bg-neutral-800"${attr("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar")}>${escape_html(collapsed ? "»" : "«")}</button>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div> <div>`);
    if (!collapsed) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<p class="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">Modules</p>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <div class="flex flex-col gap-0.5"><!--[-->`);
    const each_array = ensure_array_like(modules);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let m = each_array[$$index];
      SidebarItem($$renderer2, {
        href: `/${m.name}`,
        label: m.label,
        active: isModuleActive(m.name),
        collapsed
      });
    }
    $$renderer2.push(`<!--]--> `);
    if (modules.length === 0 && !collapsed) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<p class="px-3 text-xs text-neutral-400">No modules yet</p>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div></div> `);
    if (auth.user?.is_admin) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="mt-auto">`);
      if (!collapsed) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<p class="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">Admin</p>`);
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--> `);
      SidebarItem($$renderer2, {
        href: "/admin/builder",
        label: "Builder",
        active: builderActive(),
        collapsed
      });
      $$renderer2.push(`<!----> `);
      SidebarItem($$renderer2, {
        href: "/admin/users",
        label: "Users & Roles",
        active: path().startsWith("/admin/users"),
        collapsed
      });
      $$renderer2.push(`<!----> `);
      SidebarItem($$renderer2, {
        href: "/admin/approvals",
        label: "Approvals",
        active: path().startsWith("/admin/approvals"),
        collapsed
      });
      $$renderer2.push(`<!----></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></nav>`);
  });
}
function Breadcrumbs($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const crumbs = derived(() => {
      const path = page.url.pathname;
      if (path.startsWith("/admin")) {
        return [
          { label: "Admin", href: "/admin/builder" },
          { label: "Builder", href: null }
        ];
      }
      const moduleName = page.params.module;
      if (!moduleName) return [];
      const data = page.data;
      const moduleLabel = data.module?.label ?? moduleName;
      const list = [{ label: moduleLabel, href: `/${moduleName}` }];
      if (page.params.id) {
        const recordLabel = page.params.id === "new" ? "New" : displayName(data.record);
        list.push({ label: recordLabel, href: null });
      }
      return list;
    });
    if (crumbs().length > 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<nav class="flex min-w-0 items-center gap-1.5 text-sm text-neutral-500" aria-label="Breadcrumb"><!--[-->`);
      const each_array = ensure_array_like(crumbs());
      for (let i = 0, $$length = each_array.length; i < $$length; i++) {
        let crumb = each_array[i];
        if (i > 0) {
          $$renderer2.push("<!--[0-->");
          $$renderer2.push(`<span class="shrink-0 text-neutral-300 dark:text-neutral-700">/</span>`);
        } else {
          $$renderer2.push("<!--[-1-->");
        }
        $$renderer2.push(`<!--]--> `);
        if (crumb.href) {
          $$renderer2.push("<!--[0-->");
          $$renderer2.push(`<a${attr("href", crumb.href)} class="shrink-0 hover:text-neutral-900 hover:underline dark:hover:text-neutral-100">${escape_html(crumb.label)}</a>`);
        } else {
          $$renderer2.push("<!--[-1-->");
          $$renderer2.push(`<span class="min-w-0 truncate font-medium text-neutral-900 dark:text-neutral-100">${escape_html(crumb.label)}</span>`);
        }
        $$renderer2.push(`<!--]-->`);
      }
      $$renderer2.push(`<!--]--></nav>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]-->`);
  });
}
function NotificationBell($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let notifications = [];
    let loaded = false;
    let open = false;
    async function onOpenChange(next) {
      open = next;
      if (next && !loaded) {
        try {
          notifications = await api.listNotifications();
          loaded = true;
        } catch (e) {
          toast.error(e instanceof Error ? e.message : "Failed to load notifications");
        }
      }
    }
    if (Menu) {
      $$renderer2.push("<!--[-->");
      Menu($$renderer2, {
        open,
        onOpenChange,
        children: ($$renderer3) => {
          if (Menu_trigger) {
            $$renderer3.push("<!--[-->");
            Menu_trigger($$renderer3, {
              class: "relative rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800",
              "aria-label": "Notifications",
              children: ($$renderer4) => {
                $$renderer4.push(`<!---->🔔 `);
                {
                  $$renderer4.push("<!--[-1-->");
                }
                $$renderer4.push(`<!--]-->`);
              },
              $$slots: { default: true }
            });
            $$renderer3.push("<!--]-->");
          } else {
            $$renderer3.push("<!--[!-->");
            $$renderer3.push("<!--]-->");
          }
          $$renderer3.push(` `);
          if (Portal) {
            $$renderer3.push("<!--[-->");
            Portal($$renderer3, {
              children: ($$renderer4) => {
                if (Dropdown_menu_content) {
                  $$renderer4.push("<!--[-->");
                  Dropdown_menu_content($$renderer4, {
                    class: "z-50 w-80 rounded-lg border border-neutral-200 bg-white p-1 shadow-xl dark:border-neutral-800 dark:bg-neutral-900",
                    align: "end",
                    sideOffset: 6,
                    children: ($$renderer5) => {
                      $$renderer5.push(`<div class="flex items-center justify-between px-2 py-1.5"><span class="text-sm font-semibold">Notifications</span> `);
                      {
                        $$renderer5.push("<!--[-1-->");
                      }
                      $$renderer5.push(`<!--]--></div> <div class="max-h-80 overflow-y-auto">`);
                      if (notifications.length === 0) {
                        $$renderer5.push("<!--[0-->");
                        $$renderer5.push(`<p class="px-2 py-6 text-center text-sm text-neutral-400">No notifications yet.</p>`);
                      } else {
                        $$renderer5.push("<!--[-1-->");
                        $$renderer5.push(`<!--[-->`);
                        const each_array = ensure_array_like(notifications);
                        for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
                          let n = each_array[$$index];
                          $$renderer5.push(`<button type="button"${attr_class(`block w-full rounded-md px-2 py-2 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800 ${n.read ? "" : "bg-primary-50/60 dark:bg-primary-950/40"}`)}><div class="flex items-center gap-1.5 font-medium">`);
                          if (!n.read) {
                            $$renderer5.push("<!--[0-->");
                            $$renderer5.push(`<span class="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-600"></span>`);
                          } else {
                            $$renderer5.push("<!--[-1-->");
                          }
                          $$renderer5.push(`<!--]--> ${escape_html(n.title)}</div> `);
                          if (n.body) {
                            $$renderer5.push("<!--[0-->");
                            $$renderer5.push(`<p class="mt-0.5 text-xs text-neutral-500">${escape_html(n.body)}</p>`);
                          } else {
                            $$renderer5.push("<!--[-1-->");
                          }
                          $$renderer5.push(`<!--]--> <p class="mt-0.5 text-xs text-neutral-400">${escape_html(new Date(n.created_at).toLocaleString())}</p></button>`);
                        }
                        $$renderer5.push(`<!--]-->`);
                      }
                      $$renderer5.push(`<!--]--></div>`);
                    },
                    $$slots: { default: true }
                  });
                  $$renderer4.push("<!--]-->");
                } else {
                  $$renderer4.push("<!--[!-->");
                  $$renderer4.push("<!--]-->");
                }
              }
            });
            $$renderer3.push("<!--]-->");
          } else {
            $$renderer3.push("<!--[!-->");
            $$renderer3.push("<!--]-->");
          }
        },
        $$slots: { default: true }
      });
      $$renderer2.push("<!--]-->");
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push("<!--]-->");
    }
  });
}
const THEMES = [
  { id: "bm", label: "BM (default)", swatch: "#714b67" },
  { id: "yellow", label: "Yellow", swatch: "#d97706" },
  { id: "blue", label: "Blue", swatch: "#2563eb" },
  { id: "orange", label: "Orange", swatch: "#c05f3f" },
  { id: "dark", label: "Dark", swatch: "#4f46e5" }
];
new Set(THEMES.map((t) => t.id));
const DEFAULT_THEME = "bm";
const themeState = { current: DEFAULT_THEME };
function ThemeSwitcher($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const current = derived(() => THEMES.find((t) => t.id === themeState.current) ?? THEMES[0]);
    if (Menu) {
      $$renderer2.push("<!--[-->");
      Menu($$renderer2, {
        children: ($$renderer3) => {
          if (Menu_trigger) {
            $$renderer3.push("<!--[-->");
            Menu_trigger($$renderer3, {
              class: "flex items-center gap-1.5 rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800",
              "aria-label": "Choose theme",
              title: `Theme: ${stringify(current().label)}`,
              children: ($$renderer4) => {
                $$renderer4.push(`<span class="h-4 w-4 shrink-0 rounded-full border border-black/10 dark:border-white/20"${attr_style("", { "background-color": current().swatch })}></span>`);
              },
              $$slots: { default: true }
            });
            $$renderer3.push("<!--]-->");
          } else {
            $$renderer3.push("<!--[!-->");
            $$renderer3.push("<!--]-->");
          }
          $$renderer3.push(` `);
          if (Portal) {
            $$renderer3.push("<!--[-->");
            Portal($$renderer3, {
              children: ($$renderer4) => {
                if (Dropdown_menu_content) {
                  $$renderer4.push("<!--[-->");
                  Dropdown_menu_content($$renderer4, {
                    class: "z-50 w-44 rounded-md border border-neutral-200 bg-white p-1 shadow-xl dark:border-neutral-800 dark:bg-neutral-900",
                    align: "end",
                    sideOffset: 6,
                    children: ($$renderer5) => {
                      $$renderer5.push(`<p class="px-2 py-1.5 text-xs font-semibold uppercase text-neutral-400">Theme</p> <!--[-->`);
                      const each_array = ensure_array_like(THEMES);
                      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
                        let t = each_array[$$index];
                        $$renderer5.push(`<button type="button"${attr_class(`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800 ${t.id === themeState.current ? "font-medium text-primary-700 dark:text-primary-300" : "text-neutral-700 dark:text-neutral-300"}`)}><span class="h-3.5 w-3.5 shrink-0 rounded-full border border-black/10 dark:border-white/20"${attr_style("", { "background-color": t.swatch })}></span> <span class="flex-1">${escape_html(t.label)}</span> `);
                        if (t.id === themeState.current) {
                          $$renderer5.push("<!--[0-->");
                          $$renderer5.push(`<span aria-hidden="true">✓</span>`);
                        } else {
                          $$renderer5.push("<!--[-1-->");
                        }
                        $$renderer5.push(`<!--]--></button>`);
                      }
                      $$renderer5.push(`<!--]-->`);
                    },
                    $$slots: { default: true }
                  });
                  $$renderer4.push("<!--]-->");
                } else {
                  $$renderer4.push("<!--[!-->");
                  $$renderer4.push("<!--]-->");
                }
              }
            });
            $$renderer3.push("<!--]-->");
          } else {
            $$renderer3.push("<!--[!-->");
            $$renderer3.push("<!--]-->");
          }
        },
        $$slots: { default: true }
      });
      $$renderer2.push("<!--]-->");
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push("<!--]-->");
    }
  });
}
function Topbar($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { onOpenMobileNav } = $$props;
    $$renderer2.push(`<header class="sticky top-0 z-10 flex h-12 items-center gap-2 border-b border-neutral-200 bg-white/80 px-3 backdrop-blur sm:gap-3 sm:px-4 dark:border-neutral-800 dark:bg-neutral-950/80">`);
    if (onOpenMobileNav) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<button type="button" class="shrink-0 rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 lg:hidden dark:hover:bg-neutral-800" aria-label="Open navigation">☰</button>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <div class="min-w-0 flex-1">`);
    Breadcrumbs($$renderer2);
    $$renderer2.push(`<!----></div> <div class="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-3">`);
    ThemeSwitcher($$renderer2);
    $$renderer2.push(`<!----> `);
    if (auth.user) {
      $$renderer2.push("<!--[0-->");
      NotificationBell($$renderer2);
      $$renderer2.push(`<!----> <span class="hidden text-sm text-neutral-600 sm:inline dark:text-neutral-400">${escape_html(auth.user.display_name)}</span> <button type="button" class="rounded-md px-2 py-1 text-sm text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 dark:hover:bg-neutral-800 dark:hover:text-neutral-100">Sign out</button>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div></header>`);
  });
}
function Toaster($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const POSITION_CLASSES = {
      "top-left": "top-4 left-4 items-start",
      "top-center": "top-4 left-1/2 -translate-x-1/2 items-center",
      "top-right": "top-4 right-4 items-end",
      "bottom-left": "bottom-4 left-4 items-start",
      "bottom-center": "bottom-4 left-1/2 -translate-x-1/2 items-center",
      "bottom-right": "bottom-4 right-4 items-end"
    };
    const KIND_CLASSES = {
      success: "border-green-200 bg-green-50 text-green-800 dark:border-green-900 dark:bg-green-950 dark:text-green-300",
      error: "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300",
      warning: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300",
      info: "border-primary-200 bg-primary-50 text-primary-800 dark:border-primary-900 dark:bg-primary-950 dark:text-primary-300"
    };
    const positionClass = derived(() => POSITION_CLASSES[localization.notification_position] ?? POSITION_CLASSES["bottom-center"]);
    const isTop = derived(() => localization.notification_position.startsWith("top"));
    $$renderer2.push(`<div${attr_class(`pointer-events-none fixed z-50 flex flex-col gap-2 ${stringify(positionClass())} ${isTop() ? "flex-col" : "flex-col-reverse"}`)} role="status" aria-live="polite"><!--[-->`);
    const each_array = ensure_array_like(toast.list());
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let t = each_array[$$index];
      $$renderer2.push(`<div${attr_class(`pointer-events-auto flex max-w-sm items-start gap-2 rounded-md border px-4 py-2.5 text-sm shadow-lg ${stringify(KIND_CLASSES[t.kind])}`)} role="alert"><span class="flex-1">${escape_html(t.message)}</span> <button type="button" class="ml-2 shrink-0 text-xs opacity-60 hover:opacity-100" aria-label="Dismiss">✕</button></div>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
function AppShell($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { modules, children } = $$props;
    let collapsed = false;
    let mobileOpen = false;
    function toggleCollapse() {
      collapsed = !collapsed;
      localStorage.setItem("mf:sidebar", collapsed ? "collapsed" : "expanded");
    }
    let $$settled = true;
    let $$inner_renderer;
    function $$render_inner($$renderer3) {
      $$renderer3.push(`<div class="flex h-screen bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100"><aside class="hidden shrink-0 border-r border-neutral-200 transition-[width] duration-150 lg:block dark:border-neutral-800"${attr_style("", { width: collapsed ? "4rem" : "15rem" })}>`);
      Sidebar($$renderer3, { modules, collapsed, onToggleCollapse: toggleCollapse });
      $$renderer3.push(`<!----></aside> `);
      if (Dialog) {
        $$renderer3.push("<!--[-->");
        Dialog($$renderer3, {
          get open() {
            return mobileOpen;
          },
          set open($$value) {
            mobileOpen = $$value;
            $$settled = false;
          },
          children: ($$renderer4) => {
            if (Portal) {
              $$renderer4.push("<!--[-->");
              Portal($$renderer4, {
                children: ($$renderer5) => {
                  if (Dialog_overlay) {
                    $$renderer5.push("<!--[-->");
                    Dialog_overlay($$renderer5, { class: "fixed inset-0 z-40 bg-black/40 lg:hidden" });
                    $$renderer5.push("<!--]-->");
                  } else {
                    $$renderer5.push("<!--[!-->");
                    $$renderer5.push("<!--]-->");
                  }
                  $$renderer5.push(` `);
                  if (Dialog_content) {
                    $$renderer5.push("<!--[-->");
                    Dialog_content($$renderer5, {
                      class: "fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-xl lg:hidden dark:bg-neutral-950",
                      children: ($$renderer6) => {
                        Sidebar($$renderer6, { modules });
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
      $$renderer3.push(` <div class="flex min-w-0 flex-1 flex-col">`);
      Topbar($$renderer3, { onOpenMobileNav: () => mobileOpen = true });
      $$renderer3.push(`<!----> <main class="min-w-0 flex-1 overflow-y-auto">`);
      children($$renderer3);
      $$renderer3.push(`<!----></main></div> `);
      Toaster($$renderer3);
      $$renderer3.push(`<!----></div>`);
    }
    do {
      $$settled = true;
      $$inner_renderer = $$renderer2.copy();
      $$render_inner($$inner_renderer);
    } while (!$$settled);
    $$renderer2.subsume($$inner_renderer);
  });
}
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data, children } = $$props;
    if (
      // Reconciles the fast localStorage-cached theme (applied synchronously
      // in app.html, before this component even mounts) with the server's
      // per-user value once it's known — authoritative on a new device, or
      // after the user changed their theme somewhere else. A no-op re-write
      // when they already match.
      page.url.pathname === "/login"
    ) {
      $$renderer2.push("<!--[0-->");
      children($$renderer2);
      $$renderer2.push(`<!---->`);
    } else {
      $$renderer2.push("<!--[-1-->");
      AppShell($$renderer2, {
        modules: data.modules,
        children: ($$renderer3) => {
          children($$renderer3);
          $$renderer3.push(`<!---->`);
        }
      });
    }
    $$renderer2.push(`<!--]-->`);
  });
}
export {
  _layout as default
};
