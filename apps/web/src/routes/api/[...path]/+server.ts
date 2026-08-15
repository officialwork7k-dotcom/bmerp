import type { RequestHandler } from './$types';

// Proxies /api/* to the FastAPI backend. Replaces the old vite.config.ts
// `server.proxy` entry, which only intercepted real HTTP requests hitting
// the Vite dev server — it never applied to `node build`'s production
// server (no dev server there at all) and never applied to SvelteKit's own
// in-process SSR `fetch` either (relative URLs during SSR resolve against
// SvelteKit's route tree directly, bypassing any HTTP-layer proxy). A real
// server route works identically in `vite dev` and `node build`.
const API_BASE = process.env.API_BASE_URL ?? 'http://localhost:8000';

const proxy: RequestHandler = async ({ request, params, url }) => {
	const target = `${API_BASE}/api/${params.path}${url.search}`;
	const headers = new Headers(request.headers);
	headers.delete('host');

	const response = await fetch(target, {
		method: request.method,
		headers,
		body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer(),
		// @ts-expect-error - Node fetch requires this for streaming bodies
		duplex: 'half'
	});

	const responseHeaders = new Headers(response.headers);
	responseHeaders.delete('content-encoding');
	responseHeaders.delete('content-length');
	return new Response(response.body, { status: response.status, headers: responseHeaders });
};

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
