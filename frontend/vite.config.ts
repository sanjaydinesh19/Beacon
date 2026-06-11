import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		allowedHosts: ['beacon', 'omen.taildd3099.ts.net'],
		proxy: {
			'/api': 'http://localhost:8000'
		}
	}
});
