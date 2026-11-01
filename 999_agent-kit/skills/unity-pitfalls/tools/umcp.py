"""Unity MCP(8888) 호출 도우미: python umcp.py <tool> '<json args>'

세션에 UnityMCP 도구가 보이지 않을 때 HTTP 로 직접 부른다(CoplayDev MCP for Unity, 2026-10-08 실측).
"""
import json
import sys
import urllib.request

U = "http://127.0.0.1:8888/mcp"
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def call(body, sid=None):
    h = dict(H)
    if sid:
        h["mcp-session-id"] = sid
    r = urllib.request.urlopen(urllib.request.Request(U, json.dumps(body).encode(), h), timeout=180)
    t = r.read().decode("utf-8")
    sid = r.headers.get("mcp-session-id") or sid
    for line in t.splitlines():
        if line.startswith("data:"):
            t = line[5:]
    return (json.loads(t) if t.strip() else {}), sid


if __name__ == "__main__":
    _, sid = call({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                              "clientInfo": {"name": "umcp", "version": "1"}}})
    call({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    res, _ = call({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                   "params": {"name": sys.argv[1],
                              "arguments": json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}}}, sid)
    r = res.get("result", res)
    sc = r.get("structuredContent")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(sc if sc is not None else r, ensure_ascii=False)[:3000])
