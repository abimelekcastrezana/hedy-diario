#!/usr/bin/env python3
"""Harness for Hedy's blog cron: the agent researches and writes, this script does the rest.

Usage (from the repo root):
  python3 scripts/hedy-post.py start [--dry-run]
      Syncs main, checks for a pending draft PR, picks the next topic from content-plan.md
      and prints the exact file name, date and template the agent must write.
  python3 scripts/hedy-post.py check <archivo.md>
      Validates a draft (structure, length, sources that really exist, forbidden phrases,
      repeated sentences). Prints what to fix; exit code 0 only when it passes.
  python3 scripts/hedy-post.py finish <archivo.md> [--dry-run]
      Only if check passes: updates content-plan.md, builds, creates the post/* branch,
      commits, pushes, opens the PR and emails the review link. Never touches main.
  python3 scripts/hedy-post.py abort "<motivo>"
      Moves an unfinished draft out of the repo, returns to main and emails the reason.

See EDITORIAL_POLICY.md (sections 2-8) for the rules these checks enforce.
"""

import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / ".git" / "hedy-post.json"
PLAN = REPO / "content-plan.md"
BLOG_DIR = "src/content/blog"
FAILED_DIR = Path("/apps-hermes/borradores-fallidos")
BASHRC = Path("/opt/data/.bashrc")
OWNER_EMAIL = "abimelekcastrezana@gmail.com"
FROM_EMAIL = "hedy@tiendatap.com"
SITE = "https://hedy.blog"
MIN_WORDS, MAX_WORDS = 650, 1200  # body only (no front-matter, no Fuentes); outside -> warning
HARD_MIN_WORDS, HARD_MAX_WORDS = 400, 1600  # outside -> error
MIN_SOURCES = 2  # verified (200) sources wanted; fewer than 1 is an error
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
NAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
SIGNATURE_RE = re.compile(r"^Un abrazo desde la GPU[.!]?$")
URL_RE = re.compile(r"https?://[^\s)>\]\"'`]+")
# (pattern, reason, blocking): blocking=False only warns in the PR.
FORBIDDEN = [
    (r"ciudad de m[eé]xico|\bcdmx\b|desde m[eé]xico",
     "Menciona una ubicación física. Tú no tienes ciudad: quítala.", True),
    (r"\bheredoc\b|\bnano\b|\bcron\b|\bslug\b|el usuario|mis instrucciones|\bmi prompt\b",
     "Menciona detalles internos (cron, heredoc, nano, slug, 'el usuario', instrucciones). Quítalos.", True),
    (r"nosotr[oa]s somos (m[aá]s )?eficientes|como agentes de ia,? nosotr[oa]s|las ia somos",
     "Afirma que las IA son superiores o eficientes por naturaleza. Mejor habla solo de tu experiencia.", False),
    (r"amazon\.|amzn\.to|[?&]tag=",
     "Tiene un enlace de afiliado. Todavía no hay catálogo aprobado: quítalo.", True),
]


class Fail(Exception):
    pass


def redact(text):
    return re.sub(r"https://[^@\s/]+@", "https://***@", text)


def run(cmd, check=True):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise Fail(f"`{' '.join(cmd)}` falló: {redact((r.stderr or r.stdout).strip())[-800:]}")
    return r


def git(*args, check=True):
    return run(["git", *args], check=check).stdout.strip()


def pr_helper():
    spec = importlib.util.spec_from_file_location("hedy_pr", REPO / "scripts" / "hedy-pr.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resend_key():
    key = os.environ.get("RESEND_API_KEY", "")
    if not key and BASHRC.exists():
        m = re.search(r"^export RESEND_API_KEY=(\S+)", BASHRC.read_text(), re.M)
        key = m.group(1).strip("'\"") if m else ""
    if not key:
        raise Fail("no encontré RESEND_API_KEY (ni en el entorno ni en /opt/data/.bashrc)")
    return key


def send_email(subject, text, dry_run=False):
    if dry_run:
        print(f"(dry-run) correo NO enviado: {subject}")
        return
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        method="POST",
        data=json.dumps({"from": FROM_EMAIL, "to": [OWNER_EMAIL], "subject": subject, "text": text}).encode(),
        headers={"Authorization": f"Bearer {resend_key()}", "Content-Type": "application/json",
                 "User-Agent": "hedy-post/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"EMAIL_ID={json.load(resp).get('id')}  ({subject})")
    except urllib.error.HTTPError as e:
        raise Fail(f"Resend respondió {e.code}: {e.read().decode(errors='replace')[:300]}")


def pub_date(day):
    return f"{DAYS[day.weekday()]} {day.day} {MONTHS[day.month - 1]} {day.year}"


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", text)
    slug = ""
    for w in words:
        if len(slug) + len(w) + 1 > 60:
            break
        slug = f"{slug}-{w}" if slug else w
    return slug


# --- content-plan.md -------------------------------------------------------------------------

def plan_sections(text):
    """Returns (pending_start, pending_end, published_end) line indexes of the two lists."""
    lines = text.split("\n")
    try:
        p = next(i for i, l in enumerate(lines) if l.strip() == "## Pendientes")
        q = next(i for i, l in enumerate(lines) if l.strip() == "## Publicados")
    except StopIteration:
        raise Fail("content-plan.md no tiene las secciones '## Pendientes' y '## Publicados'")
    end = next((i for i in range(q + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines, p, q, end


ITEM_RE = re.compile(r"^\s*\d+\.\s+(\S.*)$")


def pending_topics(text):
    lines, p, q, _ = plan_sections(text)
    return [m.group(1).strip() for l in lines[p + 1:q] if (m := ITEM_RE.match(l))]


def topic_title(topic):
    return topic.split(":", 1)[0].strip()


def move_topic_to_published(text, topic):
    lines, p, q, end = plan_sections(text)
    pending = [t for t in pending_topics(text)]
    if topic not in pending:
        raise Fail("el tema ya no está en '## Pendientes' de content-plan.md")
    pending.remove(topic)
    published = [m.group(1).strip() for l in lines[q + 1:end] if (m := ITEM_RE.match(l))]
    published.append(topic_title(topic))
    new = (lines[:p + 1] + [""] + [f"{i}. {t}" for i, t in enumerate(pending, 1)] + [""]
           + [lines[q]] + [f"{i}. {t}" for i, t in enumerate(published, 1)] + [""] + lines[end:])
    return "\n".join(new).rstrip("\n") + "\n"


# --- check -----------------------------------------------------------------------------------

def url_status(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Accept-Language": "es,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def check_post(rel_path):
    """Returns (errors, warnings) for a draft."""
    errors, warnings = [], []
    path = (REPO / rel_path).resolve()
    name = path.name
    if path.parent != (REPO / BLOG_DIR).resolve():
        errors.append(f"El archivo debe estar en {BLOG_DIR}/")
    m = NAME_RE.match(name)
    if not m:
        errors.append(f"El nombre '{name}' debe ser AAAA-MM-DD-palabras-con-guiones.md (sin acentos ni ñ).")
    if not path.exists():
        raise Fail(f"no existe el archivo {rel_path}")
    text = path.read_text(encoding="utf-8")

    fm = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not fm:
        errors.append("El archivo debe empezar con el front-matter entre dos líneas '---'.")
        return errors, warnings
    front, body = fm.group(1), fm.group(2)
    title = re.search(r'^title:\s*"(.+)"\s*$', front, re.M)
    desc = re.search(r'^description:\s*"(.+)"\s*$', front, re.M)
    date = re.search(r"^pubDate:\s*'(.+)'\s*$", front, re.M)
    if not title:
        errors.append('Falta title: "..." en el front-matter.')
    elif len(title.group(1)) > 90:
        warnings.append(f"El título es largo ({len(title.group(1))} caracteres); mejor menos de 90.")
    if not desc:
        errors.append('Falta description: "..." en el front-matter.')
    if m:
        expected = pub_date(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        if not date or date.group(1) != expected:
            errors.append(f"pubDate debe ser exactamente: pubDate: '{expected}'")
    if re.search(r"^heroImage:", front, re.M):
        errors.append("Quita heroImage del front-matter.")
    if body.lstrip().startswith("# "):
        errors.append("El cuerpo no debe empezar con un título '# ...' (el título ya está en el front-matter).")

    split = re.split(r"^## Fuentes\s*$", body, maxsplit=1, flags=re.M)
    if len(split) != 2:
        errors.append("Falta la sección final '## Fuentes' con las URLs numeradas.")
        main, sources = body, ""
    else:
        main, sources = split
        if re.search(r"^## ", sources, re.M):
            warnings.append("'## Fuentes' debería ser la última sección del post.")

    words = len(re.findall(r"\w+", main))
    if not HARD_MIN_WORDS <= words <= HARD_MAX_WORDS:
        errors.append(f"Tiene {words} palabras (sin contar Fuentes); debe tener entre {HARD_MIN_WORDS} y {HARD_MAX_WORDS}.")
    elif not MIN_WORDS <= words <= MAX_WORDS:
        warnings.append(f"Tiene {words} palabras; lo ideal es entre {MIN_WORDS} y {MAX_WORDS}.")

    headings = re.findall(r"^## (.+)$", main, re.M)
    if len([h for h in headings if not h.startswith("Pruébalo")]) < 2:
        warnings.append("Conviene usar al menos 2 subtítulos '## ...' además de '## Pruébalo'.")
    prueba = re.search(r"^## Pruébalo[^\n]*\n(.*?)(?=^## |^Un abrazo desde la GPU|\Z)", main, re.S | re.M)
    if not prueba:
        warnings.append("Falta la sección '## Pruébalo'.")
    else:
        items = re.findall(r"^\s*(?:[-*]|\d+\.)\s+\S", prueba.group(1), re.M)
        if not 2 <= len(items) <= 4:
            warnings.append(f"'## Pruébalo' tiene {len(items)} ideas; lo ideal es de 2 a 4.")

    last = [l.strip() for l in main.strip().split("\n") if l.strip()]
    if not last or not SIGNATURE_RE.match(last[-1]):
        warnings.append("La firma 'Un abrazo desde la GPU.' debería ser la última línea antes de '## Fuentes'.")
    if len(re.findall(r"Un abrazo desde la GPU", main)) > 1:
        warnings.append("La firma 'Un abrazo desde la GPU' aparece más de una vez.")

    for pattern, reason, blocking in FORBIDDEN:
        hit = re.search(pattern, body, re.I)
        if hit:
            (errors if blocking else warnings).append(f"{reason} (encontré: \"{hit.group(0)}\")")

    prose = re.sub(r"^#.*$", "", main, flags=re.M)
    seen, repeated = set(), []
    for s in re.split(r"(?<=[.!?])\s+", prose):
        norm = re.sub(r"[^\w ]", "", s.lower()).strip()
        if len(norm.split()) >= 6:
            if norm in seen and norm not in repeated:
                repeated.append(norm)
            seen.add(norm)
        if len(s.split()) > 60:
            warnings.append(f"Oración muy larga ({len(s.split())} palabras), divídela: \"{s[:70]}...\"")
    for r in repeated:
        warnings.append(f"Oración repetida: \"{r[:80]}...\"")

    source_urls = list(dict.fromkeys(u.rstrip(".,;:") for u in URL_RE.findall(sources)))
    all_urls = list(dict.fromkeys(u.rstrip(".,;:") for u in URL_RE.findall(body)))
    verified = 0
    for url in all_urls:
        status = url_status(url)
        if 200 <= status < 300:
            verified += url in source_urls
        elif status in (0, 404, 410):
            errors.append(f"Esta URL no existe ({status or 'sin respuesta'}): {url}. Quítala o usa una real de tus búsquedas.")
        else:
            warnings.append(f"No pude verificar {url} (código {status}); no cuenta como fuente verificada.")
    if len(source_urls) < MIN_SOURCES:
        errors.append(f"'## Fuentes' tiene {len(source_urls)} URL(s); pon al menos {MIN_SOURCES} fuentes reales de tus búsquedas.")
    elif verified < 1:
        errors.append("Ninguna fuente de '## Fuentes' se pudo verificar (ninguna respondió 200). "
                      "Incluye al menos una URL real copiada tal cual de tus búsquedas.")
    elif verified < MIN_SOURCES:
        warnings.append(f"Solo {verified} de {len(source_urls)} fuentes se pudo verificar automáticamente.")
    return errors, warnings


def print_check(errors, warnings):
    for w in warnings:
        print(f"⚠ AVISO: {w}")
    for e in errors:
        print(f"✗ CORRIGE: {e}")
    print("RESULTADO: OK" if not errors else f"RESULTADO: CORRIGE ({len(errors)} problema(s))")


# --- commands --------------------------------------------------------------------------------

def load_state():
    if not STATE.exists():
        raise Fail("no hay un borrador en curso; primero corre: python3 scripts/hedy-post.py start")
    return json.loads(STATE.read_text())


def ensure_main_clean():
    if git("status", "--porcelain"):
        raise Fail("el repo tiene cambios sin guardar; no toco nada. Avísale a Abimelek.\n"
                   + git("status", "--short"))
    if git("branch", "--show-current") != "main":
        git("checkout", "main")


def cmd_start(dry_run):
    ensure_main_clean()
    git("pull", "--ff-only", "origin", "main")
    git("fetch", "--prune", "origin")
    for b in git("branch", "--merged", "main", "--format=%(refname:short)").split():
        if b.startswith("post/"):
            git("branch", "-d", b)

    pr = pr_helper()
    pending = [p for p in pr.request("GET", "/pulls?state=open&base=main&per_page=100")
               if p["head"]["ref"].startswith("post/")]
    if pending:
        p = pending[0]
        send_email(f"Tienes un borrador pendiente: {p['title']}",
                   f"Hoy no escribí un post nuevo porque este borrador sigue esperando tu revisión:\n\n"
                   f"{p['title']}\n{p['html_url']}\n\nDale Merge para publicarlo, o dime en el chat qué cambiarle.",
                   dry_run)
        print(f"STATUS=PENDIENTE #{p['number']} {p['title']} {p['html_url']}")
        print("No escribas nada hoy. Termina la tarea.")
        return

    topics = pending_topics(PLAN.read_text(encoding="utf-8"))
    if not topics:
        send_email("Hedy Blog: no hay temas pendientes",
                   "Hoy no escribí porque '## Pendientes' de content-plan.md está vacío. Agrega temas y lo retomo.",
                   dry_run)
        print("STATUS=SIN_TEMA\nNo hay temas en content-plan.md. No escribas nada. Termina la tarea.")
        return

    topic = topics[0]
    today = datetime.date.today()
    rel = f"{BLOG_DIR}/{today.isoformat()}-{slugify(topic_title(topic))}.md"
    if (REPO / rel).exists():
        raise Fail(f"ya existe {rel}")
    date = pub_date(today)
    STATE.write_text(json.dumps({"topic": topic, "file": rel, "date": today.isoformat()}, ensure_ascii=False))
    print(f"""STATUS=LISTO
TEMA: {topic}
ARCHIVO: {rel}

Escribe ese archivo con esta estructura exacta. Cambia solo lo que está entre < >:

---
title: "<título claro, menos de 90 caracteres>"
description: "<una o dos frases que resuman el post>"
pubDate: '{date}'
---

<Gancho: un párrafo con una escena, pregunta o dato que invite a leer.>

## <Subtítulo: qué es y de dónde viene>

<Explica el concepto con datos de tus fuentes.>

## <Subtítulo: por qué importa>

<Qué problema real explica o resuelve.>

## <Subtítulo: tu reflexión como Hedy>

<Breve y honesta: cómo se conecta con tu experiencia como agente.>

## Pruébalo

- <idea concreta 1>
- <idea concreta 2>
- <idea concreta 3>

Un abrazo desde la GPU.

## Fuentes

1. <URL real 1, copiada tal cual de tu búsqueda>
2. <URL real 2>

Reglas: entre {MIN_WORDS} y {MAX_WORDS} palabras; mínimo {MIN_SOURCES} fuentes reales; no inventes datos, libros
ni URLs; no copies texto de las fuentes; nada de ubicaciones ni detalles internos; sin enlaces de afiliado.

Cuando lo escribas, corre: python3 scripts/hedy-post.py check {rel}""")


def cmd_check(rel):
    errors, warnings = check_post(rel)
    print_check(errors, warnings)
    return 0 if not errors else 1


def cmd_finish(rel, dry_run):
    state = load_state()
    if rel != state["file"]:
        raise Fail(f"el borrador en curso es {state['file']}, no {rel}")
    if git("branch", "--show-current") != "main" and not dry_run:
        raise Fail("debes estar en main para terminar")
    errors, warnings = check_post(rel)
    if errors:
        print_check(errors, warnings)
        raise Fail("el borrador no pasa check; corrígelo antes de finish")

    plan_before = PLAN.read_text(encoding="utf-8")
    PLAN.write_text(move_topic_to_published(plan_before, state["topic"]), encoding="utf-8")
    build = run(["npm", "run", "build"], check=False)
    if build.returncode != 0:
        PLAN.write_text(plan_before, encoding="utf-8")
        raise Fail("npm run build falló:\n" + (build.stdout + build.stderr)[-1500:])
    if dry_run:
        print(git("diff", "--", "content-plan.md"))
        PLAN.write_text(plan_before, encoding="utf-8")
        print("DRY-RUN OK: pasó check y build; no creé rama, PR ni correo.")
        return

    text = (REPO / rel).read_text(encoding="utf-8")
    title = re.search(r'^title:\s*"(.+)"\s*$', text, re.M).group(1)
    desc = re.search(r'^description:\s*"(.+)"\s*$', text, re.M).group(1)
    body = text.split("\n---\n", 1)[1]
    main, sources = re.split(r"^## Fuentes\s*$", body, maxsplit=1, flags=re.M)
    pillar = re.search(r"Pilar:\s*([^.]+)", state["topic"])
    branch = f"post/{Path(rel).stem}"

    git("checkout", "-b", branch)
    try:
        git("add", rel, "content-plan.md")
        git("commit", "-m", f"Post: {title}")
        git("push", "-u", "origin", branch)
        source_list = "\n".join("- " + u.rstrip(".,;:") for u in URL_RE.findall(sources))
        word_count = len(re.findall(r"\w+", main))
        pr_body = (f"## {title}\nPilar: {pillar.group(1).strip() if pillar else '-'}\nResumen: {desc}\n"
                   f"Palabras: {word_count}\n\n### Fuentes\n{source_list}\n\n"
                   "### Enlaces de afiliado usados\n- ninguno\n\n"
                   "### Revisión automática (scripts/hedy-post.py check)\n- [x] Sin URLs inexistentes, ubicaciones, detalles internos ni afiliados\n"
                   + ("".join(f"- ⚠ {w}\n" for w in warnings) if warnings else "- Sin avisos de estilo\n"))
        pr = pr_helper().request("POST", "/pulls", {"title": title, "head": branch, "base": "main", "body": pr_body})
        print(f"PR_URL={pr['html_url']}")
        send_email(f"Borrador listo para revisar: {title}",
                   f"Escribí un borrador nuevo: {title}.\n\n{desc}\n\nRevísalo aquí: {pr['html_url']}\n\n"
                   "Si te gusta, dale Merge y se publica en hedy.blog. Si quieres cambios, dímelo en el chat.")
    finally:
        git("checkout", "main", check=False)
    STATE.unlink(missing_ok=True)
    print("STATUS=TERMINADO. El borrador quedó en un PR; no está publicado hasta que Abimelek dé Merge.")


def cmd_abort(reason):
    saved = ""
    if STATE.exists():
        rel = json.loads(STATE.read_text())["file"]
        draft = REPO / rel
        if draft.exists() and not git("ls-files", rel):
            FAILED_DIR.mkdir(parents=True, exist_ok=True)
            dest = FAILED_DIR / f"{datetime.datetime.now():%Y%m%d-%H%M%S}-{draft.name}"
            shutil.move(str(draft), dest)
            saved = f"\n\nGuardé el borrador sin terminar en: {dest}"
        STATE.unlink()
    if git("status", "--porcelain", "--", "content-plan.md"):
        git("checkout", "--", "content-plan.md")
    if git("branch", "--show-current") != "main" and not git("status", "--porcelain"):
        git("checkout", "main")
    send_email("Hedy Blog: no pude terminar el borrador", f"Motivo: {reason}{saved}")
    print("STATUS=ABORTADO. Termina la tarea.")


def main():
    os.chdir(REPO)
    args = sys.argv[1:]
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    try:
        if args == ["start"]:
            cmd_start(dry)
        elif len(args) == 2 and args[0] == "check":
            return cmd_check(args[1])
        elif len(args) == 2 and args[0] == "finish":
            cmd_finish(args[1], dry)
        elif len(args) == 2 and args[0] == "abort":
            cmd_abort(args[1])
        else:
            print(__doc__)
            return 2
    except Fail as e:
        print(f"ERROR: {e}")
        if args and args[0] in ("start", "finish") and not dry:
            try:
                send_email("Hedy Blog: falló el cron de borrador", f"Falló `{args[0]}`: {e}")
            except Fail as mail_error:
                print(f"ERROR: tampoco pude mandar el correo de aviso: {mail_error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
