import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		// Vite rejects requests whose Host header it doesn't recognize (DNS
		// rebinding protection) — an ngrok tunnel forwards the real request
		// Host as the public *.ngrok-free.app/.dev subdomain, which changes
		// every time the tunnel restarts on the free tier, so a leading-dot
		// wildcard covers any of them rather than needing to update this
		// file each time. Only relevant when proxying the local dev server
		// through a tunnel (e.g. for Telegram's public_base_url) — see
		// AI Assistant settings' "Public Base URL" field.
		allowedHosts: ['.ngrok-free.app', '.ngrok-free.dev', '.ngrok.io'],
		// Pre-transforms the engine components dev-server-side instead of
		// waiting for the browser to request each one on first navigation —
		// the actual cause of "creating new takes too long": Vite dev mode
		// serves every component/dependency as a separate unbundled ES
		// module over HTTP (no bundling in dev), so a route that touches
		// many files pays for all of them on first visit. Warmup doesn't
		// remove those requests, just gets a head start on them. The real
		// fix is running the production build (`npm run build && node
		// build`) for actual use — dev mode's per-module request model is
		// inherent to Vite, not something warmup fully solves.
		warmup: {
			clientFiles: [
				'./src/lib/components/engine/DetailPage.svelte',
				'./src/lib/components/engine/DataForm.svelte',
				'./src/lib/components/engine/FieldControl.svelte',
				'./src/lib/components/engine/ListPage.svelte',
				'./src/lib/components/engine/DataTable.svelte',
				'./src/lib/api.ts',
				'./src/lib/validation.ts',
				'./src/lib/formula.ts'
			]
		}
	}
});
