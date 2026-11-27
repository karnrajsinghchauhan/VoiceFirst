# R2: Security and privacy review (ASVS L2, DPDP 2023 + Rules 2025, CERT-In 2022)

R2, branch v3/pitch-pack, 27 Nov 2026. `pytest tests/api tests/admin tests/mcp tests/demo`: 73 passed.

## Verdict
Access control is sound: explicit RBAC, hashed 256-bit API keys compared in constant time, full OIDC checks, forced RLS, a production validator that rejects dev secrets, and an allowlisted, CSRF-protected console proxy. The gaps are in the privacy and regulatory plumbing that the security pack and DPA describe as done. Retention and erasure leave raw phone numbers and booking payloads in place forever. Breach clocks never alert, ICT-log retention exists only as a config number, and production would ship a placeholder grievance contact. These four block a pilot; none needs a redesign.

## Critical
None found.

## High

**H1. Retention purge and erasure miss most of the personal data**
- Evidence: `server/app/postcall/retention.py:29-32` purges only `audio_refs` and `transcripts`. `server/app/rights/workflow.py:202-211` erases those two tables and pseudonymises `call_outcomes`, nothing else. Raw personal data stays in:
  - `booking_events.payload` (phone_e164 and first_name; `campaigns/models.py:24-30`);
  - `clearances.phone_e164` (`compliance/models.py:100`);
  - `consent_records.phone_e164`, with `consent_days=None` meaning kept forever (`core/config.py:75`);
  - `handoffs.summary.who` (first name; `handoff/summary.py:46`);
  - CRM tickets and the Kafka `av.call-outcomes.v1` topic.
- Impact: The notice (`voice/notice.py:68-70`), DPA 6.1 and security pack §5 all say data is deleted. That is untrue for the tables above. This breaches DPDP s.8(7) and s.12(3).
- Fix: add `booking_events`, `clearances`, `handoffs`, `gate_decisions`, `dial_attempts` and `whatsapp_sends` to `purge_expired` with per-purpose settings; delete or null them in `fulfil_erasure` and queue a CRM redaction; store consent by phone_hash.

**H2. The breach and CERT-In clocks never alert and cannot be closed**
- Evidence:
  - `incidents/service.py:113` `overdue()` is never called.
  - The API offers only list and open (`api/routes/ops.py:174-196`). `mark_reported` and `mark_principals_notified` have no endpoint.
  - There is no 24 h timer for notifying Agoda, although security pack §6 and DPA 5.1 promise it.
  - DPDP Rule 7(1) requires an intimation to the Board "without delay"; only the 72 h detailed report is modelled.
  - `detected_at` is accepted unchecked (`ops.py:184`), so a future date pushes the deadline back.
- Impact: The 6 h CERT-In deadline can pass silently.
- Fix: a cron that pages via `overdue()` at T-2 h and at the deadline; audited `POST /incidents/{id}/reported` and `/principals-notified`; a 24 h `agoda_notify_due_at` and a Board intimation field; reject future `detected_at`.

**H3. CERT-In ICT-log retention and NTP sync are claimed but not built**
- Evidence: `retention.ict_log_days` (`core/config.py:76`) and `ntp_servers` (`config.py:139`) are read only by the validator and the Helm env. Logs go to stdout (`core/logging.py:33`), and no log sink, retention policy or NTP configuration exists in code. SECURITY.md C-12 and security pack §5 still say "ICT logs 180 days rolling, producible in India".
- Impact: This fails CERT-In Direction (iv) (180-day logs kept in India) and Direction (i) (NTP sync to NIC/NPL). Both are unsupported claims in a buyer document.
- Fix: Add a Helm log-shipping sidecar to an India-region store with a 180-day lifecycle, plus a chrony config pointing at samay1/2.nic.in. Until then, mark C-12 "planned" in both documents.

**H4. Production would accept the placeholder grievance contact and notice URL**
- Evidence: `core/config.py:87-88` defaults to "[CD: grievance contact]" and `https://example.invalid/...`. The production validator (`config.py:155-179`) does not check either. `voice/notice.py:66,72` puts both values into every notice. The payment link has the same problem (`config.py:93`).
- Impact: Every DPDP s.5 / Rule 3 notice would carry no real grievance channel and a dead link.
- Fix: In `validate_for_environment`, reject any grievance, notice or payment URL that contains `example.invalid` or `[CD`.

## Medium

**M1. No engine rate limiting; web limiter bypassable**
- Evidence: the server has no throttling, although `web/src/lib/server/security.ts:73-74` says it has. The engine `/demo/*` passcode has no minimum length or throttle (`demo/settings.py:12`). The web limiter keys on client-supplied X-Forwarded-For (`security.ts:83`) in an unbounded per-instance Map (`security.ts:77`).
- Fix: per-IP and per-key limits at ingress or in middleware; key the web limiter on the platform-set IP in a shared store; require a 12+ character engine passcode.

**M2. The audit log is not append-only, and authentication failures are not logged**
- Evidence: `audit_log` has no trigger or REVOKE (`migrations/.../3352282f8f92_initial_schema.py:34`), so the app role can UPDATE or DELETE rows. `api/deps.py:87-101` and `api/errors.py` log no 401/403 (ASVS 7.1.3). `GET /calls`, `/handoff` and `/audit` are unaudited.
- Fix: Add `REVOKE UPDATE, DELETE ON audit_log FROM app_role` in a migration, and write audit rows for 401/403 and for personal-data reads.

**M3. The environment defaults to dev, which fails open**
- Evidence: `core/config.py:115` sets `environment="dev"`. That skips every production check and enables the dev tokens (`config.py:121-128`), which are public in the repo (`web/src/lib/mock-backend.ts:13`). Only Helm sets production (`values.yaml:7`).
- Fix: Make `environment` required with no default, or refuse to start with dev tokens unless `AV_ALLOW_DEV_TOKENS=1`.

**M4. The console session holds a raw long-lived credential, which undercuts the MFA answer**
- Evidence:
  - `app/api/console/session/route.ts:21-23` accepts any bearer, including admin `avk_` keys, and stores it in a cookie.
  - Key expiry is optional (`api/routes/admin.py:34`, `admin/apikeys.py:72`).
  - The web app has no OIDC code flow, although `admin/oidc.py:4` describes one.
  - Sign-out only deletes the cookie.
- Impact: An API key bypasses the MFA answer in security pack Q6.
- Fix: Refuse `avk_` keys at console sign-in, require key expiry of 90 days or less, and build the OIDC PKCE flow.

**M5. The rights workflow covers only part of what the notice and DPA promise**
- Evidence: `rights/models.py:13` has only access, correction and erasure, though `notice.py:62` and DPA 3.4 promise nomination and grievance. The access export (`workflow.py:153-157`) omits booking_events and handoffs; identity checks are not recorded.
- Fix: Add `nomination` and `grievance` kinds with SLA timers, widen the export, and record a `verified_by` field.

**M6. Full booking IDs reach read-only users and MCP agents under a "redacted" label**
- Evidence: `CallOutcome.booking_id` is unmasked. It is served by `records.py:53-66` and by `mcp/tools.py:105-112`, whose tool is described as "redacted".
- Fix: Apply `mask_booking_id` in the response views. Leave the full ID only for `transcripts:read`.

## Low
- **L1. The demo gate cookie is static.** Its value is `HMAC(passcode, "av-gate-v1")` (`web/src/lib/server/security.ts:51-53`, `middleware.ts:17-26`). It is unrevocable and allows offline passcode guessing. Fix: sign `{exp, nonce}` with a separate secret.
- **L2. Sign-in is open to login CSRF.** `POST /console/session` has no CSRF check, and `req.json()` ignores the content type (`session/route.ts:16-18`). Fix: require `content-type: application/json` and check Origin.
- **L3. Public `/status` says too much.** It reveals the kill-switch state and whether providers are live or mock,, with an unauthenticated DB query per request (`api/routes/status.py:40-62`). Fix: cache the result for 30 s and use generic component names.
- **L4. The API's docs and error messages leak detail.** FastAPI `/docs` and `/openapi.json` are exposed in production (`api/app.py:33`). Auth errors tell an unknown key apart from a revoked or expired one, and echo PyJWT's reason (`apikeys.py:133-137`, `oidc.py:62`). Fix: return one generic 401 message.
- **L5. JWKS is fetched once at boot** (`wiring/main.py:27`), so IdP key rotation breaks SSO. Fix: re-fetch on an unknown `kid`.
- **L6. Concierge consent is not recorded.** The booking consent is stored nowhere (`web/src/lib/server/engine.ts:212-214`),, and the engine has no `/concierge` routes. Brief S9 asks for recorded consent.
- **L7. An MCP agent can undo a human's pause.** `start_campaign` (`mcp/tools.py:100-102`). Fix: refuse unless an agent made the pause.
- **L8. Placeholder disclosure address** (SECURITY.md:27).
