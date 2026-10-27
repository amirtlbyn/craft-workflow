#!/usr/bin/env python3
"""craft_stack - which stacks a repository runs, and what each one needs.

A stack pack is stacks/<id>/stack.json. It says how to recognize the stack
(marker files, a dependency name), where its tests live and how a test names a
criterion, which commands prove Gate A, which paths carry money, auth,
migrations, data access and entry points, which skills and standards apply, and
which concurrency skill it has.

This module finds the packs that match a repository, and answers questions
about them. bin/craft-stack is its command line. bin/craft-spec trace,
bin/craft-check, bin/craft-toolchain, bin/craft-jev, bin/craft-ui-state and the
SessionStart hook read it.

Detection looks at the repository root and at directories up to two levels
below it, so a monorepo with services/wallet/go.mod and web/package.json gets
both stacks, each owning its own directory. Within one directory, one pack per
language wins, by priority: manage.py makes a Python directory Django even when
FastAPI is also a dependency.

An override wins over detection:

    CRAFT_STACK=go,node                    for one shell
    .claude/craft/stack.json               {"stacks": ["fastapi"]}, written by
                                           bin/craft-stack set fastapi

Two rules, the same as craft_state:

1. Nothing here raises. Every public function returns a safe default.
2. Nothing here writes, except set_override(), and that only under .claude/craft/.

Standard library only.
"""

import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

PLUGIN_ROOT = craft_state.PLUGIN_ROOT
STACKS_DIR = PLUGIN_ROOT / "stacks"
OVERRIDE_FILE = "stack.json"
DEFAULT_STACK = "django"
MAX_DEPTH = 2
MAX_READ_BYTES = 256 * 1024
MAX_SCAN_FILES = 400
PATH_KEYS = ("money", "auth", "migrations", "models", "views")
SKIP_DIRECTORIES = {
    ".git", ".claude", ".hg", ".svn", ".tox", ".venv", "venv", "env", ".env",
    "node_modules", "__pycache__", "site-packages", "build", "dist", "target",
    "vendor", ".gradle", ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".next", ".nuxt", ".output", "coverage", "out", "bin", "obj",
}

_packs_cache = None


# ---------------------------------------------------------------------------
# Packs
# ---------------------------------------------------------------------------


def load_packs():
    """Return {id: pack} for every stacks/<id>/stack.json that parses."""
    global _packs_cache
    if _packs_cache is not None:
        return _packs_cache
    packs = {}
    try:
        for path in sorted(STACKS_DIR.glob("*/stack.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and data.get("id"):
                data["_dir"] = str(path.parent.relative_to(PLUGIN_ROOT))
                packs[str(data["id"])] = data
    except Exception:
        packs = {}
    _packs_cache = packs
    return packs


def pack(stack_id):
    """Return one pack, or {}."""
    return load_packs().get(str(stack_id or ""), {})


def _read(path, limit=MAX_READ_BYTES):
    try:
        with open(str(path), "rb") as handle:
            return handle.read(limit).decode("utf-8", errors="replace")
    except OSError:
        return ""


def _matches_detect(data, directory):
    """Return the evidence string when the pack's detect rules match directory, else ''."""
    detect = data.get("detect") or {}
    for name in detect.get("any_file") or []:
        if (directory / name).is_file():
            return name
    for rule in detect.get("any_contains") or []:
        try:
            pattern = re.compile(rule.get("pattern") or "$^")
        except re.error:
            continue
        for name in rule.get("files") or []:
            candidate = directory / name
            if candidate.is_file() and pattern.search(_read(candidate)):
                return "%s names %s" % (name, data.get("id"))
    return ""


def _walk_directories(root, depth=MAX_DEPTH):
    """Yield (relative_posix, path) for root and its subdirectories up to depth."""
    yield "", root
    frontier = [(root, 0)]
    while frontier:
        directory, level = frontier.pop(0)
        if level >= depth:
            continue
        try:
            children = sorted(entry for entry in directory.iterdir() if entry.is_dir())
        except OSError:
            continue
        for child in children:
            if child.name in SKIP_DIRECTORIES or child.name.startswith("."):
                continue
            yield child.relative_to(root).as_posix(), child
            frontier.append((child, level + 1))


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def read_override(cwd=None):
    """Return the stack ids an override names, or []."""
    try:
        environment = str(os.environ.get("CRAFT_STACK", "")).strip()
        if environment:
            return [part.strip() for part in environment.split(",") if part.strip() in load_packs()]
        path = craft_state.state_path(OVERRIDE_FILE, cwd)
        data = json.loads(path.read_text(encoding="utf-8"))
        stacks = data.get("stacks") if isinstance(data, dict) else None
        if isinstance(stacks, list):
            return [str(item) for item in stacks if str(item) in load_packs()]
    except Exception:
        pass
    return []


def set_override(stacks, cwd=None):
    """Write .claude/craft/stack.json. An empty list removes it. Return True on success."""
    try:
        path = craft_state.state_path(OVERRIDE_FILE, cwd)
        if not stacks:
            if path.is_file():
                path.unlink()
            return True
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"stacks": list(stacks), "updated_at": craft_state.now()}, indent=2) + "\n",
            encoding="utf-8",
        )
        return True
    except Exception:
        return False


def detect(cwd=None):
    """Return the stacks of the repository, root first.

    Each entry: {"id", "dir", "evidence"}. "dir" is relative to the repository
    root, "" for the root itself. With an override, the named stacks own the
    root and the evidence says "override".
    """
    try:
        root = craft_state.host_root(cwd)
        override = read_override(cwd)
        if override:
            return [{"id": stack_id, "dir": "", "evidence": "override"} for stack_id in override]
        packs = load_packs()
        found = []
        for relative, directory in _walk_directories(root):
            per_language = {}
            for stack_id, data in packs.items():
                evidence = _matches_detect(data, directory)
                if not evidence:
                    continue
                language = data.get("language") or stack_id
                best = per_language.get(language)
                if best is None or int(data.get("priority", 0)) > int(packs[best[0]].get("priority", 0)):
                    per_language[language] = (stack_id, evidence)
            for stack_id, evidence in per_language.values():
                found.append({"id": stack_id, "dir": relative, "evidence": evidence})
        found.sort(key=lambda item: (item["dir"].count("/") + (1 if item["dir"] else 0),
                                     item["dir"], -int(packs[item["id"]].get("priority", 0))))
        return found
    except Exception:
        return []


def primary(cwd=None, found=None):
    """Return the id of the repository's main stack, or DEFAULT_STACK."""
    try:
        found = detect(cwd) if found is None else found
        if not found:
            return DEFAULT_STACK
        packs = load_packs()
        at_root = [item for item in found if item["dir"] == ""]
        pool = at_root or found
        pool = sorted(pool, key=lambda item: -int(packs.get(item["id"], {}).get("priority", 0)))
        return pool[0]["id"]
    except Exception:
        return DEFAULT_STACK


def stack_ids(cwd=None, found=None):
    """Return the distinct stack ids found, primary first. Never empty."""
    found = detect(cwd) if found is None else found
    ids = [primary(cwd, found)]
    for item in found:
        if item["id"] not in ids:
            ids.append(item["id"])
    return ids


def owner_of(path, cwd=None, found=None):
    """Return the stack entry that owns a repository-relative path, or None.

    The deepest stack directory that contains the path wins. A file outside
    every stack directory belongs to the primary stack.
    """
    try:
        found = detect(cwd) if found is None else found
        text = str(path).replace("\\", "/")
        root = craft_state.host_root(cwd).as_posix()
        if text.startswith(root + "/"):
            text = text[len(root) + 1:]
        while text.startswith("./"):
            text = text[2:]
        best = None
        for item in found:
            prefix = item["dir"]
            if prefix and not (text == prefix or text.startswith(prefix + "/")):
                continue
            if best is None or len(prefix) > len(best["dir"]):
                best = item
        if best is not None:
            return best
        stack_id = primary(cwd, found)
        return {"id": stack_id, "dir": "", "evidence": "primary"}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Globs, tests, skills, standards
# ---------------------------------------------------------------------------


def globs_for(key, cwd=None, found=None):
    """Return config/paths.json[key] plus the globs every detected stack adds for key."""
    globs = list(craft_state.globs_for(key))
    try:
        for stack_id in stack_ids(cwd, found):
            paths = pack(stack_id).get("paths")
            if not isinstance(paths, dict):
                continue
            for glob in paths.get(key) or []:
                if isinstance(glob, str) and glob and glob not in globs:
                    globs.append(glob)
    except Exception:
        pass
    return globs


def test_spec(cwd=None, found=None):
    """Return {"globs": [...], "extensions": [...]} for every detected stack."""
    globs, extensions = [], []
    try:
        for stack_id in stack_ids(cwd, found):
            tests = pack(stack_id).get("tests") or {}
            for glob in tests.get("globs") or []:
                if glob not in globs:
                    globs.append(glob)
            for extension in tests.get("extensions") or []:
                if extension not in extensions:
                    extensions.append(extension)
    except Exception:
        pass
    for glob in craft_state.globs_for("tests"):
        if not glob.endswith(".md") and glob not in globs:
            globs.append(glob)
    # config/paths.json's tests globs are Python's, and they always apply.
    if ".py" not in extensions:
        extensions.append(".py")
    return {"globs": globs, "extensions": extensions}


def skills_for(cwd=None, paths=None, found=None, with_concurrency=True):
    """Return the skills the stacks of paths need, primary first, without duplicates.

    With no paths, every detected stack counts. A skill is returned only when
    `skills/<name>/SKILL.md` exists in the plugin, so a pack that names a
    missing skill does not dangle. The concurrency skill of a stack is added
    only when that stack's concurrency report says it is ready.
    """
    found = detect(cwd) if found is None else found
    if paths:
        owners = []
        for path in paths:
            owner = owner_of(path, cwd, found)
            if owner and owner not in owners:
                owners.append(owner)
    else:
        owners = found or [{"id": primary(cwd, found), "dir": "", "evidence": "primary"}]
    skills = []
    for owner in owners:
        data = pack(owner["id"])
        for name in data.get("skills") or []:
            if name in skills:
                continue
            if not (PLUGIN_ROOT / "skills" / str(name) / "SKILL.md").is_file():
                continue
            skills.append(name)
        if with_concurrency:
            report = concurrency(cwd, owner)
            skill = report.get("skill")
            if skill and report.get("verdict") == "ready" and skill not in skills:
                skills.append(skill)
    return skills


def checks_for(stack_id, cwd=None, directory=""):
    """Return {label: command} for one stack, its conditions read in its directory."""
    result = {}
    try:
        data = pack(stack_id)
        root = craft_state.host_root(cwd)
        base = root / directory if directory else root
        manifest = _manifest(base, data.get("language"))
        manager = _node_manager(base)
        for label, candidates in (data.get("checks") or {}).items():
            if not isinstance(candidates, list):
                continue
            for candidate in candidates:
                if not isinstance(candidate, dict) or not candidate.get("run"):
                    continue
                if _candidate_applies(candidate, base, manifest):
                    command = str(candidate["run"]).replace("{pm}", manager)
                    if directory and not command.startswith("cd "):
                        command = "cd %s && %s" % (directory, command)
                    result[label] = command
                    break
    except Exception:
        pass
    return result


def _candidate_applies(candidate, base, manifest):
    if "when_file" in candidate and not (base / candidate["when_file"]).is_file():
        return False
    if "when_any_file" in candidate and not any((base / name).is_file() for name in candidate["when_any_file"]):
        return False
    rule = candidate.get("when_contains")
    if isinstance(rule, dict):
        target = base / str(rule.get("file", ""))
        try:
            if not target.is_file() or not re.search(rule.get("pattern") or "$^", _read(target)):
                return False
        except re.error:
            return False
    if "when_script" in candidate:
        scripts = manifest.get("scripts") if isinstance(manifest.get("scripts"), dict) else {}
        if candidate["when_script"] not in scripts:
            return False
    if "when_dependency" in candidate:
        name = candidate["when_dependency"]
        dependencies = {}
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            if isinstance(manifest.get(key), dict):
                dependencies.update(manifest[key])
        if name not in dependencies:
            return False
    return True


def _package_json(base):
    return _json_file(base / "package.json")


def _json_file(path):
    try:
        data = json.loads(_read(path) or "{}")
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _manifest(base, language):
    """Return the manifest of a pack's language: composer.json for php, package.json otherwise."""
    if language != "php":
        return _package_json(base)
    composer = _json_file(base / "composer.json")
    keys = (("scripts", "scripts"), ("require", "dependencies"), ("require-dev", "devDependencies"))
    return {target: composer[source] for source, target in keys if isinstance(composer.get(source), dict)}


def _node_manager(base):
    for lockfile, manager in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"),
                              ("bun.lockb", "bun"), ("bun.lock", "bun")):
        if (base / lockfile).is_file():
            return manager
    return "npm"


def toolchain_for(stack_id):
    """Return the toolchain list of a stack, or None when it uses config/toolchain.json."""
    value = pack(stack_id).get("toolchain")
    return value if isinstance(value, list) else None


def lens_addendum(lens, stack_id):
    """Return the "## <lens>" section of a stack's lenses.md, or ''."""
    try:
        relative = pack(stack_id).get("lenses")
        if not relative:
            return ""
        text = (PLUGIN_ROOT / relative).read_text(encoding="utf-8")
        lines, inside = [], False
        for line in text.splitlines():
            heading = re.match(r"^##\s+(.+?)\s*$", line)
            if heading:
                inside = heading.group(1).strip().lower() == lens.lower()
                continue
            if inside:
                lines.append(line)
        if lines:
            return "\n".join(lines).strip()
        # Fall back to a keyword match: a lens named "ssr" resolves the
        # "## SSR Safety Lens" section (php packs name headings by lens id;
        # frontend packs use prose headings).
        needle = lens.lower()
        for line in text.splitlines():
            heading = re.match(r"^##\s+(.+?)\s*$", line)
            if heading and needle in heading.group(1).strip().lower():
                inside = True
                continue
            if inside:
                if heading:
                    inside = False
                    continue
                lines.append(line)
        return "\n".join(lines).strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Concurrency readiness
# ---------------------------------------------------------------------------
#
# The question is not "can this language do concurrency". It is "was this
# system built for the kind of concurrency the change wants". Each analyzer
# reads cheap evidence (dependencies, server commands, how handlers are
# declared) and returns one of three verdicts:
#
#   ready      the system runs this model already. The stack's concurrency
#              skill applies, and new code follows the model it already has.
#   limited    some of it is safe, and the report says which part. Anything
#              beyond that part is a change of model.
#   not-ready  the system was not built for it. Do not introduce it in a task.
#              Fix the bottleneck another way, or promote to project and design
#              the change of model.


def _scan_sources(base, extensions, limit=MAX_SCAN_FILES):
    """Yield (relative, text) for up to limit source files under base."""
    count = 0
    for directory, subdirectories, filenames in os.walk(str(base)):
        subdirectories[:] = [name for name in subdirectories
                             if name not in SKIP_DIRECTORIES and not name.startswith(".")]
        for filename in filenames:
            if not filename.endswith(tuple(extensions)):
                continue
            path = pathlib.Path(directory) / filename
            count += 1
            if count > limit:
                return
            yield path.relative_to(base).as_posix(), _read(path, 128 * 1024)


def _text_of(base, names):
    parts = []
    for name in names:
        if any(char in name for char in "*?["):
            for path in sorted(base.glob(name))[:8]:
                parts.append(_read(path))
        else:
            parts.append(_read(base / name))
    return "\n".join(parts)


PY_DEPENDENCY_FILES = ["pyproject.toml", "requirements.txt", "requirements/*.txt", "Pipfile", "setup.cfg"]
DEPLOY_FILES = ["Dockerfile", "Dockerfile.*", "*.Dockerfile", "docker-compose*.yml", "docker-compose*.yaml",
                "compose*.yml", "compose*.yaml", "Procfile", "gunicorn*.py", "*.ini", "deploy/*", "k8s/*", "helm/*/*.yaml"]


def _concurrency_django(base):
    dependencies = _text_of(base, PY_DEPENDENCY_FILES).lower()
    deploy = _text_of(base, DEPLOY_FILES).lower()
    evidence = []
    asgi_server = re.search(r"\b(uvicorn|daphne|hypercorn|granian)\b", deploy) or "uvicornworker" in deploy
    wsgi_server = re.search(r"\bgunicorn\b", deploy) and not asgi_server
    if asgi_server:
        evidence.append("an ASGI server is in the deployment files (%s)" % (
            asgi_server.group(1) if hasattr(asgi_server, "group") else "UvicornWorker"))
    elif wsgi_server:
        evidence.append("gunicorn runs it with WSGI workers")
    else:
        evidence.append("no ASGI server found in the deployment files")
    channels = "channels" in dependencies
    if channels:
        evidence.append("django-channels is a dependency")
    async_views = 0
    sync_views = 0
    for relative, text in _scan_sources(base, (".py",)):
        if not re.search(r"(^|/)(views?|api|viewsets?)(/|\.py$)", relative):
            continue
        async_views += len(re.findall(r"^\s*async\s+def\s+\w+", text, re.M))
        sync_views += len(re.findall(r"^\s*def\s+(get|post|put|patch|delete|list|create|update|retrieve|destroy)\b", text, re.M))
    evidence.append("%d async and about %d sync view handlers" % (async_views, sync_views))
    drf = "djangorestframework" in dependencies or "rest_framework" in dependencies
    if drf:
        evidence.append("DRF views are sync, whatever the server")
    if (asgi_server or channels) and async_views:
        verdict, model = "limited", "asgi, mostly sync"
        summary = ("ASGI-served with some async views. New async code is allowed only in a view whose "
                   "whole call chain is async-safe. The ORM stays sync: wrap it in sync_to_async, or keep the view sync.")
    else:
        verdict, model = "not-ready", "wsgi, sync"
        summary = ("This Django service is sync. Do not add async views, asyncio, or threads to serve "
                   "more requests. Fix the bottleneck with queries, indexes, bulk operations, caching, or a "
                   "Celery task. Moving to ASGI is a project with its own design.")
    return {
        "model": model,
        "verdict": verdict,
        "summary": summary,
        "evidence": evidence,
        "allowed": [
            "select_for_update, unique constraints and idempotency keys: concurrency for correctness, always",
            "Celery tasks for slow or parallel work, made idempotent",
            "bulk_create, bulk_update, in_bulk, and bounded querysets",
        ] + (["async views whose whole call chain is async-safe"] if verdict == "limited" else []),
        "avoid": [
            "async def views that call the ORM directly",
            "asyncio.run or a new event loop inside a request",
            "threads or ThreadPoolExecutor inside a view",
            "a long transaction around a network call",
        ],
    }


def _concurrency_fastapi(base):
    dependencies = _text_of(base, PY_DEPENDENCY_FILES).lower()
    evidence = []
    async_handlers = 0
    sync_handlers = 0
    blocking = []
    for relative, text in _scan_sources(base, (".py",)):
        for match in re.finditer(r"@\w+\.(get|post|put|patch|delete|websocket|api_route)\([^\n]*\n(\s*@[^\n]*\n)*\s*(async\s+)?def\s", text):
            if match.group(3):
                async_handlers += 1
            else:
                sync_handlers += 1
        if re.search(r"^\s*async\s+def", text, re.M):
            for pattern, label in ((r"\brequests\.(get|post|put|patch|delete|request)\(", "requests"),
                                   (r"\btime\.sleep\(", "time.sleep"),
                                   (r"\bpsycopg2\b", "psycopg2"),
                                   (r"\bopen\([^)]*\)\.read\(", "blocking file read")):
                if re.search(pattern, text):
                    item = "%s in %s" % (label, relative)
                    if item not in blocking and len(blocking) < 6:
                        blocking.append(item)
    async_drivers = [name for name in ("asyncpg", "aiomysql", "aiosqlite", "motor", "sqlalchemy[asyncio]",
                                       "databases", "tortoise", "psycopg[", "redis", "httpx", "aiohttp")
                     if name in dependencies]
    sync_drivers = [name for name in ("psycopg2", "pymysql", "requests") if name in dependencies]
    evidence.append("%d async and %d sync route handlers" % (async_handlers, sync_handlers))
    if async_drivers:
        evidence.append("async libraries: %s" % ", ".join(async_drivers))
    if sync_drivers:
        evidence.append("sync libraries: %s" % ", ".join(sync_drivers))
    if blocking:
        evidence.append("blocking calls inside async code: %s" % "; ".join(blocking))
    if async_handlers and async_handlers >= sync_handlers and not blocking:
        verdict, model = "ready", "async-native"
        summary = ("async-native. Use fastapi-async: async drivers, one client per lifespan, bounded "
                   "gather, timeouts, and run_in_threadpool for any blocking library.")
    elif async_handlers:
        verdict, model = "limited", "mixed"
        summary = ("Mixed. Async handlers exist, but the evidence shows blocking calls or sync drivers. "
                   "New async code must not call them. Fix the blocking call first, or keep the handler a plain def.")
    else:
        verdict, model = "not-ready", "sync, threadpool"
        summary = ("Handlers are plain def, which FastAPI runs in a threadpool. Keep them def. Turning "
                   "them async with sync drivers blocks the event loop. Switching drivers is a project.")
    return {
        "model": model,
        "verdict": verdict,
        "summary": summary,
        "evidence": evidence,
        "allowed": (["async def handlers with async drivers", "asyncio.TaskGroup or a Semaphore-bounded gather",
                     "asyncio.timeout around every outbound call", "run_in_threadpool for a blocking library"]
                    if verdict != "not-ready" else
                    ["plain def handlers on the threadpool", "BackgroundTasks for small post-response work",
                     "a task queue for slow work"]),
        "avoid": ["a blocking call (requests, time.sleep, a sync driver) inside async def",
                  "unbounded asyncio.gather over user-sized input",
                  "a client or engine created per request",
                  "fire-and-forget asyncio.create_task without a reference or an owner"],
    }


def _concurrency_go(base):
    gomod = _read(base / "go.mod")
    evidence = ["goroutines are part of the language"]
    version = re.search(r"^go\s+(\d+\.\d+)", gomod, re.M)
    if version:
        evidence.append("go %s" % version.group(1))
    if "golang.org/x/sync" in gomod:
        evidence.append("golang.org/x/sync is a dependency (errgroup, semaphore)")
    contexts = 0
    goroutines = 0
    for _relative, text in _scan_sources(base, (".go",), limit=300):
        contexts += len(re.findall(r"ctx\s+context\.Context", text))
        goroutines += len(re.findall(r"\bgo\s+(func\b|\w+\()", text))
    evidence.append("%d functions take ctx context.Context, %d go statements" % (contexts, goroutines))
    verdict = "ready" if contexts or not goroutines else "limited"
    summary = ("Go is built for it. Every goroutine still needs an owner, a stop signal, and a bound. "
               "Use go-concurrency, and add go test -race to Gate A.")
    if verdict == "limited":
        summary = ("Goroutines exist, but no function takes a context.Context, so nothing can cancel them. "
                   "Thread ctx through the call chain before adding more.")
    return {
        "model": "goroutines",
        "verdict": verdict,
        "summary": summary,
        "evidence": evidence,
        "allowed": ["errgroup.WithContext with SetLimit", "a bounded worker pool fed by a channel",
                    "context cancellation through every call", "sync.Mutex for shared state, atomic for counters"],
        "avoid": ["a go statement with no owner and no way to stop it", "an unbounded goroutine per item",
                  "a send that blocks forever after the receiver gave up", "a shared map without a lock",
                  "closing a channel from the receiving side"],
    }


def _concurrency_java(base):
    build = _text_of(base, ["pom.xml", "build.gradle", "build.gradle.kts"]).lower()
    properties = _text_of(base, ["src/main/resources/application*.properties", "src/main/resources/application*.yml",
                                 "src/main/resources/application*.yaml"]).lower()
    evidence = []
    reactive = "spring-boot-starter-webflux" in build or "io.projectreactor" in build
    virtual = re.search(r"spring\.threads\.virtual\.enabled\s*[:=]\s*true|virtual:\s*\n\s*enabled:\s*true", properties)
    java_version = re.search(r"<java\.version>(\d+)|languageversion\.set\(javalanguageversion\.of\((\d+)\)|sourcecompatibility\s*=\s*['\"]?(?:javaversion\.version_)?(\d+)", build)
    if java_version:
        evidence.append("java %s" % next(group for group in java_version.groups() if group))
    if reactive:
        evidence.append("WebFlux or Reactor is a dependency")
        model, verdict = "reactive", "ready"
        summary = ("Reactive. Stay non-blocking end to end: no .block(), no JDBC on the event loop. "
                   "A blocking call needs publishOn(Schedulers.boundedElastic()).")
    elif virtual:
        evidence.append("spring.threads.virtual.enabled=true")
        model, verdict = "virtual threads", "ready"
        summary = ("Virtual threads. Blocking I/O is cheap. Bound concurrency with a Semaphore, not a pool size, "
                   "and avoid synchronized around blocking calls.")
    else:
        evidence.append("Spring MVC style: one platform thread per request")
        model, verdict = "thread-per-request", "limited"
        summary = ("Thread-per-request. A bounded executor with CompletableFuture is allowed for independent "
                   "I/O. Do not introduce reactive types or parallel streams for I/O. Changing the model is a project.")
    return {
        "model": model,
        "verdict": verdict,
        "summary": summary,
        "evidence": evidence,
        "allowed": ["a bounded, named executor bean with CompletableFuture", "@Transactional on the service, never across a network call",
                    "optimistic locking (@Version) or SELECT ... FOR UPDATE for money"],
        "avoid": ["parallelStream() for I/O", "an unbounded Executors.newCachedThreadPool()",
                  "@Async without a configured executor", "mixing Mono/Flux into an MVC service"],
    }


def _concurrency_node(base):
    manifest = _package_json(base)
    dependencies = {}
    for key in ("dependencies", "devDependencies"):
        if isinstance(manifest.get(key), dict):
            dependencies.update(manifest[key])
    evidence = ["one event loop: I/O concurrency is native"]
    workers = False
    for _relative, text in _scan_sources(base, (".ts", ".js", ".mjs", ".cjs"), limit=300):
        if "worker_threads" in text or "piscina" in text:
            workers = True
            break
    if workers or "piscina" in dependencies:
        evidence.append("worker_threads or piscina is in use")
    for name in ("p-limit", "p-queue", "bullmq", "bull"):
        if name in dependencies:
            evidence.append("%s is a dependency" % name)
    return {
        "model": "event loop",
        "verdict": "ready",
        "summary": ("I/O concurrency is native: bounded Promise.all, AbortSignal timeouts. CPU-bound work "
                    + ("may use the worker pool the service already has." if workers else
                       "blocks every request, and this service has no worker pool, so adding one is a project.")),
        "evidence": evidence,
        "allowed": ["Promise.all over a bounded batch, or p-limit", "AbortSignal.timeout on every outbound call",
                    "a queue (BullMQ) for slow work"] + (["the existing worker pool for CPU-bound work"] if workers else []),
        "avoid": ["an unawaited promise", "Promise.all over user-sized input", "a sync fs or crypto call in a request",
                  "CPU-bound loops on the event loop"],
    }


def _concurrency_php(base):
    path = base / "composer.json"
    allowed = ["a queue (Laravel queues and Horizon, Symfony Messenger) for slow work",
               "Http::pool, Guzzle promises, or concurrent Symfony HttpClient requests, with a bound and a timeout",
               "a database lock or an atomic guarded update for money"]
    avoid = ["pcntl_fork in a web request", "unbounded promise or request fan-out", "sleep in a request",
             "long work in the request cycle"]
    manifest = None
    if path.is_file():
        try:
            manifest = json.loads(_read(path) or "")
        except ValueError:
            manifest = None
        if not isinstance(manifest, dict):
            return {
                "model": "unknown", "verdict": "not-ready",
                "summary": "composer.json is not valid JSON, so the concurrency model cannot be read. Fix it first.",
                "evidence": ["composer.json does not parse"], "allowed": [], "avoid": avoid,
            }
    names = {}
    for key in ("require", "require-dev"):
        if isinstance(manifest, dict) and isinstance(manifest.get(key), dict):
            names.update(manifest[key])
    workers = sorted(name for name in names if name.startswith((
        "laravel/octane", "spiral/roadrunner", "openswoole/", "swoole/swoole", "runtime/frankenphp-symfony")))
    event = sorted(name for name in names if name in (
        "react/event-loop", "react/http", "react/socket", "amphp/amp", "amphp/http-server", "revolt/event-loop"))
    if workers:
        return {
            "model": "long-lived workers", "verdict": "limited",
            "summary": ("Long-lived workers keep the application in memory between requests. Request data must not "
                        "outlive the request. Changing the model is a project."),
            "evidence": ["%s is a dependency" % name for name in workers],
            "allowed": allowed,
            "avoid": avoid + ["static properties that hold request data", "a singleton that holds request data",
                              "a container binding that captures the request"],
        }
    if event:
        return {
            "model": "event loop", "verdict": "ready",
            "summary": "An event loop (ReactPHP or Amp). I/O concurrency is native. Never block the loop.",
            "evidence": ["%s is a dependency" % name for name in event],
            "allowed": allowed + ["promises and streams on the event loop, bounded"],
            "avoid": avoid + ["a blocking call on the loop"],
        }
    return {
        "model": "process per request", "verdict": "limited",
        "summary": ("PHP-FPM: one process per request, nothing shared. Move slow work to a queue. Do not "
                    "introduce a worker server or an event loop without a project."),
        "evidence": ["no worker server or event loop in composer.json"],
        "allowed": allowed,
        "avoid": avoid,
    }


ANALYZERS = {
    "django": _concurrency_django,
    "fastapi": _concurrency_fastapi,
    "go": _concurrency_go,
    "java": _concurrency_java,
    "node": _concurrency_node,
    "laravel": _concurrency_php,
    "symfony": _concurrency_php,
    "php": _concurrency_php,
}


def concurrency(cwd=None, entry=None):
    """Return the concurrency readiness report of one stack entry (the primary by default)."""
    try:
        root = craft_state.host_root(cwd)
        if entry is None:
            found = detect(cwd)
            stack_id = primary(cwd, found)
            entry = next((item for item in found if item["id"] == stack_id),
                         {"id": stack_id, "dir": "", "evidence": "default"})
        data = pack(entry["id"])
        base = root / entry["dir"] if entry.get("dir") else root
        analyzer = ANALYZERS.get(entry["id"])
        report = analyzer(base) if analyzer else {
            "model": "unknown", "verdict": "not-ready", "summary": "No analyzer for this stack.",
            "evidence": [], "allowed": [], "avoid": []}
        concurrency_pack = data.get("concurrency") or {}
        report.update({
            "stack": entry["id"],
            "dir": entry.get("dir", ""),
            "skill": concurrency_pack.get("skill", ""),
            "note": concurrency_pack.get("note", ""),
            "to_change": ("Changing the concurrency model is the project route with Risk: high. design.md "
                          "covers the server, the drivers, the deployment, the failure modes, and a load "
                          "criterion with a number."),
        })
        return report
    except Exception as error:
        return {"stack": (entry or {}).get("id", ""), "model": "unknown", "verdict": "not-ready",
                "summary": "The analyzer failed: %s" % type(error).__name__, "evidence": [],
                "allowed": [], "avoid": [], "skill": ""}


def summary(cwd=None):
    """Return a small dict for status lines: stacks, primary, emoji, concurrency."""
    try:
        found = detect(cwd)
        primary_id = primary(cwd, found)
        data = pack(primary_id)
        report = concurrency(cwd)
        return {
            "primary": primary_id,
            "label": data.get("label", primary_id),
            "emoji": data.get("emoji", ""),
            "stacks": [{"id": item["id"], "dir": item["dir"], "emoji": pack(item["id"]).get("emoji", ""),
                        "label": pack(item["id"]).get("label", item["id"]), "evidence": item["evidence"]}
                       for item in found],
            "detected": bool(found),
            "concurrency": {"model": report.get("model"), "verdict": report.get("verdict"),
                            "skill": report.get("skill"), "summary": report.get("summary")},
        }
    except Exception:
        return {"primary": DEFAULT_STACK, "label": "Django", "emoji": "", "stacks": [], "detected": False,
                "concurrency": {}}
