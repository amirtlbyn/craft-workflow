#!/usr/bin/env python3
"""deciders - ask the typed questions of config/jev.json to any decider provider.

Jev answers typed questions natively. Every other provider is a chat model
asked for one JSON object that holds the same answers, in the same shape Jev
returns them:

    noul    {"noul": 0.83}
    choice  {"choice": "task", "confidence": 0.81, "probabilities": {...}}

so bin/craft-jev's combine() and scripts/jev_approve.py read every provider the
same way, and the rules floor applies to all of them.

Two modes, set in config/deciders.json or .claude/craft/deciders.json:

    first     try the providers of "order" in turn, use the first that answers
    council   ask every provider of "council" in parallel, and average them

A council's choice is the argmax of the members' averaged probabilities, and
its confidence is that average. A split council therefore comes out below the
confidence threshold, the decision is "undecided", and Claude decides, never
below the rules floor. "agreement" says how many members picked the winner.

Privacy, per provider: send_request_text false keeps the request text local
(the paths and counts still go). Secrets in the state are redacted before any
call. File contents never go.

Standard library only: json, os, re, subprocess, threading, time, urllib.
"""

import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402
import jev_client  # noqa: E402

CONFIG_PATH = craft_state.PLUGIN_ROOT / "config" / "deciders.json"
STATE_FILE = "deciders.json"
KEY_DIRECTORY = pathlib.Path.home() / ".config" / "craft-workflow"
MODES = ("first", "council")
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "[::1]")
SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[a-z0-9._\-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)((?:password|passwd|secret|token|api[_-]?key)\s*[=:]\s*)(?!<redacted)[^\s'\"&]+"),
    re.compile(r"(://[^/\s:@]+:)[^@\s/]+@"),
)
SYSTEM_PROMPT = (
    "You are a decision function inside a software engineering workflow. You read a STATE and a set of typed "
    "QUESTIONS, and you answer every question. You never explain and never write prose. You output exactly one "
    "JSON object and nothing else. For a question of type noul, answer {\"p\": <probability from 0 to 1 that the "
    "answer is true>}. For a question of type choice, answer {\"choice\": <one key of its criteria>, "
    "\"confidence\": <0 to 1>, \"probabilities\": {<each key>: <0 to 1>, summing to 1}}. Use the criteria text to "
    "decide. Be calibrated: 0.5 means you do not know."
)


class DeciderError(jev_client.JevError):
    """No provider produced usable answers."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _deep_merge(base, override):
    merged = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def read_override(cwd=None):
    try:
        data = json.loads(craft_state.state_path(STATE_FILE, cwd).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_override(changes, cwd=None):
    """Deep-merge changes into .claude/craft/deciders.json. None deletes a key. True on success."""
    try:
        data = read_override(cwd)

        def apply(target, patch):
            for key, value in patch.items():
                if value is None:
                    target.pop(key, None)
                elif isinstance(value, dict) and isinstance(target.get(key), dict):
                    apply(target[key], value)
                else:
                    target[key] = value

        apply(data, changes)
        data["updated_at"] = craft_state.now()
        path = craft_state.state_path(STATE_FILE, cwd)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def load(cwd=None):
    """Return config/deciders.json merged with the repository's override. Never raises."""
    try:
        base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        base = {}
    if not isinstance(base, dict):
        base = {}
    base.setdefault("mode", "first")
    base.setdefault("order", ["jev"])
    base.setdefault("providers", {"jev": {"type": "jev", "key_env": "OPENROUTER_API_KEY",
                                           "key_file": "openrouter.key", "send_request_text": True}})
    merged = _deep_merge(base, read_override(cwd))
    environment_mode = str(os.environ.get("CRAFT_DECIDER_MODE", "")).strip().lower()
    if environment_mode in MODES:
        merged["mode"] = environment_mode
    environment_order = str(os.environ.get("CRAFT_DECIDERS", "")).strip()
    if environment_order:
        names = [name.strip() for name in environment_order.split(",") if name.strip()]
        merged["order"] = names
        merged["council"] = names
    return merged


def provider(config, name):
    data = (config.get("providers") or {}).get(name)
    return dict(data, name=name) if isinstance(data, dict) else None


def chain(config, purpose="decide"):
    """Return the provider names to ask, in order, for a purpose."""
    if purpose == "approve":
        names = config.get("approve_providers") or ["jev"]
    elif config.get("mode") == "council":
        names = config.get("council") or config.get("order") or ["jev"]
    else:
        names = config.get("order") or ["jev"]
    return [name for name in names if provider(config, name)]


def api_key(data):
    """Return (key, source) for a provider. ('', '') when it needs none or none is found."""
    if data.get("type") == "jev":
        return jev_client.api_key()
    environment_name = str(data.get("key_env") or "")
    if environment_name:
        value = str(os.environ.get(environment_name, "")).strip()
        if value:
            return value, environment_name
    key_file = data.get("key_file")
    if key_file:
        path = KEY_DIRECTORY / str(key_file)
        try:
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value, str(path)
        except OSError:
            pass
    return "", ""


def base_url(data):
    """Return the provider's base URL with ${VAR} filled from the environment."""
    url = str(data.get("base_url") or "")
    return re.sub(r"\$\{(\w+)\}", lambda match: os.environ.get(match.group(1), ""), url).rstrip("/")


def url_allowed(url):
    """https anywhere; http only to this machine."""
    if url.startswith("https://"):
        return True
    if url.startswith("http://"):
        host = url[len("http://"):].split("/", 1)[0].rsplit(":", 1)[0]
        return host in LOCAL_HOSTS
    return False


def readiness(data):
    """Return (ready, why) without making a request."""
    kind = data.get("type")
    if kind == "jev":
        key, _source = jev_client.api_key()
        return (bool(key), "key found" if key else "no OpenRouter key")
    if kind == "claude-cli":
        found = any(os.access(os.path.join(directory, "claude"), os.X_OK)
                    for directory in os.environ.get("PATH", "").split(os.pathsep) if directory)
        return (found, "claude on PATH" if found else "claude is not on PATH")
    if kind == "openai":
        missing = [name for name in re.findall(r"\$\{(\w+)\}", str(data.get("base_url") or ""))
                   if not os.environ.get(name)]
        if missing:
            return (False, "set %s" % ", ".join(missing))
        url = base_url(data)
        if not url:
            return (False, "no base_url")
        if not url_allowed(url):
            return (False, "base_url must be https, or http on this machine")
        if not data.get("model"):
            return (False, "no model set")
        if data.get("local"):
            return (True, "local, reachability checked on call")
        key, _source = api_key(data)
        return (bool(key), "key found" if key else "no key in %s" % (data.get("key_env") or "its key file"))
    return (False, "unknown type %r" % kind)


def available(config, purpose="decide"):
    """Return the names in the chain that look ready."""
    return [name for name in chain(config, purpose) if readiness(provider(config, name))[0]]


# ---------------------------------------------------------------------------
# What a provider is sent
# ---------------------------------------------------------------------------


def redact(value):
    """Return value with secret-looking substrings replaced, recursively."""
    if isinstance(value, str):
        text = value
        for pattern in SECRET_PATTERNS:
            text = pattern.sub(lambda match: (match.group(1) if match.groups() else "") + "<redacted>", text)
        return text
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def state_for(data, state):
    """Return the state a provider may see."""
    if not isinstance(state, dict):
        return redact(state)
    shown = dict(state)
    if not data.get("send_request_text", True):
        shown.pop("request", None)
    return redact(shown)


# ---------------------------------------------------------------------------
# Parsing a chat model's answer
# ---------------------------------------------------------------------------


def extract_json(text):
    """Return the first JSON object in text. Raise ValueError when there is none."""
    text = re.sub(r"(?s)<think>.*?</think>", "", text or "")
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:index + 1])
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    raise ValueError("no JSON object in the reply")


def _probability(value):
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return min(1.0, max(0.0, float(value)))
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes"):
            return 1.0
        if lowered in ("false", "no"):
            return 0.0
        try:
            return min(1.0, max(0.0, float(lowered)))
        except ValueError:
            return None
    return None


def normalize(raw, questions):
    """Return {name: Jev-shaped answer} for the questions a raw reply answers."""
    if isinstance(raw, dict) and isinstance(raw.get("answers"), dict):
        raw = raw["answers"]
    answers = {}
    if not isinstance(raw, dict):
        return answers
    for name, question in questions.items():
        value = raw.get(name)
        kind = (question or {}).get("type")
        if kind == "noul":
            if isinstance(value, dict):
                value = next((value[key] for key in ("p", "probability", "noul", "value", "answer") if key in value),
                             None)
            probability = _probability(value)
            if probability is not None:
                answers[name] = {"noul": probability}
        elif kind == "choice":
            keys = list(((question or {}).get("criteria") or {}).keys())
            choice = value.get("choice") if isinstance(value, dict) else value
            if not isinstance(choice, str) or choice not in keys:
                continue
            probabilities = {}
            if isinstance(value, dict) and isinstance(value.get("probabilities"), dict):
                for key in keys:
                    probability = _probability(value["probabilities"].get(key))
                    if probability is not None:
                        probabilities[key] = probability
            total = sum(probabilities.values())
            if total > 0:
                probabilities = {key: probability / total for key, probability in probabilities.items()}
            confidence = _probability(value.get("confidence")) if isinstance(value, dict) else None
            if confidence is None:
                confidence = probabilities.get(choice, 0.5)
            if not probabilities:
                rest = (1.0 - confidence) / max(1, len(keys) - 1)
                probabilities = {key: (confidence if key == choice else rest) for key in keys}
            answers[name] = {"choice": choice, "confidence": confidence, "probabilities": probabilities}
    return answers


# ---------------------------------------------------------------------------
# Provider calls
# ---------------------------------------------------------------------------


def _post_json(url, body, headers, timeout):
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers=dict({"Content-Type": "application/json"}, **headers))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def call_openai(data, questions, state, timeout):
    """Ask an OpenAI-compatible chat endpoint. Return (answers, meta). Raise DeciderError."""
    url = base_url(data)
    if not url_allowed(url):
        raise DeciderError("base_url must be https, or http on this machine")
    key, _source = api_key(data)
    headers = dict(data.get("headers") or {})
    if key:
        headers["Authorization"] = "Bearer %s" % key
    user = json.dumps({"STATE": state, "QUESTIONS": questions,
                       "ANSWER": "one JSON object whose keys are the question names"}, ensure_ascii=False)
    body = {
        "model": data.get("model"),
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": int(data.get("max_tokens", 800)),
        "response_format": {"type": "json_object"},
    }
    started = time.time()
    payload = None
    last_error = ""
    for attempt in range(2):
        try:
            payload = _post_json(url + "/chat/completions", body, headers, timeout)
            break
        except urllib.error.HTTPError as error:
            last_error = "HTTP %d" % error.code
            if error.code in (400, 422) and "response_format" in body:
                body.pop("response_format")       # a model without JSON mode: ask in the prompt alone
                continue
            if error.code in (429, 500, 502, 503) and attempt == 0:
                time.sleep(0.5)
                continue
            raise DeciderError(last_error)
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise DeciderError("%s: %s" % (type(error).__name__, getattr(error, "reason", error)))
    if payload is None:
        raise DeciderError(last_error or "no answer")
    try:
        message = payload["choices"][0]["message"]
        text = message.get("content") or ""
        if not text.strip():
            text = message.get("reasoning") or message.get("reasoning_content") or ""
        answers = normalize(extract_json(text), questions)
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise DeciderError("unusable reply: %s" % error)
    if not answers:
        raise DeciderError("the reply answered none of the questions")
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return answers, {
        "latency_ms": int((time.time() - started) * 1000),
        "model": payload.get("model") or data.get("model"),
        "cost": usage.get("cost", 0 if data.get("free") else None),
        "tokens": usage.get("total_tokens"),
    }


def call_claude(data, questions, state, timeout):
    """Ask Claude through `claude -p --safe-mode`. Return (answers, meta). Raise DeciderError."""
    prompt = SYSTEM_PROMPT + "\n\n" + json.dumps({"STATE": state, "QUESTIONS": questions}, ensure_ascii=False)
    started = time.time()
    try:
        completed = subprocess.run(
            ["claude", "-p", "--safe-mode", "--model", str(data.get("model") or "haiku"), "--output-format", "json"],
            input=prompt.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=max(timeout, 30), env=dict(os.environ, CRAFT_HOOKS="off"),
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise DeciderError("claude -p failed: %s" % type(error).__name__)
    if completed.returncode != 0:
        raise DeciderError("claude -p exited %d" % completed.returncode)
    try:
        envelope = json.loads(completed.stdout.decode("utf-8", errors="replace"))
        answers = normalize(extract_json(envelope.get("result", "")), questions)
    except (ValueError, AttributeError) as error:
        raise DeciderError("unusable reply: %s" % error)
    if not answers:
        raise DeciderError("the reply answered none of the questions")
    return answers, {"latency_ms": int((time.time() - started) * 1000), "model": data.get("model"),
                     "cost": envelope.get("total_cost_usd"), "uses_plan": True}


def call_provider(config, name, questions, state, jev_config=None, cwd=None, timeout=None):
    """Ask one provider. Return (answers, meta). Raise DeciderError or JevError."""
    data = provider(config, name)
    if data is None:
        raise DeciderError("unknown provider %s" % name)
    timeout = float(timeout or data.get("timeout_seconds") or config.get("timeout_seconds", 8))
    shown = state_for(data, state)
    kind = data.get("type")
    if kind == "jev":
        jev_config = jev_config or jev_client.effective_config(cwd)
        key, _source = jev_client.api_key()
        if not key:
            raise DeciderError("no API key")
        answers, meta = jev_client.call_jev(jev_config, questions, shown, key, jev_client.endpoint(jev_config, cwd))
    elif kind == "openai":
        answers, meta = call_openai(data, questions, shown, timeout)
    elif kind == "claude-cli":
        answers, meta = call_claude(data, questions, shown, timeout)
    else:
        raise DeciderError("unknown provider type %r" % kind)
    meta = dict(meta, provider=name, label=data.get("label", name))
    return answers, meta


# ---------------------------------------------------------------------------
# Asking: first, or a council
# ---------------------------------------------------------------------------


def combine_council(results, questions):
    """Average the members' answers. Return (answers, votes)."""
    answers = {}
    votes = {}
    for name, (member_answers, _meta) in results.items():
        votes[name] = {}
        for question, answer in member_answers.items():
            if "noul" in answer:
                votes[name][question] = round(answer["noul"], 3)
            elif "choice" in answer:
                votes[name][question] = [answer["choice"], round(answer.get("confidence", 0.0), 3)]
    for question, spec in questions.items():
        kind = (spec or {}).get("type")
        members = [result[0].get(question) for result in results.values() if result[0].get(question)]
        if not members:
            continue
        if kind == "noul":
            values = [member["noul"] for member in members if "noul" in member]
            if values:
                answers[question] = {"noul": sum(values) / len(values), "members": len(values)}
        elif kind == "choice":
            keys = list(((spec or {}).get("criteria") or {}).keys())
            average = {key: 0.0 for key in keys}
            for member in members:
                for key in keys:
                    average[key] += float((member.get("probabilities") or {}).get(key, 0.0))
            average = {key: value / len(members) for key, value in average.items()}
            winner = max(keys, key=lambda key: average[key])
            agreement = sum(1 for member in members if member.get("choice") == winner)
            answers[question] = {"choice": winner, "confidence": average[winner], "probabilities": average,
                                 "agreement": "%d/%d" % (agreement, len(members))}
    return answers, votes


def ask(questions, state, cwd=None, purpose="decide", jev_config=None, timeout=None, config=None):
    """Ask the configured deciders. Return (answers, meta). Raise DeciderError when none answers.

    meta: mode, providers asked, the provider (or council) that answered,
    latency_ms, cost, failures, and for a council the votes of each member.
    """
    config = config or load(cwd)
    names = chain(config, purpose)
    if not names:
        raise DeciderError("no decider is configured")
    mode = "first" if purpose == "approve" else config.get("mode", "first")
    failures = {}
    started = time.time()

    if mode != "council" or len(names) == 1:
        for name in names:
            ready, why = readiness(provider(config, name))
            if not ready:
                failures[name] = why
                continue
            try:
                answers, meta = call_provider(config, name, questions, state, jev_config, cwd, timeout)
            except jev_client.JevError as error:
                failures[name] = str(error)
                continue
            meta.update({"mode": "first", "asked": names, "failures": failures})
            return answers, meta
        raise DeciderError("no decider answered: " + "; ".join("%s: %s" % item for item in failures.items())
                           if failures else "no decider answered")

    results = {}
    lock = threading.Lock()

    def worker(name):
        ready, why = readiness(provider(config, name))
        if not ready:
            with lock:
                failures[name] = why
            return
        try:
            outcome = call_provider(config, name, questions, state, jev_config, cwd, timeout)
            with lock:
                results[name] = outcome
        except jev_client.JevError as error:
            with lock:
                failures[name] = str(error)

    threads = [threading.Thread(target=worker, args=(name,), daemon=True) for name in names]
    for thread in threads:
        thread.start()
    deadline = time.time() + float(timeout or config.get("timeout_seconds", 8)) + 2
    for thread in threads:
        thread.join(max(0.0, deadline - time.time()))
    with lock:
        finished = dict(results)
        failed = dict(failures)
    for name in names:
        if name not in finished and name not in failed:
            failed[name] = "timed out"
    needed = min(int(config.get("min_council", 2)), len(names))
    if len(finished) < max(1, needed):
        raise DeciderError("the council had %d answer(s), %d needed: %s" % (
            len(finished), needed, "; ".join("%s: %s" % item for item in failed.items())))
    answers, votes = combine_council(finished, questions)
    costs = [meta.get("cost") for _answers, meta in finished.values() if isinstance(meta.get("cost"), (int, float))]
    return answers, {
        "mode": "council",
        "asked": names,
        "provider": "council",
        "members": sorted(finished),
        "votes": votes,
        "failures": failed,
        "latency_ms": int((time.time() - started) * 1000),
        "cost": sum(costs) if costs else None,
        "model": "council of %d" % len(finished),
        "attempts": 1,
    }


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover(config, name, only_free=False, timeout=10):
    """Return [{"id", "free", "context"}] the provider serves. Raise DeciderError."""
    data = provider(config, name)
    if data is None:
        raise DeciderError("unknown provider %s" % name)
    if data.get("type") == "jev":
        data = dict(data, base_url="https://openrouter.ai/api/v1")
    if data.get("type") == "claude-cli":
        return [{"id": model, "free": False, "context": None} for model in ("haiku", "sonnet", "opus")]
    url = base_url(data)
    if not url_allowed(url):
        raise DeciderError("base_url must be https, or http on this machine")
    key, _source = api_key(data)
    headers = {"Authorization": "Bearer %s" % key} if key else {}
    request = urllib.request.Request(url + "/models", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise DeciderError("HTTP %d" % error.code)
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise DeciderError("%s: %s" % (type(error).__name__, getattr(error, "reason", error)))
    rows = payload.get("data") if isinstance(payload, dict) else payload
    models = []
    for row in rows or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        pricing = row.get("pricing") or {}
        free = (str(row["id"]).endswith(":free") or row["id"] == "openrouter/free"
                or (pricing and str(pricing.get("prompt")) in ("0", "0.0") and str(pricing.get("completion")) in ("0", "0.0"))
                or bool(data.get("free")) and not pricing)
        if only_free and not free:
            continue
        models.append({"id": row["id"], "free": bool(free), "context": row.get("context_length")})
    return sorted(models, key=lambda model: model["id"])
