import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import fs from 'fs';
import path from 'path';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: '0.0.0.0', // Listen on all network interfaces
		port: 5197,
		strictPort: true, // Fail if port is already in use
		https: {
			key: fs.readFileSync(path.resolve(__dirname, 'key.pem')),
			cert: fs.readFileSync(path.resolve(__dirname, 'cert.pem'))
		},
		proxy: {
			'/api': {
				target: 'http://192.168.1.14:8080',
				changeOrigin: true,
				secure: false
			}
		}
	}
});
