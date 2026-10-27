#!/usr/bin/env python3
"""stack_selftest - prove the 0.7 machinery without a live session or network.

    python3 scripts/stack_selftest.py [--verbose]

Groups:
  stacks      detection of the five packs, a monorepo, and the overrides
  checks      the check commands each pack resolves for a repository
  concurrency the readiness verdicts: what each system is built for
  trace       criterion IDs found in Python, Go, Java, Kotlin, and TypeScript tests
  craft-check runner summaries and JUnit XML
  deciders    parsing, privacy, a council, and the OpenAI-compatible client
              against a local mock server
  jev floor   the concurrency lens routed from an added goroutine
  ui-state    the snapshot the craft mod draws, and the review records

Every repository is a throwaway directory. Exit 0 when every case passes.
"""

import http.server
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading

SCRIPTS = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
BIN = ROOT / "bin"
sys.path.insert(0, str(SCRIPTS))

import craft_stack  # noqa: E402
import craft_state  # noqa: E402
import deciders  # noqa: E402

VERBOSE = "--verbose" in sys.argv
results = []
temporary = []


def check(group, name, actual, expected):
    results.append({"group": group, "name": name, "actual": actual, "expected": expected,
                    "passed": actual == expected})


def repo(files):
    root = pathlib.Path(tempfile.mkdtemp(prefix="craft-stack-"))
    temporary.append(root)
    (root / ".git").mkdir()
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def run(name, arguments, cwd, environment=None):
    env = dict(os.environ)
    for key in ("CRAFT_STACK", "CRAFT_DECIDERS", "CRAFT_DECIDER_MODE", "CRAFT_JEV", "OPENROUTER_API_KEY"):
        env.pop(key, None)
    env.update(environment or {})
    finished = subprocess.run([sys.executable, str(BIN / name)] + arguments, cwd=str(cwd), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    return finished.returncode, finished.stdout.decode("utf-8", errors="replace")


def load_bin(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(BIN / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def ids(found):
    return ",".join(sorted("%s@%s" % (item["id"], item["dir"] or ".") for item in found))


# ---------------------------------------------------------------------------


def test_stacks():
    group = "stacks"
    django = repo({"manage.py": "", "requirements.txt": "Django==5.1\ndjangorestframework\n"})
    fastapi = repo({"pyproject.toml": '[project]\ndependencies = [\n  "fastapi>=0.115",\n  "asyncpg",\n]\n'})
    go = repo({"go.mod": "module x\n\ngo 1.24\n"})
    java = repo({"pom.xml": "<project/>", "mvnw": ""})
    node = repo({"package.json": '{"scripts":{"test":"vitest run"}}', "pnpm-lock.yaml": ""})
    mono = repo({"services/wallet/go.mod": "module w\n", "web/package.json": "{}",
                 "api/pyproject.toml": 'dependencies = ["fastapi"]\n'})
    both = repo({"manage.py": "", "requirements.txt": "django\nfastapi\n", "package.json": "{}"})
    laravel = repo({"artisan": "", "composer.json": '{"require":{"laravel/framework":"^11"}}', "package.json": "{}"})
    symfony = repo({"composer.json": '{"require":{"symfony/framework-bundle":"^7"}}'})
    php = repo({"composer.json": '{"require":{"slim/slim":"^4"}}'})
    nuxt = repo({"package.json": '{"dependencies":{"nuxt":"^4.0.0"}}',
                 "nuxt.config.ts": "export default defineNuxtConfig({})"})
    plain = repo({"README.md": "# nothing"})
    lookalike = repo({"requirements.txt": "django-environ\ndjangorestframework-simplejwt\n"})

    check(group, "manage.py is django", ids(craft_stack.detect(str(django))), "django@.")
    check(group, "fastapi in pyproject is fastapi", ids(craft_stack.detect(str(fastapi))), "fastapi@.")
    check(group, "artisan and laravel/framework beat the Vite package.json", ids(craft_stack.detect(str(laravel))),
          "laravel@.,node@.")
    check(group, "the root's primary is laravel, not node", craft_stack.primary(str(laravel)), "laravel")
    check(group, "symfony/framework-bundle is symfony", ids(craft_stack.detect(str(symfony))), "symfony@.")
    check(group, "any other composer.json is php", ids(craft_stack.detect(str(php))), "php@.")
    check(group, "go.mod is go", ids(craft_stack.detect(str(go))), "go@.")
    check(group, "pom.xml is java", ids(craft_stack.detect(str(java))), "java@.")
    check(group, "package.json is node", ids(craft_stack.detect(str(node))), "node@.")
    check(group, "nuxt dep and config are nuxt, not vue", ids(craft_stack.detect(str(nuxt))), "nuxt@.")
    check(group, "the nuxt pack lists only skills that exist",
          all((craft_stack.PLUGIN_ROOT / "skills" / name / "SKILL.md").is_file()
              for name in craft_stack.skills_for(str(nuxt), with_concurrency=False)), True)
    check(group, "a monorepo gets one stack per service", ids(craft_stack.detect(str(mono))),
          "fastapi@api,go@services/wallet,node@web")
    check(group, "one python pack per directory, by priority", ids(craft_stack.detect(str(both))), "django@.,node@.")
    check(group, "the root's highest priority is primary", craft_stack.primary(str(both)), "django")
    check(group, "nothing detected falls back to django", craft_stack.primary(str(plain)), "django")
    check(group, "django-environ alone is not django", ids(craft_stack.detect(str(lookalike))), "")
    owner = craft_stack.owner_of("services/wallet/internal/limit.go", str(mono))
    check(group, "the deepest stack directory owns a path", owner["id"] if owner else None, "go")
    owner = craft_stack.owner_of(str(mono / "web" / "src" / "a.ts"), str(mono))
    check(group, "an absolute path is owned too", owner["id"] if owner else None, "node")

    craft_stack.set_override(["go"], str(plain))
    check(group, "set overrides detection", ids(craft_stack.detect(str(plain))), "go@.")
    craft_stack.set_override([], str(plain))
    check(group, "unset brings detection back", ids(craft_stack.detect(str(plain))), "")
    os.environ["CRAFT_STACK"] = "java"
    check(group, "CRAFT_STACK wins", ids(craft_stack.detect(str(go))), "java@.")
    del os.environ["CRAFT_STACK"]

    globs = craft_stack.globs_for("views", str(go))
    check(group, "go adds its handler globs", "*_handler.go" in globs and "views.py" in globs, True)
    check(group, "test globs include *_test.go", "*_test.go" in craft_stack.test_spec(str(go))["globs"], True)
    code, out = run("craft-stack", ["--json"], mono)
    check(group, "craft-stack --json parses", (code, json.loads(out)["primary"]), (0, "fastapi"))
    code, out = run("craft-stack", ["for", "web/x.ts"], mono)
    check(group, "craft-stack for names the owner", "node" in out, True)
    code, out = run("craft-stack", ["lens", "query", "--paths", "services/wallet/a.go"], mono)
    check(group, "craft-stack lens prints the stack's notes", "Index evidence" in out and "go" in out, True)


def test_checks():
    group = "checks"
    node = repo({"package.json": json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."},
                                              "devDependencies": {"prettier": "3"}}),
                 "pnpm-lock.yaml": "", "tsconfig.json": "{}"})
    resolved = craft_stack.checks_for("node", str(node))
    check(group, "node: the package manager from the lockfile", resolved.get("tests"), "pnpm test")
    check(group, "node: lint from the script", resolved.get("lint"), "pnpm run lint")
    check(group, "node: prettier from the dependency", resolved.get("format"), "npx prettier --check .")
    check(group, "node: tsc when tsconfig.json exists", resolved.get("types"), "npx tsc --noEmit")
    java = repo({"pom.xml": "<plugin>spotless-maven-plugin</plugin>", "mvnw": ""})
    resolved = craft_stack.checks_for("java", str(java))
    check(group, "java: the wrapper wins", resolved.get("tests"), "./mvnw -q test")
    check(group, "java: spotless when configured", resolved.get("format"), "./mvnw -q spotless:check")
    check(group, "java: no checkstyle when not configured", "lint" in resolved, False)
    fastapi = repo({"pyproject.toml": "dependencies = ['fastapi']\n[tool.black]\n", "uv.lock": ""})
    resolved = craft_stack.checks_for("fastapi", str(fastapi))
    check(group, "fastapi: uv run when uv.lock exists", resolved.get("tests"), "uv run pytest -q")
    check(group, "fastapi: black when configured", resolved.get("format"), "black --check .")
    go = repo({"go.mod": "module x\n"})
    resolved = craft_stack.checks_for("go", str(go), "")
    check(group, "go: the race detector row", resolved.get("race"), "go test -race ./...")
    resolved = craft_stack.checks_for("go", str(go), "services/wallet")
    check(group, "a service directory is entered first", resolved.get("tests"), "cd services/wallet && go test ./...")


def verdict(files, stack_id):
    root = repo(files)
    return craft_stack.concurrency(str(root), {"id": stack_id, "dir": "", "evidence": "test"})["verdict"]


def test_concurrency():
    group = "concurrency"
    check(group, "django on gunicorn is not-ready",
          verdict({"manage.py": "", "Procfile": "web: gunicorn config.wsgi", "apps/views.py": "def get(self):\n  pass\n"},
                  "django"), "not-ready")
    check(group, "django on uvicorn with async views is limited",
          verdict({"manage.py": "", "Dockerfile": "CMD uvicorn config.asgi:application",
                   "apps/views.py": "async def get(request):\n  pass\n"}, "django"), "limited")
    async_app = ('@router.get("/a")\nasync def a():\n    return 1\n'
                 '@router.post("/b")\nasync def b():\n    return 2\n')
    check(group, "fastapi with async handlers and drivers is ready",
          verdict({"pyproject.toml": 'dependencies=["fastapi","asyncpg","httpx"]', "app/api/x.py": async_app}, "fastapi"),
          "ready")
    blocking = async_app + "import requests\nasync def c():\n    requests.get('http://x')\n"
    check(group, "fastapi with requests inside async is limited",
          verdict({"pyproject.toml": 'dependencies=["fastapi"]', "app/api/x.py": blocking}, "fastapi"), "limited")
    sync_app = '@app.get("/a")\ndef a():\n    return 1\n'
    check(group, "fastapi with def handlers is not-ready",
          verdict({"pyproject.toml": 'dependencies=["fastapi","psycopg2"]', "main.py": sync_app}, "fastapi"), "not-ready")
    check(group, "go with ctx is ready",
          verdict({"go.mod": "module x\ngo 1.24\n", "a.go": "func A(ctx context.Context) {}\n"}, "go"), "ready")
    check(group, "go with goroutines and no ctx is limited",
          verdict({"go.mod": "module x\n", "a.go": "func A() { go work() }\n"}, "go"), "limited")
    check(group, "spring mvc is limited", verdict({"pom.xml": "spring-boot-starter-web"}, "java"), "limited")
    check(group, "spring webflux is ready", verdict({"pom.xml": "spring-boot-starter-webflux"}, "java"), "ready")
    check(group, "virtual threads are ready",
          verdict({"pom.xml": "spring-boot-starter-web",
                   "src/main/resources/application.properties": "spring.threads.virtual.enabled=true"}, "java"), "ready")
    check(group, "node is ready", verdict({"package.json": "{}"}, "node"), "ready")

    ready = repo({"pyproject.toml": 'dependencies=["fastapi","asyncpg"]', "app/api/x.py": async_app})
    check(group, "a ready system loads its concurrency skill",
          "fastapi-async" in craft_stack.skills_for(str(ready)), True)
    sync = repo({"pyproject.toml": 'dependencies=["fastapi"]', "main.py": sync_app})
    check(group, "a not-ready system does not", "fastapi-async" in craft_stack.skills_for(str(sync)), False)
    code, _out = run("craft-stack", ["concurrency"], sync)
    check(group, "craft-stack concurrency exits 1 on not-ready", code, 1)


SPEC = """# SPEC: Mixed

Key: MIX · Route: task · Risk: low

## Acceptance criteria

| ID | Criterion | Class | Failure |
|---|---|---|---|
| MIX-1 | a | B | c |
| MIX-2 | a | B | c |
| MIX-3 | a | B | c |
| MIX-4 | a | B | c |
| MIX-5 | a | B | c |
| MIX-6 | a | B | c |
"""


def test_trace():
    group = "trace"
    root = repo({
        ".claude/specs/s/spec.md": SPEC,
        ".claude/specs/ACTIVE": "s\n",
        "go.mod": "module x\n",
        "package.json": "{}",
        "pom.xml": "<project/>",
        "tests/test_mix.py": 'def test_one():\n    """MIX-1: Given ..."""\n',
        "wallet/limit_test.go": ("package wallet\n\n// MIX-2: Given over the limit\nfunc TestLimit(t *testing.T) {\n"
                                 "\tt.Run(\"MIX-3 resets at midnight\", func(t *testing.T) {})\n}\n"),
        "src/test/java/x/KycTest.java": ("class KycTest {\n  @Test\n  @DisplayName(\"MIX-4: expired is refused\")\n"
                                         "  void expiredIsRefused() {}\n}\n"),
        "src/test/kotlin/x/PayTest.kt": "class PayTest {\n  @Test\n  fun `MIX-5 a payout is capped`() {}\n}\n",
        "web/pay.test.ts": "describe('pay', () => {\n  it('MIX-6: shows the error', () => {})\n  it('MIX-9: stray', () => {})\n})\n",
        "web/src/pay.ts": "// MIX-6 mentioned in source, not a test\n",
    })
    code, out = run("craft-spec", ["trace", "--json"], root)
    data = json.loads(out)
    criteria = data["criteria"]
    check(group, "every language found, exit 0", code, 0)
    check(group, "python docstring", criteria["MIX-1"], ["tests/test_mix.py::test_one"])
    check(group, "go comment above the test", criteria["MIX-2"], ["wallet/limit_test.go::TestLimit"])
    check(group, "go subtest name", criteria["MIX-3"], ["wallet/limit_test.go::TestLimit/MIX-3 resets at midnight"])
    check(group, "java DisplayName above the method", criteria["MIX-4"],
          ["src/test/java/x/KycTest.java::expiredIsRefused"])
    check(group, "kotlin backtick name", criteria["MIX-5"], ["src/test/kotlin/x/PayTest.kt::MIX-5 a payout is capped"])
    check(group, "typescript test title", criteria["MIX-6"], ["web/pay.test.ts::MIX-6: shows the error"])
    check(group, "an unknown ID in a test is an orphan", any("MIX-9" in item for item in data["orphans"]), True)
    snapshot = json.loads((root / ".claude" / "craft" / "trace.json").read_text())
    check(group, "trace.json is written for the board", snapshot["spec"], "s")


def test_craft_check():
    group = "craft-check"
    module = load_bin("craft-check")
    check(group, "pytest summary", module.summarize("== 2 failed, 40 passed in 1s ==\n").get("passed"), 40)
    check(group, "gotestsum summary", module.summarize("DONE 42 tests, 2 failures in 3s\n").get("failed"), 2)
    check(group, "maven summary uses the last line",
          module.summarize("Tests run: 3, Failures: 0, Errors: 0, Skipped: 0\nTests run: 42, Failures: 1, Errors: 0, Skipped: 2\n")
          .get("total"), 42)
    check(group, "jest summary", module.summarize("Tests:       1 failed, 41 passed, 42 total\n").get("passed"), 41)
    check(group, "the race detector is counted",
          module.summarize("WARNING: DATA RACE\nWARNING: DATA RACE\n--- FAIL: TestX\nFAIL\tpkg\n").get("races"), 2)
    check(group, "go test -race is the race label", module.guess_label("go test -race ./..."), "race")
    check(group, "./mvnw test is a test", module.guess_label("./mvnw -q test"), "tests")
    check(group, "gofmt is format", module.guess_label('test -z "$(gofmt -l .)"'), "format")
    check(group, "tsc is types", module.guess_label("npx tsc --noEmit"), "types")

    root = repo({"report.xml": ""})
    craft_state.start_session("task", cwd=str(root))
    junit = ('<testsuite><testcase classname="a" name="ok"/><testcase classname="a" name="bad">'
             '<failure message="expected 1, got 2">trace</failure></testcase><testcase name="s"><skipped/></testcase>'
             '</testsuite>')
    command = "printf '%s' > report.xml && exit 1" % junit
    code, out = run("craft-check", ["--junit", "report.xml", "--", command], root)
    check(group, "the exit code is the command's", code, 1)
    check(group, "junit counts are printed", "1 passed · 1 failed · 1 skipped · 3 total (junit)" in out, True)
    check(group, "the failing test is named", "a.bad — expected 1, got 2" in out, True)
    recorded = craft_state.checks(str(root))[-1]
    check(group, "the summary is recorded for the board", (recorded.get("summary") or {}).get("failed"), 1)


# ---------------------------------------------------------------------------
# Deciders
# ---------------------------------------------------------------------------


QUESTIONS = {
    "route": {"type": "choice", "instructions": "Route?", "criteria": {"quick": "q", "task": "t", "project": "p"}},
    "risk_high": {"type": "noul", "instructions": "Risky?"},
}


class MockChat(object):
    """A local OpenAI-compatible server. replies: a list of (status, content)."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.bodies = []
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                owner.bodies.append(json.loads(self.rfile.read(length).decode("utf-8")))
                status, content = owner.replies.pop(0) if owner.replies else (200, "{}")
                payload = {"model": "mock-model", "choices": [{"message": {"content": content}}],
                           "usage": {"total_tokens": 42}}
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                data = json.dumps({"data": [{"id": "a:free", "pricing": {"prompt": "0", "completion": "0"}},
                                            {"id": "b", "pricing": {"prompt": "0.000001", "completion": "0.000002"}}]})
                self.send_response(200)
                self.end_headers()
                self.wfile.write(data.encode("utf-8"))

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/v1" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


def test_deciders():
    group = "deciders"
    check(group, "json after a think block and a fence",
          deciders.extract_json('<think>{"x":1}</think>```json\n{"route": {"choice": "task"}}\n```'),
          {"route": {"choice": "task"}})
    answers = deciders.normalize({"route": {"choice": "task", "confidence": 0.8, "probabilities": {"task": 0.6, "quick": 0.3, "project": 0.3}},
                                  "risk_high": {"p": 1.4}}, QUESTIONS)
    check(group, "probabilities are normalized", round(answers["route"]["probabilities"]["task"], 2), 0.5)
    check(group, "a probability is clamped", answers["risk_high"]["noul"], 1.0)
    check(group, "an unknown choice is dropped", deciders.normalize({"route": "maybe"}, QUESTIONS), {})
    check(group, "a bare word answers a noul", deciders.normalize({"risk_high": "yes"}, QUESTIONS)["risk_high"]["noul"], 1.0)

    council, votes = deciders.combine_council({
        "a": (deciders.normalize({"route": {"choice": "task", "confidence": 0.9}, "risk_high": {"p": 0.2}}, QUESTIONS), {}),
        "b": (deciders.normalize({"route": {"choice": "task", "confidence": 0.7}, "risk_high": {"p": 0.6}}, QUESTIONS), {}),
        "c": (deciders.normalize({"route": {"choice": "project", "confidence": 0.6}, "risk_high": {"p": 0.7}}, QUESTIONS), {}),
    }, QUESTIONS)
    check(group, "the council picks the majority", council["route"]["choice"], "task")
    check(group, "agreement is counted", council["route"]["agreement"], "2/3")
    check(group, "confidence is the averaged probability", round(council["route"]["confidence"], 3), round((0.9 + 0.7 + 0.2) / 3, 3))
    check(group, "a noul is averaged", round(council["risk_high"]["noul"], 2), 0.5)
    check(group, "votes are kept per member", votes["c"]["route"], ["project", 0.6])

    private = {"send_request_text": False}
    shown = deciders.state_for(private, {"request": "hello", "paths": ["a"]})
    check(group, "send_request_text false keeps the text local", "request" in shown, False)
    shown = deciders.state_for({}, {"request": "TOKEN=abc123456789 sk-or-v1-abcdefgh1234 ok"})
    check(group, "secrets are redacted", "abc123456789" in shown["request"] or "abcdefgh1234" in shown["request"], False)
    check(group, "https is allowed", deciders.url_allowed("https://api.groq.com/openai/v1"), True)
    check(group, "http to this machine is allowed", deciders.url_allowed("http://localhost:11434/v1"), True)
    check(group, "http elsewhere is refused", deciders.url_allowed("http://example.com/v1"), False)

    good = '{"route": {"choice": "task", "confidence": 0.85}, "risk_high": {"p": 0.9}}'
    server = MockChat([(400, ""), (200, good)])
    try:
        data = {"type": "openai", "base_url": server.url, "model": "m", "local": True, "free": True}
        answers, meta = deciders.call_openai(data, QUESTIONS, {"request": "x"}, 5)
        check(group, "a 400 retries without response_format", "response_format" in server.bodies[-1], False)
        check(group, "the answer is read", answers["route"]["choice"], "task")
        check(group, "a free provider costs 0", meta["cost"], 0)
        models = deciders.discover({"providers": {"x": data}}, "x", only_free=True)
        check(group, "discover lists the free models", [model["id"] for model in models], ["a:free"])
    finally:
        server.close()

    first = MockChat([(500, ""), (500, "")])
    second = MockChat([(200, good)])
    try:
        config = {"mode": "first", "order": ["broken", "fine"], "providers": {
            "broken": {"type": "openai", "base_url": first.url, "model": "m", "local": True},
            "fine": {"type": "openai", "base_url": second.url, "model": "m", "local": True}}}
        answers, meta = deciders.ask(QUESTIONS, {"request": "x"}, config=config)
        check(group, "mode first moves past a failing provider", meta["provider"], "fine")
        check(group, "the failure is reported", "broken" in meta["failures"], True)
    finally:
        first.close()
        second.close()

    one = MockChat([(200, good)])
    two = MockChat([(200, '{"route": {"choice": "project", "confidence": 0.6}, "risk_high": {"p": 0.5}}')])
    three = MockChat([(500, ""), (500, "")])
    try:
        config = {"mode": "council", "council": ["one", "two", "three"], "min_council": 2, "providers": {
            "one": {"type": "openai", "base_url": one.url, "model": "m", "local": True},
            "two": {"type": "openai", "base_url": two.url, "model": "m", "local": True},
            "three": {"type": "openai", "base_url": three.url, "model": "m", "local": True}}}
        answers, meta = deciders.ask(QUESTIONS, {"request": "x"}, config=config)
        check(group, "a council answers with two of three", meta["members"], ["one", "two"])
        check(group, "a split council is not confident", answers["route"]["confidence"] < 0.7, True)
    finally:
        one.close()
        two.close()
        three.close()

    root = repo({})
    chat = MockChat([(200, good)])
    try:
        code, _out = run("craft-decide", ["set", "ollama", "base_url", chat.url], root)
        check(group, "craft-decide set writes the override", code, 0)
        run("craft-decide", ["use", "ollama"], root)
        run("craft-jev", ["on"], root)
        code, out = run("craft-jev", ["decide", "--stage", "route", "--request", "Add a column to wallets"], root)
        check(group, "craft-jev decide asks the chosen decider", "🦙 Ollama" in out, True)
        print(out) if VERBOSE else None
        check(group, "the floor still applies", "floor task" in out, True)
        code, out = run("craft-decide", ["status", "--json"], root)
        check(group, "status reports the order", json.loads(out)["order"], ["ollama"])
    finally:
        chat.close()


def test_jev_floor():
    group = "jev floor"
    root = repo({"go.mod": "module x\n", "worker.go": "package x\n"})
    subprocess.run(["git", "init", "-q"], cwd=str(root))
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "."], cwd=str(root))
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"], cwd=str(root))
    (root / "worker.go").write_text("package x\nfunc Run() {\n\tgo func() {}()\n}\n", encoding="utf-8")
    code, out = run("craft-jev", ["decide", "--stage", "review", "--json"], root)
    decision = json.loads(out)
    check(group, "an added goroutine routes the concurrency lens", "concurrency" in decision["items"]["lenses"]["value"], True)
    code, out = run("craft-jev", ["decide", "--stage", "route", "--request", "make the payouts parallel", "--json"], root)
    decision = json.loads(out)
    check(group, "a parallel request forces at least task", decision["items"]["route"]["floor"], "task")
    check(group, "and loads the concurrency skill first", decision["items"]["stack_skills"]["value"][0], "concurrency")


def test_ui_state():
    group = "ui-state"
    root = repo({".claude/specs/s/spec.md": SPEC.replace("Risk: low", "Risk: high"),
                 ".claude/specs/s/tasks.md": "- [x] T1 — a\n- [ ] T2 — b\n",
                 ".claude/specs/ACTIVE": "s\n", "go.mod": "module x\n"})
    craft_state.start_session("task", cwd=str(root), spec="s")
    craft_state.record_check("craft-spec trace", 0, cwd=str(root), label="trace")
    craft_state.record_check("go test ./...", 0, cwd=str(root), label="tests", summary={"passed": 3, "failed": 0})
    craft_state.record_check("go test -race ./...", 1, cwd=str(root), label="race")
    code, out = run("craft-session", ["record-finding", "--severity", "High", "--lens", "logic",
                                      "--where", "a.go:1", "--title", "x"], root)
    check(group, "record-finding gets an id", "F1" in out, True)
    run("craft-session", ["record-review", "--lenses", "spec,style", "--decision", "APPROVE"], root)
    code, out = run("craft-ui-state", [], root)
    data = json.loads(out)
    check(group, "the stack is go", data["stack"]["primary"], "go")
    check(group, "six criteria are read", len(data["spec"]["criteria"]), 6)
    check(group, "two tasks are read", [task["done"] for task in data["spec"]["tasks"]], [True, False])
    check(group, "a failed race keeps Gate A shut", (data["gate_a"]["passed"], data["gate_a"]["total"], data["gate_a"]["green"]),
          (2, 3, False))
    check(group, "a proposed finding keeps Gate B in review", data["gate_b"]["state"], "in review")
    run("craft-session", ["finding", "F1", "--state", "rejected"], root)
    data = json.loads(run("craft-ui-state", [], root)[1])
    check(group, "a rejected finding lets an approved round go green", data["gate_b"]["state"], "green")
    run("craft-session", ["record-finding", "--severity", "Critical", "--title", "y", "--state", "confirmed"], root)
    data = json.loads(run("craft-ui-state", [], root)[1])
    check(group, "a confirmed critical requests changes", data["gate_b"]["state"], "changes requested")


def report():
    failed = [item for item in results if not item["passed"]]
    current = None
    for item in results:
        if not VERBOSE and item["passed"]:
            continue
        if item["group"] != current:
            current = item["group"]
            print("\n%s" % current)
        mark = "PASS" if item["passed"] else "FAIL"
        detail = "" if item["passed"] and not VERBOSE else "  got %r, expected %r" % (item["actual"], item["expected"])
        print("  %s  %s%s" % (mark, item["name"], detail if not item["passed"] else ""))
    print("\n%d passed, %d failed" % (len(results) - len(failed), len(failed)))
    return 1 if failed else 0


def main():
    try:
        for test in (test_stacks, test_checks, test_concurrency, test_trace, test_craft_check,
                     test_deciders, test_jev_floor, test_ui_state):
            try:
                test()
            except Exception as error:  # a crashing group is a failing group
                check(test.__name__, "ran without an exception", "%s: %s" % (type(error).__name__, error), "no exception")
        return report()
    finally:
        for root in temporary:
            shutil.rmtree(str(root), ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
