#!/usr/bin/env python3
"""Read-only discovery and client config helper for ReOpenly's native MCP server."""

import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://reopenly.com"
MCP_PATH = "/api/mcp"
PRM_PATH = "/.well-known/oauth-protected-resource/api/mcp"


def normalize_base_url(base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    if not url.startswith(("https://", "http://")):
        raise SystemExit("Base URL must start with https:// or http://.")
    return url


def mcp_url(base_url: str) -> str:
    return f"{normalize_base_url(base_url)}{MCP_PATH}"


def build_config(client: str, base_url: str) -> dict:
    endpoint = mcp_url(base_url)
    if client == "claude-code":
        return {
            "client": "claude-code",
            "command": f"claude mcp add --transport http reopenly {endpoint}",
            "mcpServers": {
                "reopenly": {
                    "type": "http",
                    "url": endpoint,
                }
            },
        }
    if client == "opencode":
        return {
            "client": "opencode",
            "mcp": {
                "reopenly": {
                    "type": "remote",
                    "url": endpoint,
                    "oauth": {},
                }
            },
        }
    if client == "codex":
        return {
            "client": "codex",
            "toml": (
                "[mcp_servers.reopenly]\n"
                f'url = "{endpoint}"\n'
            ),
        }
    if client == "cursor":
        return {
            "client": "cursor",
            "mcpServers": {
                "reopenly": {
                    "url": endpoint,
                }
            },
        }
    if client == "chatgpt":
        return {
            "client": "chatgpt",
            "mcpServers": {
                "reopenly": {
                    "type": "streamable-http",
                    "url": endpoint,
                }
            },
            "authentication": "OAuth 2.1",
            "defaultScope": "mcp:read",
        }
    raise SystemExit(f"Unsupported client: {client}")


def fetch_json_or_status(url: str, timeout: float) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, text/event-stream",
            "User-Agent": "reopenly-skills-mcp-check/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = raw[:500]
            return {
                "url": url,
                "status": resp.status,
                "www_authenticate": resp.headers.get("WWW-Authenticate"),
                "body": body,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw[:500]
        return {
            "url": url,
            "status": exc.code,
            "www_authenticate": exc.headers.get("WWW-Authenticate"),
            "body": body,
        }
    except urllib.error.URLError as exc:
        return {
            "url": url,
            "status": None,
            "error": str(exc.reason),
        }


def cmd_discover(args: argparse.Namespace) -> int:
    base = normalize_base_url(args.base_url)
    prm_url = f"{base}{PRM_PATH}"
    endpoint = mcp_url(base)
    result = {
        "endpoint": endpoint,
        "transport": "streamable-http",
        "protected_resource_metadata": fetch_json_or_status(prm_url, args.timeout),
        "unauthenticated_probe": fetch_json_or_status(endpoint, args.timeout),
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    payload = build_config(args.client, args.base_url)
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"ReOpenly origin (default: {DEFAULT_BASE_URL}).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_config = subparsers.add_parser(
        "config",
        help="Print an MCP client configuration snippet for https://reopenly.com/api/mcp.",
    )
    p_config.add_argument(
        "--client",
        required=True,
        choices=("claude-code", "opencode", "codex", "cursor", "chatgpt"),
        help="Target MCP client.",
    )
    p_config.set_defaults(func=cmd_config)

    p_discover = subparsers.add_parser(
        "discover",
        help="Probe public OAuth protected-resource metadata without credentials.",
    )
    p_discover.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds (default: 15).",
    )
    p_discover.set_defaults(func=cmd_discover)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
