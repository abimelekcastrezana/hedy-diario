import { getCollection } from 'astro:content';
import pilares from '../data/pilares.json';

// Pilares de EDITORIAL_POLICY.md sección 6. Colores de la paleta Okabe-Ito (distinguibles con daltonismo).
export const PILARES: Record<string, { nombre: string; color: string }> = {
	foco: { nombre: 'Foco y productividad', color: '#0072B2' },
	aprender: { nombre: 'Aprender y pensar', color: '#D55E00' },
	escribir: { nombre: 'Escribir y crear en internet', color: '#009E73' },
	tech: { nombre: 'Cultura tech con alma', color: '#CC79A7' },
	sin: { nombre: 'Sin clasificar', color: '#8a8f98' },
};

export type NodoGrafo = { id: string; title: string; url: string; pilar: string; grado: number; r: number };
export type EnlaceGrafo = { source: string; target: string };

// Un enlace es un link interno `/<id-de-otro-post>/` dentro del cuerpo de un post.
export async function getGrafo() {
	const posts = await getCollection('blog');
	const ids = new Set(posts.map((p) => p.id));
	const vistos = new Set<string>();
	const enlaces: EnlaceGrafo[] = [];
	for (const p of posts) {
		for (const m of (p.body ?? '').matchAll(/\]\(\/([^)\s/#]+)\/?\)|href="\/([^"\s/#]+)\/?"/g)) {
			const target = m[1] ?? m[2];
			const clave = `${p.id}>${target}`;
			if (ids.has(target) && target !== p.id && !vistos.has(clave)) {
				vistos.add(clave);
				enlaces.push({ source: p.id, target });
			}
		}
	}
	const grado = (id: string) => enlaces.filter((e) => e.source === id || e.target === id).length;
	const nodos: NodoGrafo[] = posts
		.sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf())
		.map((p) => {
			const g = grado(p.id);
			const pilar = (pilares as Record<string, string>)[p.id];
			return {
				id: p.id,
				title: p.data.title,
				url: `/${p.id}/`,
				pilar: pilar && pilar in PILARES ? pilar : 'sin',
				grado: g,
				r: Math.min(7 + g * 2.5, 18),
			};
		});
	const titulo = new Map(nodos.map((n) => [n.id, n.title]));
	const mencionadoEn = (id: string) =>
		enlaces.filter((e) => e.target === id).map((e) => ({ id: e.source, title: titulo.get(e.source) ?? e.source }));
	return { nodos, enlaces, mencionadoEn };
}
