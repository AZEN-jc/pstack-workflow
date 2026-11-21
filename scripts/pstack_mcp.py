#!/usr/bin/env python3
"""
pstack Zero-Dependency Stdio MCP Server (JSON-RPC 2.0)
Exposes: pstack_route, pstack_verify, pstack_swarm, pstack_arena, pstack_tree
Usage:
  python3 scripts/pstack_mcp.py
  python3 scripts/pstack_mcp.py --list-tools
  python3 scripts/pstack_mcp.py --self-test
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from pstack_resolver import ensure_workspace_skeleton, get_workspace_root
from pstack_router import auto_discover_pointers_and_scope, classify_goal, generate_brief, load_models_config
from pstack_scheduler import execute_arena, execute_swarm, load_dag_state
from pstack_tree import load_tree_data, render_ascii_tree

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "pstack-mcp", "version": "3.1.0"}

MCP_TOOLS: list[dict[str, object]] = [
    {
        "name": "pstack_route",
        "description": "Classify goal intent/tier and generate active-brief.md with ranked bilingual Repo-Map pointers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "Task goal or natural language instruction"},
                "output": {"type": "string", "description": "Optional custom brief output path"},
                "workspace": {"type": "string", "description": "Optional target workspace root path"},
            },
            "required": ["goal"],
        },
    },
    {
        "name": "pstack_verify",
        "description": "Run deterministic Pstack verification gates (all|handoff|prose|code|prep-verifier|verdict).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["all", "handoff", "prose", "code", "prep-verifier", "verdict"],
                    "default": "all",
                },
                "target": {"type": "string", "description": "Optional file or directory target"},
                "blind": {"type": "boolean", "description": "Use --blind mode for prep-verifier"},
                "fix": {"type": "boolean", "description": "Use --fix mode for handoff"},
                "workspace": {"type": "string", "description": "Optional target workspace root path"},
            },
            "required": [],
        },
    },
    {
        "name": "pstack_swarm",
        "description": "Execute parallel Git Worktree DAG nodes by topological wave.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "High-level task goal for default DAG"},
                "spec": {"type": "string", "description": "Optional path to custom DAG JSON spec"},
                "dry_run": {"type": "boolean", "default": True, "description": "Simulate execution"},
                "workspace": {"type": "string", "description": "Optional target workspace root path"},
            },
            "required": [],
        },
    },
    {
        "name": "pstack_arena",
        "description": "Run multi-agent competition in separate isolated Git Worktrees.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "runners": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of competing runners (e.g. ['codex', 'opencode'])",
                },
                "dry_run": {"type": "boolean", "default": True, "description": "Simulate execution"},
                "workspace": {"type": "string", "description": "Optional target workspace root path"},
            },
            "required": [],
        },
    },
    {
        "name": "pstack_tree",
        "description": "Return DAG state and recent event stream from dag-state.json and events.jsonl.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "json": {"type": "boolean", "default": True, "description": "Return structured JSON payload"},
                "workspace": {"type": "string", "description": "Optional target workspace root path"},
            },
            "required": [],
        },
    },
]


def _resolve_ws(arguments: dict, default_workspace: Path | None = None) -> Path:
    raw_ws = arguments.get("workspace")
    if isinstance(raw_ws, str) and raw_ws.strip():
        return Path(raw_ws).expanduser().resolve()
    return (default_workspace or get_workspace_root()).resolve()


def _tool_pstack_route(arguments: dict, default_workspace: Path | None) -> dict:
    goal = str(arguments.get("goal", "")).strip()
    if not goal:
        raise ValueError("Missing required parameter: goal")
    ws = _resolve_ws(arguments, default_workspace)
    output_arg = arguments.get("output")
    output_path = Path(str(output_arg)).expanduser().resolve() if output_arg else None
    cfg = load_models_config(ws)
    classification = classify_goal(goal, cfg)
    buf = io.StringIO()
    with redirect_stdout(buf):
        brief_path = generate_brief(goal, ws, output_path=output_path, models_cfg=cfg)
        pointers, allowed_paths = auto_discover_pointers_and_scope(goal, ws)
    payload = {
        "status": "ROUTED",
        "goal": goal,
        "classification": classification,
        "allowed_paths": allowed_paths,
        "pointers": pointers,
        "brief_path": str(brief_path),
    }
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}], "isError": False}


def _tool_pstack_verify(arguments: dict, default_workspace: Path | None) -> dict:
    mode = str(arguments.get("mode", "all")).strip() or "all"
    valid_modes = {"all", "handoff", "prose", "code", "prep-verifier", "verdict"}
    if mode not in valid_modes:
        raise ValueError(f"Invalid verify mode: {mode}")
    ws = _resolve_ws(arguments, default_workspace)
    verify_script = Path(__file__).resolve().parent / "pstack-verify.py"
    cmd = [sys.executable, str(verify_script), mode]
    target = arguments.get("target")
    if target:
        cmd.append(str(target))
    if mode == "prep-verifier" and arguments.get("blind"):
        cmd.append("--blind")
    if mode == "handoff" and arguments.get("fix"):
        cmd.append("--fix")

    env = os.environ.copy()
    env["PSTACK_WORKSPACE"] = str(ws)
    proc = subprocess.run(cmd, cwd=ws, env=env, capture_output=True, text=True, check=False)
    combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    payload = {
        "mode": mode,
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "output": combined.strip(),
    }
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}], "isError": False}


def _tool_pstack_swarm(arguments: dict, default_workspace: Path | None) -> dict:
    ws = _resolve_ws(arguments, default_workspace)
    goal = arguments.get("goal")
    spec_raw = arguments.get("spec")
    spec_path = Path(str(spec_raw)).expanduser().resolve() if spec_raw else None
    dry_run = bool(arguments.get("dry_run", True))
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = execute_swarm(ws, goal=str(goal) if goal else None, spec_path=spec_path, dry_run=dry_run)
    dag_state = load_dag_state(ws)
    payload = {
        "exit_code": rc,
        "passed": rc == 0,
        "dag_state": dag_state,
        "output": buf.getvalue().strip(),
    }
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}], "isError": rc != 0}


def _tool_pstack_arena(arguments: dict, default_workspace: Path | None) -> dict:
    ws = _resolve_ws(arguments, default_workspace)
    runners_arg = arguments.get("runners")
    if isinstance(runners_arg, str):
        runners = [r.strip() for r in runners_arg.split(",") if r.strip()]
    elif isinstance(runners_arg, list):
        runners = [str(r).strip() for r in runners_arg if str(r).strip()]
    else:
        runners = ["codex", "opencode"]
    dry_run = bool(arguments.get("dry_run", True))
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = execute_arena(ws, runners=runners, dry_run=dry_run)
    dag_state = load_dag_state(ws)
    payload = {
        "exit_code": rc,
        "winner": dag_state.get("winner"),
        "dag_state": dag_state,
        "output": buf.getvalue().strip(),
    }
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}], "isError": rc != 0}


def _tool_pstack_tree(arguments: dict, default_workspace: Path | None) -> dict:
    ws = _resolve_ws(arguments, default_workspace)
    json_mode = bool(arguments.get("json", True))
    dag_data, events = load_tree_data(ws)
    if not json_mode:
        ascii_tree = render_ascii_tree(dag_data, events)
        return {"content": [{"type": "text", "text": ascii_tree}], "isError": False}
    payload = {
        "version": "3.1",
        "dag_state": dag_data,
        "events_count": len(events),
        "events": events[-20:],
    }
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}], "isError": False}


TOOL_HANDLERS = {
    "pstack_route": _tool_pstack_route,
    "pstack_verify": _tool_pstack_verify,
    "pstack_swarm": _tool_pstack_swarm,
    "pstack_arena": _tool_pstack_arena,
    "pstack_tree": _tool_pstack_tree,
}


def handle_jsonrpc_message(msg: dict, default_workspace: Path | None = None) -> dict | None:
    if not isinstance(msg, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}

    method = msg.get("method")
    req_id = msg.get("id")
    raw_params = msg.get("params")
    if raw_params is not None and not isinstance(raw_params, dict):
        if req_id is None:
            return None
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Invalid params: expected object"}}
    params = raw_params or {}

    if method == "notifications/initialized" or (req_id is None and isinstance(method, str) and method.startswith("notifications/")):
        return None

    if req_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name")
        raw_args = params.get("arguments")
        if raw_args is not None and not isinstance(raw_args, dict):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Invalid params: arguments must be an object"},
            }
        arguments = raw_args or {}
        if tool_name not in TOOL_HANDLERS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
            }
        try:
            result = TOOL_HANDLERS[tool_name](arguments, default_workspace)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Tool error ({tool_name}): {exc}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def _emit_response(resp: dict, framed: bool) -> None:
    encoded = json.dumps(resp, ensure_ascii=False)
    body_bytes = encoded.encode("utf-8")
    stdout_buf = getattr(sys.stdout, "buffer", None)
    if stdout_buf is not None:
        if framed:
            header = f"Content-Length: {len(body_bytes)}\r\n\r\n".encode("ascii")
            stdout_buf.write(header + body_bytes)
        else:
            stdout_buf.write(body_bytes + b"\n")
        stdout_buf.flush()
        return

    if framed:
        sys.stdout.write(f"Content-Length: {len(body_bytes)}\r\n\r\n")
        sys.stdout.write(encoded)
    else:
        sys.stdout.write(encoded + "\n")
    sys.stdout.flush()


def _read_exact_bytes(stream, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def serve_stdio(default_workspace: Path | None = None) -> int:
    stdin_buf = getattr(sys.stdin, "buffer", None)
    while True:
        if stdin_buf is not None:
            raw_line = stdin_buf.readline()
            if not raw_line:
                break
            stripped = raw_line.decode("utf-8", errors="replace").strip()
        else:
            line = sys.stdin.readline()
            if not line:
                break
            stripped = line.strip()

        if not stripped:
            continue

        framed = False
        raw_json = stripped
        lower_first = stripped.lower()
        if lower_first.startswith("content-length:") or lower_first.startswith("content-type:"):
            framed = True
            headers: list[str] = [stripped]
            while True:
                if stdin_buf is not None:
                    hdr_raw = stdin_buf.readline()
                    if not hdr_raw or hdr_raw in (b"\n", b"\r\n"):
                        break
                    hdr_txt = hdr_raw.decode("utf-8", errors="replace").strip()
                else:
                    hdr_line = sys.stdin.readline()
                    if not hdr_line or hdr_line in ("\n", "\r\n"):
                        break
                    hdr_txt = hdr_line.strip()
                if hdr_txt:
                    headers.append(hdr_txt)

            content_len: int | None = None
            for hdr in headers:
                if hdr.lower().startswith("content-length:"):
                    try:
                        content_len = int(hdr.split(":", 1)[1].strip())
                    except ValueError:
                        content_len = -1
                    break

            if content_len is None or content_len <= 0:
                _emit_response(
                    {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid Content-Length"}},
                    framed=False,
                )
                continue

            if stdin_buf is not None:
                body_raw = _read_exact_bytes(stdin_buf, content_len)
                if not body_raw:
                    break
                raw_json = body_raw.decode("utf-8", errors="replace")
            else:
                raw_json = sys.stdin.read(content_len)
                if not raw_json:
                    break

        try:
            msg = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            _emit_response(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc}"}},
                framed=framed,
            )
            continue

        resp = handle_jsonrpc_message(msg, default_workspace=default_workspace)
        if resp is not None:
            _emit_response(resp, framed=framed)

    return 0


def run_self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp).resolve()
        ensure_workspace_skeleton(ws)

        init_resp = handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            default_workspace=ws,
        )
        assert init_resp and init_resp["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION

        notif_resp = handle_jsonrpc_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            default_workspace=ws,
        )
        assert notif_resp is None

        list_resp = handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            default_workspace=ws,
        )
        assert list_resp is not None
        tool_names = [t["name"] for t in list_resp["result"]["tools"]]
        assert tool_names == ["pstack_route", "pstack_verify", "pstack_swarm", "pstack_arena", "pstack_tree"]

        route_resp = handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "pstack_route", "arguments": {"goal": "修复状态机超时异常", "workspace": str(ws)}},
            },
            default_workspace=ws,
        )
        assert route_resp is not None and not route_resp["result"]["isError"]

        tree_resp = handle_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "pstack_tree", "arguments": {"json": True, "workspace": str(ws)}},
            },
            default_workspace=ws,
        )
        assert tree_resp is not None and not tree_resp["result"]["isError"]

    print("[OK] Pstack MCP Server self-test passed (5 tools, JSON-RPC 2.0 Stdio)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack Zero-Dependency Stdio MCP Server")
    parser.add_argument("--list-tools", action="store_true", help="Print exposed MCP tool definitions as JSON")
    parser.add_argument("--self-test", action="store_true", help="Run internal MCP protocol loopback self-test")
    args = parser.parse_args()

    if args.list_tools:
        print(json.dumps(MCP_TOOLS, indent=2, ensure_ascii=False))
        return 0
    if args.self_test:
        return run_self_test()
    return serve_stdio()


if __name__ == "__main__":
    sys.exit(main())
