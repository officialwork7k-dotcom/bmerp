import { h as bind_props, p as props_id, g as attributes, d as derived, j as spread_props, e as escape_html } from "./index2.js";
import { n as noop, d as DialogRootState, b as boxWith, c as createId, a8 as DialogActionState, m as mergeProps, a9 as AlertDialogCancelState, e as DialogContentState, F as Focus_scope, aa as afterSleep, E as Escape_layer, f as Dismissible_layer, T as Text_selection_layer, S as Scroll_lock, P as Portal, D as Dialog_overlay } from "./dialog-overlay.js";
import { D as Dialog_title, a as Dialog_description } from "./dialog-description.js";
function Alert_dialog($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let {
      open = false,
      onOpenChange = noop,
      onOpenChangeComplete = noop,
      children
    } = $$props;
    DialogRootState.create({
      variant: boxWith(() => "alert-dialog"),
      open: boxWith(() => open, (v) => {
        open = v;
        onOpenChange(v);
      }),
      onOpenChangeComplete: boxWith(() => onOpenChangeComplete)
    });
    children?.($$renderer2);
    $$renderer2.push(`<!---->`);
    bind_props($$props, { open });
  });
}
function Alert_dialog_action($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const uid = props_id($$renderer2);
    let {
      children,
      child,
      id = createId(uid),
      ref = null,
      $$slots,
      $$events,
      ...restProps
    } = $$props;
    const actionState = DialogActionState.create({
      id: boxWith(() => id),
      ref: boxWith(() => ref, (v) => ref = v)
    });
    const mergedProps = derived(() => mergeProps(restProps, actionState.props));
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
function Alert_dialog_cancel($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const uid = props_id($$renderer2);
    let {
      id = createId(uid),
      ref = null,
      children,
      child,
      disabled = false,
      $$slots,
      $$events,
      ...restProps
    } = $$props;
    const cancelState = AlertDialogCancelState.create({
      id: boxWith(() => id),
      ref: boxWith(() => ref, (v) => ref = v),
      disabled: boxWith(() => Boolean(disabled))
    });
    const mergedProps = derived(() => mergeProps(restProps, cancelState.props));
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
function Alert_dialog_content($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const uid = props_id($$renderer2);
    let {
      id = createId(uid),
      children,
      child,
      ref = null,
      forceMount = false,
      interactOutsideBehavior = "ignore",
      onCloseAutoFocus = noop,
      onEscapeKeydown = noop,
      onOpenAutoFocus = noop,
      onInteractOutside = noop,
      preventScroll = true,
      trapFocus = true,
      restoreScrollDelay = null,
      $$slots,
      $$events,
      ...restProps
    } = $$props;
    const contentState = DialogContentState.create({
      id: boxWith(() => id),
      ref: boxWith(() => ref, (v) => ref = v)
    });
    const mergedProps = derived(() => mergeProps(restProps, contentState.props));
    if (contentState.shouldRender || forceMount) {
      $$renderer2.push("<!--[0-->");
      {
        let focusScope = function($$renderer3, { props: focusScopeProps }) {
          Escape_layer($$renderer3, spread_props([
            mergedProps(),
            {
              enabled: contentState.root.opts.open.current,
              ref: contentState.opts.ref,
              onEscapeKeydown: (e) => {
                onEscapeKeydown(e);
                if (e.defaultPrevented) return;
                contentState.root.handleClose();
              },
              children: ($$renderer4) => {
                Dismissible_layer($$renderer4, spread_props([
                  mergedProps(),
                  {
                    ref: contentState.opts.ref,
                    enabled: contentState.root.opts.open.current,
                    interactOutsideBehavior,
                    onInteractOutside: (e) => {
                      onInteractOutside(e);
                      if (e.defaultPrevented) return;
                      contentState.root.handleClose();
                    },
                    children: ($$renderer5) => {
                      Text_selection_layer($$renderer5, spread_props([
                        mergedProps(),
                        {
                          ref: contentState.opts.ref,
                          enabled: contentState.root.opts.open.current,
                          children: ($$renderer6) => {
                            if (child) {
                              $$renderer6.push("<!--[0-->");
                              if (contentState.root.opts.open.current) {
                                $$renderer6.push("<!--[0-->");
                                Scroll_lock($$renderer6, { preventScroll, restoreScrollDelay });
                              } else {
                                $$renderer6.push("<!--[-1-->");
                              }
                              $$renderer6.push(`<!--]--> `);
                              child($$renderer6, {
                                props: mergeProps(mergedProps(), focusScopeProps),
                                ...contentState.snippetProps
                              });
                              $$renderer6.push(`<!---->`);
                            } else {
                              $$renderer6.push("<!--[-1-->");
                              Scroll_lock($$renderer6, { preventScroll });
                              $$renderer6.push(`<!----> <div${attributes({ ...mergeProps(mergedProps(), focusScopeProps) })}>`);
                              children?.($$renderer6);
                              $$renderer6.push(`<!----></div>`);
                            }
                            $$renderer6.push(`<!--]-->`);
                          },
                          $$slots: { default: true }
                        }
                      ]));
                    },
                    $$slots: { default: true }
                  }
                ]));
              },
              $$slots: { default: true }
            }
          ]));
        };
        Focus_scope($$renderer2, {
          ref: contentState.opts.ref,
          loop: true,
          trapFocus,
          enabled: contentState.root.opts.open.current,
          onCloseAutoFocus,
          onOpenAutoFocus: (e) => {
            onOpenAutoFocus(e);
            if (e.defaultPrevented) return;
            e.preventDefault();
            afterSleep(0, () => contentState.opts.ref.current?.focus());
          },
          focusScope
        });
      }
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]-->`);
    bind_props($$props, { ref });
  });
}
function ConfirmDialog($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let {
      open = false,
      title,
      description,
      confirmLabel = "Confirm",
      danger = false,
      onConfirm
    } = $$props;
    let $$settled = true;
    let $$inner_renderer;
    function $$render_inner($$renderer3) {
      if (Alert_dialog) {
        $$renderer3.push("<!--[-->");
        Alert_dialog($$renderer3, {
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
                  if (Alert_dialog_content) {
                    $$renderer5.push("<!--[-->");
                    Alert_dialog_content($$renderer5, {
                      class: "fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-lg border border-neutral-200 bg-white p-5 shadow-xl dark:border-neutral-800 dark:bg-neutral-900",
                      children: ($$renderer6) => {
                        if (Dialog_title) {
                          $$renderer6.push("<!--[-->");
                          Dialog_title($$renderer6, {
                            class: "text-base font-semibold",
                            children: ($$renderer7) => {
                              $$renderer7.push(`<!---->${escape_html(title)}`);
                            },
                            $$slots: { default: true }
                          });
                          $$renderer6.push("<!--]-->");
                        } else {
                          $$renderer6.push("<!--[!-->");
                          $$renderer6.push("<!--]-->");
                        }
                        $$renderer6.push(` `);
                        if (description) {
                          $$renderer6.push("<!--[0-->");
                          if (Dialog_description) {
                            $$renderer6.push("<!--[-->");
                            Dialog_description($$renderer6, {
                              class: "mt-1.5 text-sm text-neutral-500",
                              children: ($$renderer7) => {
                                $$renderer7.push(`<!---->${escape_html(description)}`);
                              },
                              $$slots: { default: true }
                            });
                            $$renderer6.push("<!--]-->");
                          } else {
                            $$renderer6.push("<!--[!-->");
                            $$renderer6.push("<!--]-->");
                          }
                        } else {
                          $$renderer6.push("<!--[-1-->");
                        }
                        $$renderer6.push(`<!--]--> <div class="mt-5 flex justify-end gap-2">`);
                        if (Alert_dialog_cancel) {
                          $$renderer6.push("<!--[-->");
                          Alert_dialog_cancel($$renderer6, {
                            class: "rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800",
                            children: ($$renderer7) => {
                              $$renderer7.push(`<!---->Cancel`);
                            },
                            $$slots: { default: true }
                          });
                          $$renderer6.push("<!--]-->");
                        } else {
                          $$renderer6.push("<!--[!-->");
                          $$renderer6.push("<!--]-->");
                        }
                        $$renderer6.push(` `);
                        if (Alert_dialog_action) {
                          $$renderer6.push("<!--[-->");
                          Alert_dialog_action($$renderer6, {
                            onclick: onConfirm,
                            class: `rounded-md px-3 py-1.5 text-sm font-medium text-white ${danger ? "bg-red-600 hover:bg-red-700" : "bg-primary-600 hover:bg-primary-700"}`,
                            children: ($$renderer7) => {
                              $$renderer7.push(`<!---->${escape_html(confirmLabel)}`);
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
export {
  ConfirmDialog as C
};
