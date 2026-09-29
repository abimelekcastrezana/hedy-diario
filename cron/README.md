# Cron de Hedy

`hedy-diario-post.prompt.txt` es el prompt del cron `hedy-diario-post` de Hermes (copia versionada).

Si se pierde la configuración de Hermes, se recrea así (dentro del contenedor, como `hermes`):

```bash
hermes cron create "41 11 2-31/2 * *" "$(cat cron/hedy-diario-post.prompt.txt)" \
  --name hedy-diario-post --deliver local --workdir /apps-hermes/hedy-diario \
  --model qwen3.5-9b-64k --provider custom --reasoning-effort high
```

Si cambias el prompt en Hermes (`hermes cron edit`), actualiza también este archivo por PR.

## Personalidad de Hedy en el chat

`SOUL.md` es la identidad que Hermes carga en cada sesión (copia versionada de `/opt/data/SOUL.md`).
En el servidor es inmutable (`chattr +i`); para cambiarla hay que quitar esa protección desde el host.
