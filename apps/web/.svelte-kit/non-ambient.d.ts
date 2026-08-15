
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	type MatcherParam<M> = M extends (param : string) => param is (infer U extends string) ? U : string;

	export interface AppTypes {
		RouteId(): "/" | "/admin" | "/admin/ai-settings" | "/admin/approvals" | "/admin/builder" | "/admin/tokens" | "/admin/users" | "/admin/webhooks" | "/api" | "/api/[...path]" | "/dashboard" | "/login" | "/period-close" | "/reports" | "/[module]" | "/[module]/[id]";
		RouteParams(): {
			"/api/[...path]": { path: string };
			"/[module]": { module: string };
			"/[module]/[id]": { module: string; id: string }
		};
		LayoutParams(): {
			"/": { path?: string | undefined; module?: string | undefined; id?: string | undefined };
			"/admin": Record<string, never>;
			"/admin/ai-settings": Record<string, never>;
			"/admin/approvals": Record<string, never>;
			"/admin/builder": Record<string, never>;
			"/admin/tokens": Record<string, never>;
			"/admin/users": Record<string, never>;
			"/admin/webhooks": Record<string, never>;
			"/api": { path?: string | undefined };
			"/api/[...path]": { path: string };
			"/dashboard": Record<string, never>;
			"/login": Record<string, never>;
			"/period-close": Record<string, never>;
			"/reports": Record<string, never>;
			"/[module]": { module: string; id?: string | undefined };
			"/[module]/[id]": { module: string; id: string }
		};
		Pathname(): "/" | "/admin/ai-settings" | "/admin/approvals" | "/admin/builder" | "/admin/tokens" | "/admin/users" | "/admin/webhooks" | `/api/${string}` & {} | "/dashboard" | "/login" | "/period-close" | "/reports" | `/${string}` & {} | `/${string}/${string}` & {};
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): string & {};
	}
}