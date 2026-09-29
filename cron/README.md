# Cron de Hedy

`hedy-diario-post.prompt.txt` es el prompt del cron `hedy-diario-post` de Hermes (copia versionada).

El cron usa el arnés `scripts/hedy-post.py`: el modelo solo investiga y escribe; el script hace git, `content-plan.md`, la revisión automática (`check`), el PR y los correos. El cron solo tiene las herramientas `terminal`, `file` y `web`.

Si se pierde la configuración de Hermes, se recrea así (dentro del contenedor, como `hermes`, desde el repo):

```bash
hermes cron create "41 11 2-31/2 * *" "$(cat cron/hedy-diario-post.prompt.txt)" \
  --name hedy-diario-post --deliver local --workdir /apps-hermes/hedy-diario \
  --model qwen3.5-9b-64k --provider custom --reasoning-effort high
# limitar herramientas (usa el id que imprime el comando anterior)
cd /opt/hermes && .venv/bin/python3 -c "from cron.jobs import update_job; print(update_job('ID', {'enabled_toolsets': ['terminal', 'file', 'web']})['enabled_toolsets'])"
```

Probar sin efectos (sin correos, ramas ni PR): `python3 scripts/hedy-post.py start --dry-run`.

Si cambias el prompt en Hermes, actualiza también este archivo por PR.

## Personalidad de Hedy en el chat

`SOUL.md` es la identidad que Hermes carga en cada sesión (copia versionada de `/opt/data/SOUL.md`).
En el servidor es inmutable (`chattr +i`); para cambiarla hay que quitar esa protección desde el host.
