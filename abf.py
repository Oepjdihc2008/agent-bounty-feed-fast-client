#!/usr/bin/env python3
"""
Agent Bounty Feed CLI & MCP Client (Zero Dependencies)
A fast, lightweight CLI and Python SDK for interacting with Agent Bounty Feed:
- REST API (/earn-now)
- MCP JSON-RPC 2.0 (Streamable HTTP tools endpoint)
- Full filtering (min reward, no-KYC, network, source)

Author: Oepjdihc2008
License: MIT
"""

import sys
import json
import argparse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

BASE_URL = "https://agent-bounty-feed.dailydollar.workers.dev"
MCP_ENDPOINT = f"{BASE_URL}/mcp"
EARN_NOW_ENDPOINT = f"{BASE_URL}/earn-now"
FEED_JSON = "https://dailydollar-bot.github.io/agent-bounty-feed/feed.json"
USER_AGENT = "AgentBountyFeed-CLI/1.0 (Zero-Dependency; Python 3)"


class ABFClient:
    """Client for Agent Bounty Feed REST and MCP endpoints."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _http_get(self, url: str) -> Dict[str, Any]:
        req = urllib.request.Request(url, headers=self.headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")

    def _mcp_call(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(MCP_ENDPOINT, data=data, headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if "error" in res:
                    raise RuntimeError(f"MCP Error {res['error'].get('code')}: {res['error'].get('message')}")
                content = res.get("result", {}).get("content", [])
                if content and "text" in content[0]:
                    return json.loads(content[0]["text"])
                return res.get("result")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"MCP HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"MCP Network error: {e.reason}")

    def get_earn_now(self) -> Dict[str, Any]:
        """Fetch real-time top claimable bounties from /earn-now."""
        return self._http_get(EARN_NOW_ENDPOINT)

    def list_bounties(
        self,
        source: Optional[str] = None,
        min_usd: Optional[float] = None,
        network: Optional[str] = None,
        exclude_requires: Optional[str] = None,
        limit: int = 20,
        sort: str = "reward"
    ) -> Dict[str, Any]:
        """Query MCP list_bounties tool with full parameter support."""
        args: Dict[str, Any] = {"limit": limit, "sort": sort}
        if source:
            args["source"] = source
        if min_usd is not None:
            args["min_usd"] = min_usd
        if network:
            args["network"] = network
        if exclude_requires:
            args["exclude_requires"] = exclude_requires
        return self._mcp_call("list_bounties", args)

    def get_feed_stats(self) -> Dict[str, Any]:
        """Fetch live ecosystem aggregate stats via MCP."""
        return self._mcp_call("get_feed_stats", {})

    def get_bounty(self, bounty_id: str) -> Dict[str, Any]:
        """Retrieve single bounty record by ID via MCP."""
        return self._mcp_call("get_bounty", {"id": bounty_id})


def format_table(rows: List[List[str]], headers: List[str]) -> str:
    """Format tabular data into an aligned ASCII table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))

    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * widths[i] for i in range(len(widths)))
    body_lines = [" | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row)) for row in rows]
    return f"{header_line}\n{sep_line}\n" + "\n".join(body_lines)


def cmd_earn_now(client: ABFClient, args: argparse.Namespace) -> None:
    data = client.get_earn_now()
    items = data.get("items", [])
    print(f"\n⚡ Agent Bounty Feed — Earn Now (Total Active: {data.get('count', 0)})")
    print(f"Generated At: {data.get('generated_at')}\n")

    if not items:
        print("No live bounties found.")
        return

    table_data = []
    for item in items:
        reward_str = f"${item.get('est_usd', 0)} USD"
        reqs = ",".join(item.get("requires", []))
        deadline = (item.get("deadline") or "Open")[:10]
        table_data.append([
            item.get("id", ""),
            reward_str,
            item.get("source", ""),
            reqs,
            deadline,
            item.get("title", "")[:45] + "..."
        ])

    headers = ["ID", "Reward", "Source", "Requires", "Deadline", "Title"]
    print(format_table(table_data, headers))


def cmd_list(client: ABFClient, args: argparse.Namespace) -> None:
    res = client.list_bounties(
        source=args.source,
        min_usd=args.min_usd,
        network=args.network,
        exclude_requires=args.exclude_requires,
        limit=args.limit,
        sort=args.sort
    )
    items = res.get("items", [])
    print(f"\n📋 Active Bounties (Matched: {res.get('total_matching', len(items))}, Showing: {len(items)})")
    
    table_data = []
    for item in items:
        reward_val = item.get("reward")
        curr = item.get("currency", "USD")
        reward_str = f"{reward_val} {curr}" if reward_val is not None else "N/A"
        reqs = ",".join(item.get("requires", []))
        table_data.append([
            item.get("id", ""),
            reward_str,
            item.get("source", ""),
            item.get("network") or "any",
            reqs,
            item.get("title", "")[:40] + "..."
        ])

    headers = ["ID", "Reward", "Source", "Network", "Requires", "Title"]
    print(format_table(table_data, headers))


def cmd_stats(client: ABFClient, args: argparse.Namespace) -> None:
    res = client.get_feed_stats()
    stats = res.get("stats", {})
    print("\n📊 Agent Bounty Feed Ecosystem Statistics")
    print("-" * 45)
    print(f"Total Available Bounties: {stats.get('items', 0)}")
    print(f"Total Value (USD):        ${stats.get('total_usd', 0):,.2f}")
    print(f"Audit Contest Pools:      ${stats.get('audit_contest_prize_pools_usd', 0):,.2f}")
    print(f"Zero Bond / Zero KYC:     {stats.get('no_bond_no_stake_no_kyc', 0)} listings")
    print(f"New in Last 24 Hours:     {stats.get('new_last_24h', 0)}")
    print("-" * 45)

    by_source = stats.get("by_source", {})
    source_rows = []
    for s_name, s_data in by_source.items():
        if s_data.get("items", 0) > 0 or s_data.get("usd", 0) > 0:
            source_rows.append([s_name, str(s_data.get("items", 0)), f"${s_data.get('usd', 0):,.2f}"])
    
    if source_rows:
        print("\nBreakdown by Source:")
        print(format_table(source_rows, ["Source", "Active Items", "Volume (USD)"]))


def cmd_get(client: ABFClient, args: argparse.Namespace) -> None:
    res = client.get_bounty(args.bounty_id)
    print(f"\n🔍 Bounty Details: {args.bounty_id}")
    print("-" * 50)
    print(json.dumps(res, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agent Bounty Feed CLI: Zero-dependency client for Web3 & AI bounties."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # earn-now
    subparsers.add_parser("earn-now", help="Fetch immediate high-yield live bounties")

    # list
    list_p = subparsers.add_parser("list", help="Query MCP bounties tool with custom filters")
    list_p.add_argument("--source", type=str, help="Comma-separated sources (e.g. frantic,taskmarket,direct)")
    list_p.add_argument("--min-usd", type=float, help="Minimum reward in USD")
    list_p.add_argument("--network", type=str, help="Payout network (base, solana, etc.)")
    list_p.add_argument("--exclude-requires", type=str, help="Exclude conditions: kyc,stake,github,human_only")
    list_p.add_argument("--limit", type=int, default=15, help="Max results (default: 15)")
    list_p.add_argument("--sort", type=str, default="reward", choices=["reward", "first_seen"], help="Sort order")

    # stats
    subparsers.add_parser("stats", help="Show ecosystem metrics and payout volumes")

    # get
    get_p = subparsers.add_parser("get", help="Inspect single bounty by ID")
    get_p.add_argument("bounty_id", type=str, help="Bounty ID (e.g. frantic:129)")

    args = parser.parse_args()
    client = ABFClient()

    try:
        if args.command == "earn-now":
            cmd_earn_now(client, args)
        elif args.command == "list":
            cmd_list(client, args)
        elif args.command == "stats":
            cmd_stats(client, args)
        elif args.command == "get":
            cmd_get(client, args)
    except Exception as e:
        sys.stderr.write(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
