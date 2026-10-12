#!/usr/bin/env python3
"""jev_client - the shared OpenRouter client for the optional Jev layer.

bin/craft-jev (routing decisions) and scripts/jev_approve.py (the tool-call
approval hook) both use it. Standard library only: json, os, pathlib, time,
urllib.

Where each setting comes from, first match wins:

    endpoint   CRAFT_JEV_URL  ->  .claude/craft/jev.json "endpoint"  ->  config/jev.json
    model      CRAFT_JEV_MODEL -> .claude/craft/jev.json "model"     ->  config/jev.json
    switch     CRAFT_JEV       -> .claude/craft/jev.json "enabled"
    approval   CRAFT_JEV_APPROVE -> .claude/craft/jev.json "approve"
    key        OPENROUTER_API_KEY -> ~/.config/craft-workflow/openrouter.key

The per-repository file never holds the key.
"""

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import craft_state  # noqa: E402

PLUGIN_ROOT = craft_state.PLUGIN_ROOT
CONFIG_PATH = PLUGIN_ROOT / "config" / "jev.json"
STATE_FILE = "jev.json"
KEY_FILE = pathlib.Path.home() / ".config" / "craft-workflow" / "openrouter.key"
OVERRIDABLE = ("endpoint", "model")
TRUE_WORDS = ("on", "1", "true", "yes")
FALSE_WORDS = ("off", "0", "false", "no")


def load_config():
    """Return config/jev.json as a dict. {} when it is missing or broken."""
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def state_path(cwd=None):
    return craft_state.state_path(STATE_FILE, cwd)


def read_state(cwd=None):
    """Return the per-repository Jev settings. {} on any problem."""
    try:
        data = json.loads(state_path(cwd).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(changes, cwd=None):
    """Merge changes into the per-repository settings. None deletes a key."""
    try:
        data = read_state(cwd)
        for key, value in changes.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        data["updated_at"] = craft_state.now()
        path = state_path(cwd)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def _switch(environment_name, state_key, cwd):
    override = str(os.environ.get(environment_name, "")).strip().lower()
    if override in TRUE_WORDS:
        return True
    if override in FALSE_WORDS:
        return False
    return bool(read_state(cwd).get(state_key))


def is_enabled(cwd=None):
    """Return True when Jev is on for this repository."""
    return _switch("CRAFT_JEV", "enabled", cwd)


def is_approve_enabled(cwd=None):
    """Return True when Jev may approve tool calls. It needs Jev on as well."""
    return is_enabled(cwd) and _switch("CRAFT_JEV_APPROVE", "approve", cwd)


def set_enabled(enabled, cwd=None):
    return write_state({"enabled": bool(enabled)}, cwd)


def api_key():
    """Return (key, source). key is '' when none is found."""
    key = str(os.environ.get("OPENROUTER_API_KEY", "")).strip()
    if key:
        return key, "OPENROUTER_API_KEY"
    try:
        key = KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key, str(KEY_FILE)
    except OSError:
        pass
    return "", ""


def setting(name, config, cwd=None):
    """Return (value, source) for endpoint or model."""
    environment_name = {"endpoint": "CRAFT_JEV_URL", "model": "CRAFT_JEV_MODEL"}[name]
    value = str(os.environ.get(environment_name, "")).strip()
    if value:
        return value, environment_name
    value = str(read_state(cwd).get(name, "")).strip()
    if value:
        return value, ".claude/craft/jev.json"
    return str(config.get(name, "")).strip(), "config/jev.json"


def effective_config(cwd=None):
    """Return config/jev.json with the model resolved for this repository."""
    config = load_config()
    config["model"] = model(config, cwd)
    return config


def endpoint(config, cwd=None):
    return setting("endpoint", config, cwd)[0]


def model(config, cwd=None):
    return setting("model", config, cwd)[0] or "typesafe/jev-1.13"


class JevError(Exception):
    """The call to Jev did not produce usable answers."""


def call_jev(config, questions, state, key, url):
    """POST one Decisions request, trying the fallback endpoints on 404 or 405."""
    urls = [url]
    # Fallbacks apply only to the default endpoint. An endpoint the developer
    # chose is used alone, so a typo fails loudly instead of silently moving on.
    if url == str(config.get("endpoint", "")).strip():
        urls += [
            other for other in (config.get("fallback_endpoints") or [])
            if isinstance(other, str) and other and other != url
        ]
    last = None
    for candidate in urls:
        try:
            answers, meta = call_endpoint(config, questions, state, key, candidate)
            meta["endpoint"] = candidate
            return answers, meta
        except JevError as error:
            last = error
            if str(error) not in ("HTTP 404", "HTTP 405"):
                raise
    raise last or JevError("no endpoint configured")


def call_endpoint(config, questions, state, key, url):
    """POST one Decisions request to one URL. Return (answers, meta). Raise JevError."""
    body = {
        "model": config.get("model", "typesafe/jev-1.13"),
        "state": state,
        "questions": questions,
    }
    if isinstance(config.get("provider"), dict):
        body["provider"] = config["provider"]
    data = json.dumps(body).encode("utf-8")
    timeout = float(config.get("timeout_seconds", 6))
    attempts = 1 + max(0, int(config.get("retries", 1)))
    last_error = "no attempt made"
    for attempt in range(attempts):
        if attempt:
            time.sleep(0.5 * (2 ** (attempt - 1)))
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Authorization": "Bearer %s" % key,
                "Content-Type": "application/json",
                "X-Title": "craft-workflow",
            },
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            last_error = "HTTP %d" % error.code
            if error.code in (429, 500, 502, 503, 524, 529):
                continue
            raise JevError(last_error)
        except (urllib.error.URLError, OSError, ValueError) as error:
            last_error = "%s: %s" % (type(error).__name__, getattr(error, "reason", error))
            continue
        answers = payload.get("answers") if isinstance(payload, dict) else None
        if not isinstance(answers, dict):
            raise JevError("the response holds no answers")
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        return answers, {
            "latency_ms": int((time.time() - started) * 1000),
            "cost": usage.get("cost"),
            "provider": payload.get("provider"),
            "model": payload.get("model") or body["model"],
            "attempts": attempt + 1,
        }
    raise JevError(last_error)


def noul_probability(answer):
    """Return the probability of true for a noul answer, or None."""
    if not isinstance(answer, dict):
        return None
    value = answer.get("noul")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def choice_of(answer):
    """Return (choice, confidence) for a choice answer, or (None, 0.0)."""
    if not isinstance(answer, dict):
        return None, 0.0
    choice = answer.get("choice")
    confidence = answer.get("confidence")
    if not isinstance(confidence, (int, float)):
        probabilities = answer.get("probabilities") or {}
        confidence = probabilities.get(choice) if isinstance(probabilities, dict) else None
    return (choice if isinstance(choice, str) else None), float(confidence or 0.0)


