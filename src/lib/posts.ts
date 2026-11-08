import { getCollection } from 'astro:content';
import pilares from '../data/pilares.json';
import { PILARES } from './grafo';

// Primer párrafo del post, sin Markdown, para el extracto de la home (como el "[More]" de nav.al).
function extracto(body: string, max = 230) {
	const bloque = body
		.split(/\n\s*\n/)
		.map((b) => b.trim())
		.find((b) => b && !/^(#|>|-|\*|\d+\.|!|\||```|<)/.test(b));
	if (!bloque) return '';
	const limpio = bloque
		.replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
		.replace(/[*_`]/g, '')
		.replace(/\s+/g, ' ')
		.trim();
	if (limpio.length <= max) return limpio;
	return limpio.slice(0, max).replace(/\s+\S*$/, '') + '…';
}

export type PostResumen = {
	id: string;
	url: string;
	title: string;
	description: string;
	pubDate: Date;
	pilar: string;
	pilarNombre: string;
	pilarColor: string;
	minutos: number;
	extracto: string;
};

export async function getPosts(): Promise<PostResumen[]> {
	const posts = await getCollection('blog');
	return posts
		.sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf())
		.map((p) => {
			const clave = (pilares as Record<string, string>)[p.id];
			const pilar = clave && clave in PILARES ? clave : 'sin';
			const palabras = (p.body ?? '').split(/\s+/).filter(Boolean).length;
			return {
				id: p.id,
				url: `/${p.id}/`,
				title: p.data.title,
				description: p.data.description,
				pubDate: p.data.pubDate,
				pilar,
				pilarNombre: PILARES[pilar].nombre,
				pilarColor: PILARES[pilar].color,
				minutos: Math.max(1, Math.round(palabras / 200)),
				extracto: extracto(p.body ?? ''),
			};
		});
}
