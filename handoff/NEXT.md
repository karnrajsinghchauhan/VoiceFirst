# Next steps (local session)

Repo: github.com/karnrajsinghchauhan/VoiceFirst. The full spec is docs/briefs/brief-v3.md; state is in STATUS.md, DECISIONS.md and handoff/README.md.

## 0. Setup and verify
```bash
git clone https://github.com/karnrajsinghchauhan/VoiceFirst.git && cd VoiceFirst
make hooks
cd server && uv sync --extra voice && cd ..
(cd tools/contracts-ts && npm ci) && (cd web && npm ci)
```
- Postgres 16 with login postgres/postgres and databases `agoda_voice` and `agoda_voice_test`.
- Run `make check`, `make e2e`, `make eval` and `make eval-audio`; all should be green.
- Commit with `AV_PROOF_EXAMPLES=200 git commit ...` (the hook runs `make check`). CI runs the full 10,000.
- Open PRs #1–#14 and fix any red CI: the workflow has never run.

## 1. Finish the three workstreams
For each, merge `main` in, apply its patch, finish its scope from brief v3, get `make check` green, then mark the PR ready.
- #12 `v3/w1-providers-crm`: S3 + S5. Patch: `handoff/v3-w1-providers-crm.uncommitted.patch`. Write the migration for its new tables.
- #13 `v3/w2-qa-costs-concierge`: S4, S6, S9 and S10. Patch: `handoff/v3-w2-qa-costs-concierge.uncommitted.patch`.
- #14 `v3/w3-frontend`: the section 6 site, console pages, concierge UI, `/demo`, `/agoda` + PDF, and `claims.test.ts`.

Every new table needs `tenant_id`, and its migration must call `app.core.rls.enable()`; `tests/e2e/test_tenant_isolation.py` fails otherwise.

## 2. Remaining brief-v3 work
- **S7, rest:**
  - per-tenant and per-number concurrency limits in the dispatcher;
  - API rate limiting;
  - envelope encryption (per-tenant key wrapped by a local-file KMS; production KMS is [CD]);
  - retention per purpose, with a purge report.
- **S8:**
  - CI gates: gitleaks, semgrep, trivy, cosign, CycloneDX SBOM;
  - web hardening;
  - inbound-webhook replay tests;
  - a timed backup/restore drill recorded in `reports/`;
  - `/.well-known/security.txt` and a status page fed by real health checks;
  - `docs/incident-response.md` and `docs/backup-restore.md`;
  - the security questionnaire answer sheet;
  - a STRIDE threat model covering every surface.
- **S11:**
  - IaC for one India or Singapore container host;
  - `docs/configuration.md`, `docs/launch-costs.md` (exact monthly costs) and `docs/setup-runbook.md` (section 4 of the brief);
  - a dry-run deploy only.
- **Section 5:** three blind reviews by fresh subagents (CX director, security/privacy, staff voice-AI engineer) written to `reviews/*.md`. Fix every High and Critical; list Mediums in PLAN.md.
- **Section 8:** the final phone-friendly summary, then push and notify.

## 3. Use local access (what the cloud session couldn't do)
- Fill the placeholders from Karn's files and notes: `BRAND_NAME`, `LEGAL_ENTITY_NAME`, `LEGAL_GSTIN`, `LEGAL_ADDRESS`, `CONTACT_EMAIL`, the grievance contact, and the domain (ownermeetings.com).
- In the browser, verify every row of `docs/sources.md`, add its URL and access date, and drop anything you can't verify.
- In the browser, re-check every unit price in `config/costs.yaml` and the vendor comparison, recording the URL and date of each.
- Answer what you can of `docs/discovery-questions.md` from Karn's notes; leave the rest as questions.
- Run with local Docker, which was blocked in the cloud session:
  - `make up`;
  - `helm lint deploy/helm/agoda-voice`;
  - Lighthouse on the built site (target 95+);
  - trivy against the server image.

## 4. Hard rules
- Spending gate: no signups, purchases, domains, numbers, keys or WhatsApp verification without Karn's explicit yes in chat. List each item in `docs/launch-costs.md` with its monthly cost.
- No real calls or WhatsApp messages except the 20 approved test calls, to Karn's own phones only, with keys he puts in `.env`. Count them in STATUS.md.
- Never bypass the pre-commit hook. Never put Agoda brand assets on public pages. Every public number needs a source or the label "estimate".
- Production rules already enforced in code: the database role must not be a superuser (or row-level security doesn't apply), no static API tokens, and no mock providers.
