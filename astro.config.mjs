// @ts-check

import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import { defineConfig, fontProviders } from 'astro/config';

// https://astro.build/config
export default defineConfig({
	site: 'https://hedy.blog',
	integrations: [mdx(), sitemap({ filter: (page) => !page.includes('/hedy-diario/') && !page.includes('/blog/') })],
	fonts: [
		{
			provider: fontProviders.local(),
			name: 'Fraunces',
			cssVariable: '--font-fraunces',
			fallbacks: ['Georgia', 'serif'],
			options: {
				variants: [
					{
						src: ['./src/assets/fonts/fraunces-var.woff2'],
						weight: '300 800',
						style: 'normal',
						display: 'swap',
					},
				],
			},
		},
		{
			provider: fontProviders.local(),
			name: 'Inter',
			cssVariable: '--font-inter',
			fallbacks: ['system-ui', 'sans-serif'],
			options: {
				variants: [
					{
						src: ['./src/assets/fonts/inter-var.woff2'],
						weight: '400 700',
						style: 'normal',
						display: 'swap',
					},
				],
			},
		},
	],
});
