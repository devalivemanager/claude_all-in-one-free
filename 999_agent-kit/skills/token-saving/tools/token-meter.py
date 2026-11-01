#!/usr/bin/env python3
"""token-meter.py - where does my Claude Code bill go? (token-saving-kit, read-only, no install)

Reads the session transcripts Claude Code already writes (<config>/projects/<key>/*.jsonl)
and splits usage into input / cache write / cache read / output, with cost in USD and KRW.
Nothing is sent anywhere. Python 3 standard library only.

Usage:
  python token-meter.py                        # current folder's project, all of its sessions
  python token-meter.py D:/myproject           # another project
  python token-meter.py --all                  # every project under the config dir
  python token-meter.py --days 7               # only the last 7 days
  python token-meter.py --session 2dc3ecd6     # one session (id prefix)
  python token-meter.py --compare 2026-09-01..2026-09-10 2026-09-11..2026-09-20
  python token-meter.py --krw 1400 --price claude-opus-5-5=4,20

Pricing model (USD per 1M tokens): cache write 5m = 1.25 x input, cache write 1h = 2 x input,
cache read = 0.1 x input; thinking tokens are billed as output. The unit prices below are
DEFAULT list prices from a 2026-09 external source - check the official pricing page and
override with --price. Subscription users: read the cost% column as "share of my limit".

Idea credit: 「클로드 코드 토큰 계량기」(방구석컴퍼니, 2026-09-22) - this is an independent
implementation for token-saving-kit. Written 2026-10-02.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

PRICES = {  # model-id prefix : (input, output) USD per 1M tokens. Longer prefixes FIRST (startswith match).
    "claude-opus-5-5": (4.0, 20.0),    # [external 2026-09] not back-solved yet - verify
    "claude-sonnet-5-5": (2.0, 10.0),  # [external 2026-09] - verify
    "claude-opus-5": (5.0, 25.0),      # [back-solved] recorded costUSD 29.4393 matches exactly with 1h cache write
    "claude-sonnet-5": (2.0, 10.0),    # [back-solved] 108-run benchmark cost matches exactly (ratio 1.000)
    "claude-haiku-4-5": (1.0, 5.0),    # [back-solved] recorded costUSD matches (+2 web searches)
}
# Claude Code writes cache with the 1-hour TTL (logged as ephemeral_1h) -> 2 x input price.
W5M, W1H, READ = 1.25, 2.0, 0.1
CATS = ["input", "cache write 5m", "cache write 1h", "cache read", "output"]


def price_for(model):
    for k, v in PRICES.items():
        if model and model.startswith(k):
            return v
    return None


def project_key(path):
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(path).rstrip("\\/"))


def local_day(ts):
    """transcript timestamps are UTC ('...Z'); count them on the LOCAL calendar day"""
    try:
        return dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone().date().isoformat()
    except (ValueError, TypeError):
        return ""


def load_records(files, since=""):
    """one record per API response: (session, model, usage, local date 'YYYY-MM-DD')"""
    seen = {}
    for f in files:
        sid = os.path.basename(f)[:8]
        # skip whole files last modified before the period (fast even with GBs of history)
        if since and dt.date.fromtimestamp(os.path.getmtime(f)).isoformat() < since:
            continue
        try:
            fh = open(f, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                m = d.get("message") or {}
                u = m.get("usage")
                model = str(m.get("model") or "?")
                # only real model responses (skip '<synthetic>' placeholders and non-assistant lines)
                if not isinstance(u, dict) or d.get("type") != "assistant" or model.startswith("<"):
                    continue
                # one response is logged once per content block -> count it once (requestId is global)
                key = d.get("requestId") or m.get("id") or (sid, d.get("uuid"))
                seen[key] = (sid, model, u, local_day(d.get("timestamp")))
    return list(seen.values())


def tally(records):
    tok = dict.fromkeys(CATS, 0)
    usd = dict.fromkeys(CATS, 0.0)
    r = {"tok": tok, "usd": usd, "thinking": 0, "calls": 0, "unknown": {}, "model": {}, "session": {}}
    for sid, model, u, _day in records:
        r["calls"] += 1
        cc = u.get("cache_creation") or {}
        w1h = int(cc.get("ephemeral_1h_input_tokens") or 0)
        w5m = int(cc.get("ephemeral_5m_input_tokens") or 0)
        wtot = int(u.get("cache_creation_input_tokens") or 0)
        if w1h + w5m == 0 and wtot:
            w5m = wtot  # older logs without the 5m/1h split
        t = {"input": int(u.get("input_tokens") or 0), "cache write 5m": w5m, "cache write 1h": w1h,
             "cache read": int(u.get("cache_read_input_tokens") or 0), "output": int(u.get("output_tokens") or 0)}
        r["thinking"] += int((u.get("output_tokens_details") or {}).get("thinking_tokens") or 0)
        pr = price_for(model)
        if pr is None:
            r["unknown"][model] = r["unknown"].get(model, 0) + sum(t.values())
            continue
        pi, po = pr
        c = {"input": t["input"] * pi, "cache write 5m": t["cache write 5m"] * pi * W5M,
             "cache write 1h": t["cache write 1h"] * pi * W1H, "cache read": t["cache read"] * pi * READ,
             "output": t["output"] * po}
        for k in CATS:
            tok[k] += t[k]
            usd[k] += c[k] / 1e6
        cost = sum(c.values()) / 1e6
        r["model"][model] = r["model"].get(model, 0.0) + cost
        r["session"][sid] = r["session"].get(sid, 0.0) + cost
    return r


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def report(title, r, krw):
    T = sum(r["tok"].values())
    U = sum(r["usd"].values())
    print()
    print("== token meter : %s | %d API calls ==" % (title, r["calls"]))
    print("  %-15s %15s %7s %12s %14s %7s" % ("", "tokens", "tok%", "USD", "KRW", "cost%"))
    for k in CATS:
        print("  %-15s %15s %6.1f%% %12.2f %14s %6.1f%%" % (
            k, format(r["tok"][k], ","), pct(r["tok"][k], T), r["usd"][k],
            format(round(r["usd"][k] * krw), ","), pct(r["usd"][k], U)))
    print("  %-15s %15s %7s %12.2f %14s" % ("TOTAL", format(T, ","), "", U, format(round(U * krw), ",")))
    print("  (thinking tokens inside output: %s)" % format(r["thinking"], ","))
    if r["model"]:
        print("  by model : " + " | ".join("%s $%.2f" % (m, v) for m, v in sorted(r["model"].items(), key=lambda x: -x[1])))
    if r["session"]:
        top = sorted(r["session"].items(), key=lambda x: -x[1])[:5]
        print("  top sessions : " + " | ".join("%s $%.2f" % (s, v) for s, v in top))
    if r["unknown"]:
        print("  ! no price for (excluded): " + ", ".join("%s (%s tok)" % (m, format(n, ",")) for m, n in r["unknown"].items())
              + "  -> add --price model=input,output")


def in_range(day, rng):
    a, b = rng.split("..")
    return a <= day <= b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--session", default="")
    ap.add_argument("--days", type=int, default=0, help="only the last N days (0 = all)")
    ap.add_argument("--compare", nargs=2, metavar=("FROM..TO", "FROM..TO"), help="two date ranges YYYY-MM-DD..YYYY-MM-DD")
    ap.add_argument("--krw", type=float, default=1400.0, help="KRW per USD (default 1400, an assumption)")
    ap.add_argument("--price", action="append", default=[], help="model=input,output (USD per 1M)")
    a = ap.parse_args()

    for p in a.price:
        k, v = p.split("=", 1)
        i, o = v.split(",")
        PRICES[k] = (float(i), float(o))

    cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    if a.all:
        files, scope = glob.glob(os.path.join(cfg, "projects", "*", "*.jsonl")), "all projects"
    else:
        files, scope = glob.glob(os.path.join(cfg, "projects", project_key(a.project), "*.jsonl")), os.path.abspath(a.project)
    if a.session:
        files = [f for f in files if os.path.basename(f).startswith(a.session)]
    if not files:
        print("  no session files found for: %s (config dir: %s)" % (scope, cfg))
        return 1
    since = ""
    if a.compare:
        since = min(r.split("..")[0] for r in a.compare)
    elif a.days:
        since = (dt.date.today() - dt.timedelta(days=a.days - 1)).isoformat()
    recs = load_records(files, since)
    scope = "%s | %d session files" % (scope, len(files))

    if a.compare:
        r1 = tally([x for x in recs if in_range(x[3], a.compare[0])])
        r2 = tally([x for x in recs if in_range(x[3], a.compare[1])])
        report(a.compare[0], r1, a.krw)
        report(a.compare[1], r2, a.krw)
        u1, u2 = sum(r1["usd"].values()), sum(r2["usd"].values())
        c1, c2 = max(r1["calls"], 1), max(r2["calls"], 1)
        print()
        print("  change : total %+.1f%% | per API call %+.1f%%  (compare per call when the amount of work differs)" % (
            pct(u2 - u1, u1) if u1 else 0.0, pct(u2 / c2 - u1 / c1, u1 / c1) if u1 else 0.0))
    else:
        if a.days:
            recs = [x for x in recs if x[3] >= since]
            scope += " | since " + since
        report(scope, tally(recs), a.krw)

    print()
    print("  How to read: cache read is usually most of the TOKENS; its COST share is smaller (0.1x price)")
    print("  but in long sessions it can still be the biggest cost line. Cut the line with the largest cost%%.")
    print("  - output line     -> shorter answers, lower effort/thinking")
    print("  - cache read line -> shorter sessions (/clear, new session), smaller always-loaded files")
    print("  - cache write line-> fewer context resets of big prefixes, fewer large file reads")
    print("  KRW uses --krw %.0f (assumption). Prices are defaults - verify on the official pricing page." % a.krw)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
