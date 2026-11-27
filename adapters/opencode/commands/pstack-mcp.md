---
description: Verify and inspect Pstack native Stdio MCP Server tools (/pstack-mcp)
---

Inspect and self-test the Pstack v3.1 zero-dependency JSON-RPC 2.0 Stdio MCP server (`~/.local/bin/pstack-mcp`):
1. Run `pstack mcp --self-test` to verify loopback execution across all 5 tools (`pstack_route`, `pstack_verify`, `pstack_swarm`, `pstack_arena`, `pstack_tree`).
2. Run `pstack mcp --list-tools` to inspect JSON schemas.
3. Confirm global MCP registration and sync status across coding agents with `pstack status` or `pstack update --sync-agents`.
