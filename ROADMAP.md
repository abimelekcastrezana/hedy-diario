# Roadmap — Hedy Blog

Meta: que Hedy Blog sea una fuente de ingresos (afiliados, newsletter y anuncios) sin
sacrificar la confianza del lector. Las reglas editoriales están en `EDITORIAL_POLICY.md`.

Cada fase arranca cuando se cumple su meta, no en una fecha fija. Al terminar una tarea se
marca `[x]` con la fecha y se anota en la bitácora de abajo, en el mismo commit.

**Estado actual:** Fase 0 (sin empezar) · 6 posts publicados · cron publica directo en `main`.

---

## ✅ Hecho

- [x] Dominio propio `hedy.blog` en GitHub Pages (2026-09-24)
- [x] Posts en la raíz: `hedy.blog/<fecha-slug>/` (2026-09-24)
- [x] Redirecciones de las URLs viejas `/hedy-diario/…` y `/blog/…` (2026-09-24)
- [x] Título "Hedy Blog", descripción e intro de la portada (2026-09-24)
- [x] URL y asunto del correo de Hedy actualizados en el cron (2026-09-24)
- [x] Política editorial escrita y aprobada (`EDITORIAL_POLICY.md`) (2026-09-26)

## Fase 0 — Ordenar la casa

**Meta:** ningún post se publica sin revisión, y el pipeline es seguro.

- [ ] Revocar el token de GitHub expuesto en el remote del repo y reemplazarlo
      (credential helper o token nuevo con permisos mínimos)
- [ ] Activar **Enforce HTTPS** en Settings → Pages
- [ ] Quitar el workflow `.github/workflows/auto-merge-post.yml`
- [ ] Proteger `main` en GitHub: exigir PR y no permitir saltarse la regla
- [ ] Verificar que Hedy puede abrir y listar PRs desde el contenedor (`gh` CLI o API)
- [ ] Reescribir el prompt del cron `hedy-diario-post`:
      rama `post/*`, PR, revisión de PR pendiente, correos de revisión, recordatorio y fallo
- [ ] Referenciar `EDITORIAL_POLICY.md` desde `AGENTS.md` y el prompt del cron;
      quitar la nota de "pendiente de implementar" de la política
- [ ] Corrida de prueba completa con el cron de prueba (sin publicar)
- [ ] Corregir vía PR el post de **Pomodoro** (partes escritas como si fuera Cirillo, sin fuentes)
- [ ] Corregir vía PR el post de **mente de principiante** (frases rotas, detalles internos)
- [ ] Analítica sin cookies (GoatCounter o Cloudflare Web Analytics)
- [ ] Dar de alta el sitio en Google Search Console y enviar el sitemap

## Fase 1 — Base para monetizar

**Meta:** el sitio se ve como un blog serio y cada post invita a volver.

- [ ] Página **Acerca de** (Hedy es una IA; un humano revisa cada post)
- [ ] Página **Privacidad**
- [ ] Página **Contacto**
- [ ] Página **Aviso de afiliados**
- [ ] Bloque de suscripción al final de cada post, en el layout (por ahora apunta al RSS)
- [ ] Decidir plataforma de newsletter (Buttondown / Beehiiv / Resend) y conectarla
- [ ] Imágenes de vista previa (og:image) propias por post
- [ ] Pilares visibles en el sitio (etiquetas o secciones)
- [ ] `content-plan.md` con al menos 10 temas pendientes dentro de los pilares,
      priorizando lo que la gente busca

## Fase 2 — Afiliados

**Meta para empezar:** ~15–20 posts buenos publicados.

- [ ] Registrarse en Amazon Afiliados México (libros relacionados con los posts)
- [ ] Elegir 2–3 programas de apps de productividad o notas
- [ ] Crear `src/data/afiliados.json` (catálogo aprobado)
- [ ] Componente de enlace de afiliado: `rel="sponsored nofollow"` y aviso automático
- [ ] Agregar afiliados, solo donde vienen al caso, a los posts existentes que encajen (vía PR)

## Fase 3 — Anuncios

**Meta para empezar:** ~25–30 posts buenos y algunos meses de tráfico medido.

- [ ] Revisar requisitos vigentes de AdSense
- [ ] Banner de consentimiento de cookies (certificado por Google, para visitantes de Europa/UK)
- [ ] `ads.txt` en la raíz del sitio
- [ ] Aplicar a AdSense
- [ ] Definir ubicación de anuncios sin arruinar la lectura
- [ ] Evaluar otras redes cuando el tráfico lo permita

## Fase 4 — Crecer

- [ ] Patrocinios en la newsletter
- [ ] Series a partir de los posts con más tráfico
- [ ] Revisar métricas cada mes: visitas, suscriptores, clics de afiliado, ingresos

---

## Decisiones pendientes

- Plataforma de newsletter
- Red de anuncios y cuándo aplicar
- Programas de afiliado iniciales

## Bitácora

- **2026-09-24** — Dominio `hedy.blog`, rutas en la raíz, redirecciones, título y descripción.
- **2026-09-26** — Política editorial y este roadmap agregados al repo.
