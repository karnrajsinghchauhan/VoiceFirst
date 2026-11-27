# MCP server: design (scaffold, not deployed)

Agoda Voice is an independent ProsperOps product and is not affiliated with or endorsed by Agoda.

## Purpose
Agoda builds its business "bottom up" with interacting agents (docs/sources.md S-12). This lets Agoda's own agents read and steer the calling service through the Model Context Protocol, with the same permissions, scopes and audit trail as a person in the console, and without any path to the actions that must stay with a person.

## What an agent can do
| Tool | Permission | Effect |
|---|---|---|
| `list_campaigns` | `campaigns:read` | Campaigns and whether each is paused |
| `pause_campaign` | `campaigns:write` | Pause; queued calls wait |
| `start_campaign` | `campaigns:write` | Resume a paused campaign; every call still passes every gate |
| `list_call_outcomes` | `calls:read` | Recent outcomes, redacted, no transcripts |
| `get_call_outcome` | `calls:read` | One outcome by id |
| `get_qa_report` | `metrics:read` | The latest eval scorecard |

## What stays human-only
The kill switch (engage and release), consent records, do-not-call marking, payment links, refunds, cancellations and credits. These names are on a refusal list (`HUMAN_ONLY`) so an agent gets "human-only; use the console", and no tool may require `killswitch:write`, `consent:write` or `apikeys:write`. A test enforces both. Pausing is allowed because it only ever reduces calling; the kill switch is not, because it is the operator's last-resort control and must not be released by the thing it may need to stop.

## Authentication and authorisation
- Scoped API keys only (`avk_...`, SHA-256 at rest, rotatable, with expiry). Static dev tokens and SSO tokens are refused.
- A key's effective permissions are its role narrowed by its scopes (D-021). `tools/list` shows only the tools those permissions allow; `tools/call` checks again.

## Audit
Every `tools/call`, allowed or refused, writes an audit row (`mcp.<tool>`, actor, role, outcome) and an `av.audit.v1` event.

## Protocol
JSON-RPC 2.0 with `initialize`, `tools/list` and `tools/call` (protocol version 2025-06-18). Errors: -32001 unauthenticated, -32003 forbidden or human-only, -32004 not found, -32602 invalid arguments. Tool results are returned as one JSON text content item.

## Not done yet
- Transport: the handler is transport-agnostic (`McpServer.handle(request, bearer)`); a streamable-HTTP adapter behind the API's ingress and rate limit is the next step.
- Rate limits per key and per tool.
- Resources and prompts (MCP features beyond tools) are not offered.

Code: `server/app/mcp/`. Tests: `server/tests/mcp/test_mcp.py`.
