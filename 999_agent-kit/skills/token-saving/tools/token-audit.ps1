# token-audit.ps1 - READ-ONLY token usage audit for Claude Code (token-saving-kit)
# Changes nothing. Measures where tokens leak so you fix the biggest spot only.
#
# Usage (from the project folder you want to audit):
#   powershell -ExecutionPolicy Bypass -File <kit>\tools\token-audit.ps1
#   powershell -ExecutionPolicy Bypass -File <kit>\tools\token-audit.ps1 -ProjectDir D:\path\to\project
#
# Written 2026-10-02. Output is ASCII on purpose (no BOM/encoding issues on PowerShell 5.1).
param(
    [string]$ProjectDir = (Get-Location).Path,
    [int]$Top = 5
)
$ErrorActionPreference = 'Continue'
# 2026-10-02 fix: normalize path so '.', relative paths and a trailing backslash map to the right project key
try { $ProjectDir = (Resolve-Path -LiteralPath $ProjectDir -ErrorAction Stop).Path } catch { Write-Host ("  project dir not found: {0}" -f $ProjectDir); exit 1 }
$ProjectDir = $ProjectDir.TrimEnd([char]92, [char]47)

# 2026-10-02 cross-platform: Windows PowerShell 5.1 and PowerShell 7 (Windows/macOS/Linux)
$HomeDir = $env:USERPROFILE; if ([string]::IsNullOrEmpty($HomeDir)) { $HomeDir = $HOME }
function P { [System.IO.Path]::Combine([string[]]$args) }
function ReadJson($path) {
    # returns a case-sensitive dictionary (keys like D:/x and d:/x can coexist in .claude.json)
    $raw = Get-Content $path -Raw -Encoding UTF8
    if ($PSVersionTable.PSVersion.Major -ge 6) { return ($raw | ConvertFrom-Json -AsHashtable) }
    Add-Type -AssemblyName System.Web.Extensions
    $ser = New-Object System.Web.Script.Serialization.JavaScriptSerializer
    $ser.MaxJsonLength = [int]::MaxValue
    return $ser.DeserializeObject($raw)
}
# cast to the interface: Dictionary (PS 5.1) has no public .Contains(), Hashtable (PS 7) has no .ContainsKey() on every type
function Has($d, $k) { return ($null -ne $d) -and ($d -is [System.Collections.IDictionary]) -and ([System.Collections.IDictionary]$d).Contains($k) -and ($null -ne $d[$k]) }

function KB($b) { '{0,8:N1} KB' -f ($b / 1KB) }
function Tok($b) { '~{0:N0} tok' -f ($b / 3) }   # ROUGH: ~3 bytes/token for Korean-heavy text; English/code differs

# --- [1] which config dir is really used ------------------------------------
$cfg = $env:CLAUDE_CONFIG_DIR
$cfgNote = 'CLAUDE_CONFIG_DIR set'
if ([string]::IsNullOrEmpty($cfg)) { $cfg = P $HomeDir '.claude'; $cfgNote = 'default' }
Write-Host ''
Write-Host '== [1] config dir (fixing a different dir saves 0)  -> principle 38 =='
Write-Host ("  {0}  ({1})" -f $cfg, $cfgNote)
Write-Host ("  project : {0}" -f $ProjectDir)

# --- [2] effort: global and per-agent (agent effort overrides global) -------
Write-Host ''
Write-Host '== [2] effort (agent definition overrides global)  -> principles 12,13 =='
$settings = Join-Path $cfg 'settings.json'
if (Test-Path $settings) {
    try {
        $j = Get-Content $settings -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-Host ("  global effortLevel : {0}" -f $(if ($j.effortLevel) { $j.effortLevel } else { '(unset)' }))
        # 2026-10-04: a top-level effortLevel in USER settings is ignored by Opus 5.5 and later models -> show modelSettings too
        Write-Host '  (user-level top-level effortLevel is IGNORED by Opus 5.5 and later models)'
        if ($j.modelSettings) {
            foreach ($mp in $j.modelSettings.PSObject.Properties) { Write-Host ("  modelSettings {0,-18}: effortLevel={1}" -f $mp.Name, $(if ($mp.Value.effortLevel) { $mp.Value.effortLevel } else { '(unset)' })) }
        } else { Write-Host '  modelSettings      : (none) -> Opus 5.5 sessions run at the model default (medium)' }
        if ($env:CLAUDE_CODE_EFFORT_LEVEL) { Write-Host ("  CLAUDE_CODE_EFFORT_LEVEL : {0} (overrides settings)" -f $env:CLAUDE_CODE_EFFORT_LEVEL) }
        foreach ($ps in @((P $ProjectDir '.claude' 'settings.json'), (P $ProjectDir '.claude' 'settings.local.json'))) {
            if (-not (Test-Path $ps)) { continue }
            try { $pj = Get-Content $ps -Raw -Encoding UTF8 | ConvertFrom-Json; if ($pj.effortLevel) { Write-Host ("  project effortLevel : {0}  (applies to ALL models)  {1}" -f $pj.effortLevel, $ps) } } catch {}
        }
        if ($j.env -and $j.env.CLAUDE_CODE_MAX_OUTPUT_TOKENS) { Write-Host ("  MAX_OUTPUT_TOKENS  : {0}" -f $j.env.CLAUDE_CODE_MAX_OUTPUT_TOKENS) }
        if ($j.cleanupPeriodDays) { Write-Host ("  cleanupPeriodDays  : {0}" -f $j.cleanupPeriodDays) }
    } catch { Write-Host '  settings.json parse failed' }
} else { Write-Host '  settings.json not found' }

foreach ($ad in @((P $cfg 'agents'), (P $ProjectDir '.claude' 'agents'))) {
    if (-not (Test-Path $ad)) { continue }
    $files = @(Get-ChildItem $ad -Filter *.md -ErrorAction SilentlyContinue)
    $cnt = @{}
    foreach ($f in $files) {
        $t = Get-Content $f.FullName -Raw -Encoding UTF8
        $e = 'none'; if ($t -match '(?m)^effort:\s*(\S+)') { $e = $Matches[1] }
        $m = 'none'; if ($t -match '(?m)^model:\s*(\S+)') { $m = $Matches[1] }
        $k = "effort=$e model=$m"; $cnt[$k] = 1 + [int]$cnt[$k]
    }
    Write-Host ("  {0}  ({1} agents)" -f $ad, $files.Count)
    $cnt.GetEnumerator() | Sort-Object Name | ForEach-Object { Write-Host ("    {0,-32} {1}" -f $_.Name, $_.Value) }
}

# --- [3] always-loaded files (paid every session) ---------------------------
Write-Host ''
Write-Host '== [3] always loaded every session (token figures are rough)  -> principles 24-28 =='
$projKey = ($ProjectDir -replace '[^A-Za-z0-9]', '-')
$memDir = P $cfg 'projects' $projKey 'memory'
$always = @(
    (Join-Path $ProjectDir 'CLAUDE.md'),
    (Join-Path $ProjectDir 'AGENTS.md'),
    (Join-Path $cfg 'CLAUDE.md'),
    (Join-Path $memDir 'MEMORY.md')
)
foreach ($p in $always) {
    if (Test-Path $p) {
        $b = (Get-Item $p).Length
        $note = ''; if ($p -like '*AGENTS.md') { $note = '  (only if loaded/imported - check with /context)' }
        Write-Host ("  {0} {1,-12} {2}{3}" -f (KB $b), (Tok $b), $p, $note)
    }
}
$mcp = Join-Path $ProjectDir '.mcp.json'
if (Test-Path $mcp) {
    try { $mj = Get-Content $mcp -Raw -Encoding UTF8 | ConvertFrom-Json
          Write-Host ("  .mcp.json servers  : {0}" -f (($mj.mcpServers.PSObject.Properties.Name) -join ', ')) } catch {}
}
# user-scope / per-project MCP registered in ~/.claude.json (not in .mcp.json)
$cj = P $HomeDir '.claude.json'
if (-not [string]::IsNullOrEmpty($env:CLAUDE_CONFIG_DIR)) { $alt = P $env:CLAUDE_CONFIG_DIR '.claude.json'; if (Test-Path $alt) { $cj = $alt } }
if (Test-Path $cj) {
    try {
        $cjo = ReadJson $cj
        $u = @(); if (Has $cjo 'mcpServers') { $u = @($cjo['mcpServers'].Keys) }
        Write-Host ("  user-scope MCP (.claude.json) : {0}" -f $(if ($u.Count) { $u -join ', ' } else { '(none)' }))
        $pk = $ProjectDir.Replace([string][char]92, '/')
        if (Has $cjo 'projects') {
            foreach ($name in @($cjo['projects'].Keys)) {
                $pv = $cjo['projects'][$name]
                if ($name.Replace([string][char]92, '/') -ieq $pk -and (Has $pv 'mcpServers')) {
                    $l = @($pv['mcpServers'].Keys)
                    if ($l.Count) { Write-Host ("  local-scope MCP (.claude.json project) : {0}" -f ($l -join ', ')) }
                }
            }
        }
    } catch { Write-Host '  .claude.json parse failed (MCP list may be incomplete)' }
}
Write-Host '  (MCP actually loaded may be smaller with deferred tool loading - check /context)'
$skillDir = Join-Path $cfg 'skills'
if (Test-Path $skillDir) {
    $sk = @(Get-ChildItem $skillDir -Recurse -Filter SKILL.md -ErrorAction SilentlyContinue).Count
    Write-Host ("  user skills (SKILL.md) : {0}" -f $sk)
}
$plugDir = Join-Path $cfg 'plugins'
if (Test-Path $plugDir) {
    $pk = @(Get-ChildItem $plugDir -Recurse -Filter SKILL.md -ErrorAction SilentlyContinue).Count
    Write-Host ("  plugin skills (SKILL.md, includes marketplace copies) : {0}" -f $pk)
}
# skills turned off with "skillOverrides": { "<skill>": "off" }  (principle 30)
foreach ($sf in @((P $cfg 'settings.json'), (P $ProjectDir '.claude' 'settings.json'), (P $ProjectDir '.claude' 'settings.local.json'))) {
    if (-not (Test-Path $sf)) { continue }
    try {
        $so = ReadJson $sf
        if (Has $so 'skillOverrides') {
            $off = @($so['skillOverrides'].Keys | Where-Object { "$($so['skillOverrides'][$_])" -eq 'off' }).Count
            Write-Host ("  skillOverrides off : {0,4}  {1}" -f $off, $sf)
        }
    } catch {}
}

# --- [4] delegation actually used (not just defined) ------------------------
Write-Host ''
Write-Host '== [4] subagent calls actually recorded (all projects)  -> principles 10-11,34 =='
$metas = @(Get-ChildItem (Join-Path $cfg 'projects') -Recurse -Filter *.meta.json -ErrorAction SilentlyContinue |
           Where-Object { $_.FullName -match 'subagents' })
$byType = @{}
foreach ($m in $metas) {
    try { $o = Get-Content $m.FullName -Raw -Encoding UTF8 | ConvertFrom-Json; $t = $o.agentType } catch { $t = '?' }
    if (-not $t) { $t = '?' }
    $byType[$t] = 1 + [int]$byType[$t]
}
Write-Host ("  total calls : {0}" -f $metas.Count)
$byType.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10 |
    ForEach-Object { Write-Host ("    {0,-30} {1}" -f $_.Name, $_.Value) }
Write-Host '  (model is mostly NOT recorded in meta - infer from agent definition, label it [inferred])'

# --- [5] session bloat: line count matters more than size ----------------
Write-Host ''
Write-Host ('== [5] session files of this project (top {0} by size)  -> principles 29-31 ==' -f $Top)
$sessDir = P $cfg 'projects' $projKey
if (Test-Path $sessDir) {
    $js = @(Get-ChildItem $sessDir -Filter *.jsonl -ErrorAction SilentlyContinue | Sort-Object Length -Descending)
    $sum = ($js | Measure-Object Length -Sum).Sum
    Write-Host ("  {0} sessions, total {1}" -f $js.Count, (KB $sum))
    foreach ($f in ($js | Select-Object -First $Top)) {
        $lines = 0; $r = [System.IO.File]::OpenText($f.FullName)
        try { while ($null -ne $r.ReadLine()) { $lines++ } } finally { $r.Close() }
        $flag = ''; if ($lines -ge 5000) { $flag = '  <- archive (5000+)' } elseif ($lines -ge 3000) { $flag = '  <- heavy (3000+)' }
        Write-Host ("  {0} {1,7} lines  {2}{3}" -f (KB $f.Length), $lines, $f.Name.Substring(0, [Math]::Min(12, $f.Name.Length)), $flag)
    }
} else { Write-Host ("  not found: {0}" -f $sessDir) }

Write-Host ''
Write-Host 'Next: pick the biggest spot, write the expected number first, change ONE thing, run this again.'
Write-Host ''
