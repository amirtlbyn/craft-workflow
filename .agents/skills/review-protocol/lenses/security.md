# Lens: security — application security, and nothing else

- **Ceiling:** Critical
- **Minimum confidence:** 0.5
- **Reads:** the diff, the touched applications' `README.ai.md`, and the
  authentication, authorization, and permission modules. No standards.

Not this lens's, even when they feel security-adjacent: balance arithmetic,
freeze and unfreeze pairing, ledger consistency, idempotency of financial
operations, and races that cost money rather than access. Those are `logic`.

**Other stacks.** The items below name Django constructs. On another stack, run
`bin/craft-stack lens security --paths <changed paths>` and apply its notes in their
place.

## High or Critical

- **Injection** — SQL through raw queries, `.extra()`, `RawSQL`, or f-string SQL.
  Command and template injection. Unsafe `eval`, `exec`, `pickle`, `yaml.load`.
- **Authentication or authorization bypass** — an entry point reachable without
  its permission. A missing object-level check. A permission check dropped,
  weakened, or cached across a state change.
- **Secret leakage** — credentials, tokens, keys, or signing material in code,
  logs, error responses, serializer output, or admin displays.
- **SSRF** — a user-influenced URL, host, or callback fetched server-side.
- **Crypto and signature misuse** — a changed signing payload or order, a
  weakened or home-rolled algorithm, a predictable nonce, a non-constant-time
  comparison of a secret.
- **Session, OTP, and login weakness** — replay, no throttle, account
  enumeration, an OTP checked against a stale replica read.
- **Unsafe deserialization or file handling** — unbounded upload, path
  traversal, archive extraction outside a sandbox.

Medium or Low: defence in depth, hardening, a missing log on a security action,
a broad exception swallow around a permission check.

## Checklist — answer every item

1. **Authentication** — every new or changed entry point requires what it needs.
2. **Authorization** — the permission check is present, at the right layer, and
   re-evaluated after any state change.
3. **Object-level access** — every lookup is scoped to the requesting user, or
   justified as public.
4. **Access decorator** — every new HTTP view carries the repository's mandatory
   access decorator (`@api_access_required` here, CI-enforced).
5. **Injection** — every query is parameterized, and no dynamic execution path
   takes user input.
6. **Secrets** — the diff adds, logs, or returns no credential or signing material.
7. **Outbound requests** — every user-influenced target is validated, and every
   outbound call sets an explicit timeout.
8. **Input at the boundary** — untrusted input is validated where it enters.
9. **Rate limiting** — a new authentication, OTP, or enumeration-capable
   endpoint has a throttle.
10. **Admin surface** — a new admin action or display exposes nothing beyond its role.
