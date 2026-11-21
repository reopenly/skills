---
name: reopenly-mcp
description: Connect to and use the ReOpenly native MCP server (https://reopenly.com/api/mcp) over Streamable HTTP with OAuth 2.1 to inspect projects, datasets, training runs, hosted models, Search indexes, pricing, and prepaid balance.
compatibility: Requires an MCP client supporting Streamable HTTP and OAuth 2.1 (Python 3.9+ for the optional discovery/config helper).
---

# Use ReOpenly via MCP

1. Use the ReOpenly native MCP endpoint directly when an MCP-compatible host is connected:
   - **Endpoint:** `https://reopenly.com/api/mcp`
   - **Transport:** Streamable HTTP
   - **Authentication:** OAuth 2.1 with registered-account sign-in (account-scoped)
   - **Overview:** `https://reopenly.com/mcp`

   Let the MCP client run its OAuth 2.1 sign-in flow. Never ask for or paste `REOPENLY_API_KEY`, passwords, or OAuth tokens into conversation text or tool arguments.

2. If the user needs a client setup snippet or wants to check live OAuth protected-resource discovery before connecting, run the bundled helper (substitute its installed path):

```sh
# Print a client configuration snippet (claude-code, opencode, codex, cursor, or chatgpt)
python3 /path/to/reopenly-mcp/scripts/mcp_check.py config --client claude-code

# Probe public OAuth protected-resource metadata without credentials
python3 /path/to/reopenly-mcp/scripts/mcp_check.py discover
```

3. Once connected, start with `get_connection_status` or `list_projects` to confirm the linked account and discover owned project slugs. Never invent project slugs, dataset IDs, job IDs, or hosted model aliases. Follow returned `next_cursor` pagination when listing resources, and disclose any `truncated_fields` or absent/null metrics rather than treating them as zero or complete.

4. Respect the active MCP scope and billing boundaries:
   - **Read-only launch profile (`mcp:read`):** exposes 31 observational read tools covering projects (`list_projects`, `get_project`, `get_project_overview`, `get_project_lifecycle`), datasets, examples, chats, tags, frozen versions, and imports, training jobs, profiles, and execution logs, hosted models and Search indexes, base model catalog (`get_base_model_catalog`), USD pricing (`get_model_prices`), prepaid USD balance (`get_balance`), credit history, artifact downloads, and compute preparation status.
   - **Zero destructive actions and zero in-chat purchases:** the `mcp:read` profile never modifies data, never starts paid training or inference, and never purchases credits.
   - **Mutations, paid compute, and billing:** direct users to the ReOpenly web dashboard (or the local API-key skills in this repository) for dataset writes, inference, training, and prepaid balance top-ups. When additional scopes (`mcp:write` or `mcp:compute:write`) are enabled on an account, paid compute still requires explicit first-party web review and confirmation before execution.
   - **Refusals:** if a tool call returns an authentication, scope, or access refusal, report the exact refusal without retrying with guessed identifiers or credentials.
