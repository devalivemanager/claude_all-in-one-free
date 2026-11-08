#!/usr/bin/env bash
# token-audit.sh - READ-ONLY token usage audit for Claude Code (token-saving-kit, macOS/Linux/Git Bash)
# Same sections as token-audit.ps1. Changes nothing.
#
# Usage:
#   bash token-audit.sh                 # audit the current folder as the project
#   bash token-audit.sh /path/to/project
#
# Needs only POSIX tools (find, wc, grep, sed, awk). python3 is optional (adds the MCP list).
# Written 2026-10-02.

PROJ="${1:-.}"
PROJ="$(cd "$PROJ" 2>/dev/null && pwd -P)" || { echo "  project dir not found: ${1:-.}"; exit 1; }
CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
NOTE="default"; [ -n "$CLAUDE_CONFIG_DIR" ] && NOTE="CLAUDE_CONFIG_DIR set"

# project key = absolute path with every non-alphanumeric char turned into '-'
# (on Git Bash use the Windows form of the path, which is what Claude Code uses there)
# TOKEN_AUDIT_POSIX_KEY=1 forces the POSIX form (e.g. Claude Code running inside WSL while you audit from Git Bash)
KEYSRC="$PROJ"
if [ -z "$TOKEN_AUDIT_POSIX_KEY" ] && command -v cygpath >/dev/null 2>&1; then KEYSRC="$(cygpath -w "$PROJ")"; fi
KEY="$(printf '%s' "$KEYSRC" | sed 's/[^A-Za-z0-9]/-/g')"

kb()  { awk -v b="$1" 'BEGIN{printf "%8.1f KB", b/1024}'; }
tok() { awk -v b="$1" 'BEGIN{printf "~%d tok", b/3}'; }   # rough, Korean-heavy text

echo
echo "== [1] config dir (fixing a different dir saves 0)  -> principle 38 =="
echo "  $CFG  ($NOTE)"
echo "  project : $PROJ"

echo
echo "== [2] effort (agent definition overrides global)  -> principles 12,13 =="
PY="$(command -v python3 || command -v python)"
# top-level effortLevel only (a grep would also catch the values inside modelSettings)
topeffort() {
  if [ -n "$PY" ]; then
    "$PY" -c 'import json,sys
v=(json.load(open(sys.argv[1],encoding="utf-8-sig")) or {}).get("effortLevel")
print(v if v else "")' "$1" 2>/dev/null
  else
    grep -o '"effortLevel"[[:space:]]*:[[:space:]]*"[^"]*"' "$1" | head -1 | sed 's/.*"\([^"]*\)"$/\1 (approx)/'
  fi
}
if [ -f "$CFG/settings.json" ]; then
  e="$(topeffort "$CFG/settings.json")"
  echo "  global effortLevel : ${e:-(unset)}"
  # 2026-10-04: a top-level effortLevel in USER settings is ignored by Opus 5.5 and later models -> show modelSettings too
  echo "  (user-level top-level effortLevel is IGNORED by Opus 5.5 and later models)"
  if grep -q '"modelSettings"' "$CFG/settings.json"; then
    if [ -n "$PY" ]; then
      "$PY" -c 'import json,sys
for k,v in (json.load(open(sys.argv[1],encoding="utf-8-sig")).get("modelSettings") or {}).items():
    print("  modelSettings %-18s: effortLevel=%s" % (k, (v or {}).get("effortLevel","(unset)")))' "$CFG/settings.json"
    else
      echo "  modelSettings      : present (install python3 to list)"
    fi
  else
    echo "  modelSettings      : (none) -> Opus 5.5 sessions run at the model default (medium)"
  fi
  [ -n "$CLAUDE_CODE_EFFORT_LEVEL" ] && echo "  CLAUDE_CODE_EFFORT_LEVEL : $CLAUDE_CODE_EFFORT_LEVEL (overrides settings)"
  for ps in "$PROJ/.claude/settings.json" "$PROJ/.claude/settings.local.json"; do
    [ -f "$ps" ] || continue
    pe="$(topeffort "$ps")"
    [ -n "$pe" ] && echo "  project effortLevel : $pe  (applies to ALL models)  $ps"
  done
else
  echo "  settings.json not found"
fi
for d in "$CFG/agents" "$PROJ/.claude/agents"; do
  [ -d "$d" ] || continue
  n=$(find "$d" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
  echo "  $d  ($n agents)"
  for f in "$d"/*.md; do
    [ -f "$f" ] || continue
    ef=$(grep -m1 '^effort:' "$f" | awk '{print $2}'); mo=$(grep -m1 '^model:' "$f" | awk '{print $2}')
    echo "effort=${ef:-none} model=${mo:-none}"
  done | sort | uniq -c | awk '{printf "    %-32s %s\n", $2" "$3, $1}'
done

echo
echo "== [3] always loaded every session (token figures are rough)  -> principles 24-28 =="
for p in "$PROJ/CLAUDE.md" "$PROJ/AGENTS.md" "$CFG/CLAUDE.md" "$CFG/projects/$KEY/memory/MEMORY.md"; do
  [ -f "$p" ] || continue
  b=$(wc -c < "$p" | tr -d ' ')
  extra=""; case "$p" in *AGENTS.md) extra="  (only if loaded/imported - check with /context)";; esac
  printf "  %s %-12s %s%s\n" "$(kb "$b")" "$(tok "$b")" "$p" "$extra"
done
if command -v python3 >/dev/null 2>&1; then
  python3 - "$PROJ" "$CFG" "$HOME" <<'PY'
import json, os, sys
proj, cfg, home = sys.argv[1], sys.argv[2], sys.argv[3]
def load(p):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except Exception: return None
m = load(os.path.join(proj, '.mcp.json'))
if m and m.get('mcpServers'): print('  .mcp.json servers  : ' + ', '.join(m['mcpServers']))
cj = os.path.join(os.environ.get('CLAUDE_CONFIG_DIR', ''), '.claude.json')
if not os.path.isfile(cj): cj = os.path.join(home, '.claude.json')
c = load(cj)
if c is not None:
    print('  user-scope MCP (.claude.json) : ' + (', '.join(c.get('mcpServers') or {}) or '(none)'))
    for k, v in (c.get('projects') or {}).items():
        if os.path.normcase(k.replace('\\', '/')) == os.path.normcase(proj.replace('\\', '/')) and (v or {}).get('mcpServers'):
            print('  local-scope MCP (.claude.json project) : ' + ', '.join(v['mcpServers']))
for s in (os.path.join(cfg, 'settings.json'), os.path.join(proj, '.claude', 'settings.json'), os.path.join(proj, '.claude', 'settings.local.json')):
    d = load(s)
    if d and isinstance(d.get('skillOverrides'), dict):
        off = sum(1 for x in d['skillOverrides'].values() if str(x) == 'off')
        print('  skillOverrides off : %4d  %s' % (off, s))
PY
else
  [ -f "$PROJ/.mcp.json" ] && echo "  .mcp.json present (install python3 to list servers)"
fi
echo "  (MCP actually loaded may be smaller with deferred tool loading - check /context)"
[ -d "$CFG/skills" ]  && echo "  user skills (SKILL.md) : $(find "$CFG/skills" -name SKILL.md | wc -l | tr -d ' ')"
[ -d "$CFG/plugins" ] && echo "  plugin skills (SKILL.md, includes marketplace copies) : $(find "$CFG/plugins" -name SKILL.md | wc -l | tr -d ' ')"

echo
echo "== [4] subagent calls actually recorded (all projects)  -> principles 10-11,34 =="
METAS="$(find "$CFG/projects" -path '*subagents*' -name '*.meta.json' 2>/dev/null)"
if [ -n "$METAS" ]; then
  echo "  total calls : $(printf '%s\n' "$METAS" | wc -l | tr -d ' ')"
  printf '%s\n' "$METAS" | while IFS= read -r f; do
    grep -o '"agentType"[[:space:]]*:[[:space:]]*"[^"]*"' "$f" | sed 's/.*"\([^"]*\)"$/\1/'
  done | sort | uniq -c | sort -rn | head -10 | awk '{printf "    %-30s %s\n", $2, $1}'
else
  echo "  total calls : 0"
fi
echo "  (model is mostly NOT recorded in meta - infer from agent definition, label it [inferred])"

echo
echo "== [5] session files of this project (top 5 by size)  -> principles 29-31 =="
SD="$CFG/projects/$KEY"
if [ -d "$SD" ]; then
  cnt=$(find "$SD" -maxdepth 1 -name '*.jsonl' | wc -l | tr -d ' ')
  tot=$(find "$SD" -maxdepth 1 -name '*.jsonl' -exec wc -c {} + 2>/dev/null | awk '$2!="total"{s+=$1} END{print s+0}')
  echo "  $cnt sessions, total $(kb "$tot")"
  find "$SD" -maxdepth 1 -name '*.jsonl' -exec wc -c {} + 2>/dev/null | awk '$2!="total"' | sort -rn | head -5 |
  while read -r b f; do
    l=$(wc -l < "$f" | tr -d ' ')
    flag=""; [ "$l" -ge 3000 ] && flag="  <- heavy (3000+)"; [ "$l" -ge 5000 ] && flag="  <- archive (5000+)"
    printf "  %s %7s lines  %s%s\n" "$(kb "$b")" "$l" "$(basename "$f" | cut -c1-12)" "$flag"
  done
else
  echo "  not found: $SD"
fi

echo
echo "Next: pick the biggest spot, write the expected number first, change ONE thing, run this again."
echo
