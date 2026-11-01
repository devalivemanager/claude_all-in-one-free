# 토큰 절약 설정 적용 스크립트 (token-saving-kit 판)
#
# 무엇을 하나
#   1) 전역 effortLevel 을 low 로 내린다
#   2) 서브에이전트 정의 중 effort: high / xhigh 만 medium 으로 내린다
#      (이미 low 인 것은 건드리지 않는다 - 올리면 오히려 늘어난다)
#
# 2026-10-02 수정 (반박 검토 지적 반영)
#   - CLAUDE_CONFIG_DIR 가 있으면 그 폴더를 고친다. 종전에는 ~/.claude 고정이라
#     다른 설정 폴더를 쓰는 세션에서는 「바꿨는데 효과 0」이 났다
#   - -ProjectDir 를 주면 그 프로젝트의 .claude\agents 도 함께 고친다
#   - -WhatIf 를 주면 대상만 보여 주고 아무것도 바꾸지 않는다
#   초판 2026-09-04 (전역 ~/.claude 고정판) → 2026-10-02 키트판
#
# 2026-10-03 수정 (코드 검토 지적 반영)
#   - 고친 파일을 UTF-8 BOM 없이 쓴다. 종전의 Set-Content -Encoding UTF8 은 PS 5.1 에서
#     BOM 을 붙였고, 에이전트 .md 의 첫 줄 --- (frontmatter) 앞에 BOM 이 끼었다
#   - settings.json 은 effortLevel 값 한 곳만 고친다. 종전에는 ConvertTo-Json 으로 파일 전체를
#     다시 써서 들여쓰기가 바뀌고 < > ' 가 < 처럼 바뀌어 diff 가 커졌다
#   - 에이전트 effort 줄을 바꿀 때 CRLF 의 CR 을 지우지 않는다. 종전에는 그 줄만 LF 로 바뀌었다
#
# 2026-10-04 수정 (공식 문서 대조 — Opus 5.5)
#   - 사용자 설정의 최상위 effortLevel 은 Opus 5.5 와 그 이후 모델이 무시한다(model-config · settings-reference).
#     종전 판은 최상위 키만 고쳐서, Opus 5.5 세션은 기본값 medium 으로 돌았다(「바꿨는데 효과 0」).
#   - 그래서 modelSettings.<모델>.effortLevel 도 low 로 건다($ModelKeys). modelSettings 가 아예 없을 때만 새로 넣고,
#     이미 있으면 서식을 지키려고 건드리지 않고 현재 값과 손으로 고칠 방법만 보여 준다.
#   - (같은 날 재수정 · 독립 검증 지적) 최상위 effortLevel 을 「깊이 1」 키로만 찾는다(Find-TopKey).
#     첫 판은 파일에서 처음 나오는 effortLevel 을 바꿔, modelSettings 가 앞에 있으면 그 안의 값을 고치거나 중단했다.
#     modelSettings 블록은 최상위 effortLevel 줄 바로 앞에 넣고, 바꾼 뒤 modelSettings 가 그대로인지 검사한다.
#
# 안전장치
#   - 바꾸기 전에 전부 백업한다. 되돌리려면 백업 폴더에서 복사하면 된다.
#   - 실행해도 지금 열려 있는 세션에는 안 걸린다. 세션을 다시 켜야 적용된다.
#
# 실행법 : PowerShell 에서
#   powershell -ExecutionPolicy Bypass -File .\apply-token-saving.ps1 -WhatIf
#   powershell -ExecutionPolicy Bypass -File .\apply-token-saving.ps1
#   powershell -ExecutionPolicy Bypass -File .\apply-token-saving.ps1 -ProjectDir D:\내프로젝트
param(
    [string]$ProjectDir = '',
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'

# 고친 파일은 UTF-8 (BOM 없음)으로 쓴다. 읽기는 BOM 이 있든 없든 ReadAllText 가 처리한다
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
function Write-NoBom([string]$Path, [string]$Text) { [System.IO.File]::WriteAllText($Path, $Text, $Utf8NoBom) }

# 최상위 effortLevel 을 무시하는 모델(Opus 5.5 와 그 이후). 새 모델이 나오면 여기에 더한다
$ModelKeys = @('claude-opus-5-5', 'claude-sonnet-5-5')
function Get-ModelEffort($j, [string]$m) {
    if ($null -eq $j.modelSettings) { return $null }
    $e = $j.modelSettings.$m
    if ($null -eq $e) { return $null }
    return $e.effortLevel
}

# JSON 텍스트에서 「최상위(깊이 1)」 키의 위치를 찾는다. modelSettings 안의 같은 이름 키는 건너뛴다.
# (2026-10-04 재수정 : 종전에는 파일에서 처음 나오는 effortLevel 을 바꿔, modelSettings 가 앞에 있으면 엉뚱한 값을 고쳤다)
function Find-TopKey([string]$s, [string]$key) {
    $depth = 0; $inStr = $false; $esc = $false
    for ($i = 0; $i -lt $s.Length; $i++) {
        $c = $s[$i]
        if ($inStr) {
            if ($esc) { $esc = $false } elseif ($c -eq [char]92) { $esc = $true } elseif ($c -eq [char]34) { $inStr = $false }
            continue
        }
        if ($c -eq [char]34) {
            if ($depth -eq 1 -and [string]::CompareOrdinal($s, $i, ('"' + $key + '"'), 0, $key.Length + 2) -eq 0) {
                $j = $i + $key.Length + 2
                while ($j -lt $s.Length -and [char]::IsWhiteSpace($s[$j])) { $j++ }
                if ($j -lt $s.Length -and $s[$j] -eq [char]58) { return $i }
            }
            $inStr = $true; continue
        }
        if ($c -eq [char]123 -or $c -eq [char]91) { $depth++ } elseif ($c -eq [char]125 -or $c -eq [char]93) { $depth-- }
    }
    return -1
}

$claude = $env:CLAUDE_CONFIG_DIR
$cfgNote = 'CLAUDE_CONFIG_DIR'
if ([string]::IsNullOrEmpty($claude)) { $claude = Join-Path $env:USERPROFILE '.claude'; $cfgNote = '기본값' }
$settings = Join-Path $claude 'settings.json'
$agentDirs = @(Join-Path $claude 'agents')
if ($ProjectDir -ne '') {
    $pa = Join-Path $ProjectDir '.claude\agents'
    if (Test-Path $pa) { $agentDirs += $pa } else { Write-Host "  참고 : 프로젝트 에이전트 폴더 없음 - $pa" }
}

Write-Host ''
Write-Host '== 토큰 절약 설정 적용 =='
Write-Host "  설정 폴더 : $claude ($cfgNote)"
foreach ($d in $agentDirs) { Write-Host "  에이전트 폴더 : $d" }

if (-not (Test-Path $settings)) {
    Write-Host "  중단 : settings.json 이 없습니다 - $settings"
    exit 1
}

# --- 0. 대상 미리 보기 ----------------------------------------------------
$json   = Get-Content $settings -Raw -Encoding UTF8 | ConvertFrom-Json
$before = $json.effortLevel
Write-Host "  전역 effortLevel : $before -> low"
$hasMS = $null -ne $json.modelSettings
foreach ($m in $ModelKeys) {
    $cur = Get-ModelEffort $json $m
    if ($hasMS) { Write-Host ("  modelSettings.{0} : {1} (modelSettings 가 이미 있어 건드리지 않는다)" -f $m, $(if ($cur) { $cur } else { '(없음)' })) }
    else        { Write-Host ("  modelSettings.{0} : (없음) -> low" -f $m) }
}
$targets = @()
foreach ($d in $agentDirs) {
    if (-not (Test-Path $d)) { continue }
    foreach ($f in Get-ChildItem $d -Filter *.md) {
        $t = Get-Content $f.FullName -Raw -Encoding UTF8
        if ($t -match '(?m)^effort:\s*(high|xhigh)\s*$') { $targets += $f }
    }
}
Write-Host ("  내릴 에이전트(high/xhigh -> medium) : {0} 개" -f $targets.Count)
foreach ($f in $targets) { Write-Host "    $($f.FullName)" }

if ($WhatIf) {
    Write-Host ''
    Write-Host '  [WhatIf] 여기까지. 아무것도 바꾸지 않았다.'
    exit 0
}

# --- 1. 백업 -------------------------------------------------------------
$stamp  = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path $claude "_backup_effort_$stamp"
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Copy-Item $settings $backup -Force
$i = 0
foreach ($d in $agentDirs) {
    if (-not (Test-Path $d)) { continue }
    $sub = Join-Path $backup ("agents_{0}" -f $i); $i++
    New-Item -ItemType Directory -Force -Path $sub | Out-Null
    Copy-Item (Join-Path $d '*.md') $sub -Force -ErrorAction SilentlyContinue
    Write-NoBom (Join-Path $sub '_원래위치.txt') $d
}
Write-Host "  백업 : $backup"

# --- 2. 전역 effortLevel = low -------------------------------------------
# 파일 전체를 다시 쓰지 않고 값 한 곳만 고친다 (서식·이스케이프 보존)
$raw   = [System.IO.File]::ReadAllText($settings)
$msBefore = (($raw | ConvertFrom-Json).modelSettings | ConvertTo-Json -Depth 6 -Compress)
$pos   = Find-TopKey $raw 'effortLevel'          # 최상위 키만 (modelSettings 안의 값은 건드리지 않는다)
if ($pos -ge 0) {
    $m = ([regex]'("effortLevel"\s*:\s*)("[^"]*"|null)').Match($raw, $pos)
    if (-not $m.Success -or $m.Index -ne $pos) {
        Write-Host "  중단 : 최상위 effortLevel 값을 읽지 못했습니다(문자열·null 이 아님). 원본은 그대로입니다 - $settings"
        exit 1
    }
    $new = $raw.Substring(0, $m.Index) + $m.Groups[1].Value + '"low"' + $raw.Substring($m.Index + $m.Length)
} elseif ($raw -match '^\s*\{\s*\}\s*$') {
    $new = '{ "effortLevel": "low" }'
} else {
    $nl  = if ($raw.Contains("`r`n")) { "`r`n" } else { "`n" }
    $new = ([regex]'\{').Replace($raw, '{' + $nl + '  "effortLevel": "low",', 1)
}
try { $chk = $new | ConvertFrom-Json } catch { $chk = $null }
$msAfter = if ($null -ne $chk) { ($chk.modelSettings | ConvertTo-Json -Depth 6 -Compress) } else { '<parse-failed>' }
if ($null -eq $chk -or $chk.effortLevel -ne 'low' -or $msAfter -ne $msBefore) {
    Write-Host "  중단 : 고친 settings.json 을 JSON 으로 다시 읽지 못했습니다. 원본은 그대로입니다 - $settings"
    exit 1
}
Write-NoBom $settings $new
Write-Host "  전역 effortLevel : $before -> low"

# --- 2b. 모델별 effortLevel = low (Opus 5.5 와 그 이후 모델) --------------
$raw2 = [System.IO.File]::ReadAllText($settings)
$j2   = $raw2 | ConvertFrom-Json
if ($null -eq $j2.modelSettings) {
    # 최상위 effortLevel 줄 바로 앞에 한 블록만 끼워 넣는다 (같은 들여쓰기, 나머지 서식 보존)
    $nl  = if ($raw2.Contains("`r`n")) { "`r`n" } else { "`n" }
    $p2  = Find-TopKey $raw2 'effortLevel'
    $ls  = if ($p2 -gt 0) { $raw2.LastIndexOf("`n", $p2 - 1) + 1 } else { -1 }
    $ind = if ($ls -ge 0) { $raw2.Substring($ls, $p2 - $ls) } else { 'x' }
    if ($ind.Trim().Length -eq 0) {
        $items = ($ModelKeys | ForEach-Object { $ind + '  "' + $_ + '": { "effortLevel": "low" }' }) -join (',' + $nl)
        $new2  = $raw2.Substring(0, $ls) + $ind + '"modelSettings": {' + $nl + $items + $nl + $ind + '},' + $nl + $raw2.Substring($ls)
    } else {
        # effortLevel 이 다른 내용과 같은 줄에 있으면(한 줄짜리 JSON 등) 여는 중괄호 바로 뒤에 넣는다
        $items = ($ModelKeys | ForEach-Object { '    "' + $_ + '": { "effortLevel": "low" }' }) -join (',' + $nl)
        $new2  = ([regex]'\{').Replace($raw2, '{' + $nl + '  "modelSettings": {' + $nl + $items + $nl + '  },', 1)
    }
    try { $chk2 = $new2 | ConvertFrom-Json } catch { $chk2 = $null }
    $bad = ($null -eq $chk2) -or ($chk2.effortLevel -ne 'low') -or (@($ModelKeys | Where-Object { (Get-ModelEffort $chk2 $_) -ne 'low' }).Count -gt 0)
    if ($bad) {
        Write-Host "  중단 : modelSettings 를 넣은 settings.json 을 다시 읽지 못했습니다. 최상위 effortLevel 까지만 바뀌었습니다 - $settings"
        exit 1
    }
    Write-NoBom $settings $new2
    Write-Host ("  modelSettings : {0} -> low" -f ($ModelKeys -join ', '))
} else {
    $notLow = @($ModelKeys | Where-Object { (Get-ModelEffort $j2 $_) -ne 'low' })
    if ($notLow.Count -gt 0) {
        Write-Host "  ★ modelSettings 가 이미 있어 건드리지 않았습니다. 아래 모델은 low 가 아닙니다 — 손으로 고치거나, 그 모델 세션에서 /effort low 를 입력하세요:"
        foreach ($m in $notLow) { Write-Host ("    {0} = {1}" -f $m, $(if (Get-ModelEffort $j2 $m) { Get-ModelEffort $j2 $m } else { '(없음 — 모델 기본값으로 돈다)' })) }
    } else {
        Write-Host "  modelSettings : 이미 low"
    }
}

# --- 3. 에이전트 high / xhigh 만 medium ----------------------------------
$changed = 0
foreach ($f in $targets) {
    $t = [System.IO.File]::ReadAllText($f.FullName)
    # 뒤쪽 공백과 CR 은 앞보기로만 확인하고 남긴다 (CRLF 파일의 줄바꿈 보존)
    $n = [regex]::Replace($t, '(?m)^(effort:[ \t]*)(high|xhigh)(?=[ \t]*\r?$)', '${1}medium')
    if ($n -ne $t) {
        Write-NoBom $f.FullName $n
        $changed++
    }
}
Write-Host "  서브에이전트 : $changed 개 -> medium"

# --- 4. 검증 -------------------------------------------------------------
Write-Host ''
Write-Host '== 검증 =='
$jv  = Get-Content $settings -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host "  effortLevel = $($jv.effortLevel)"
foreach ($m in $ModelKeys) { Write-Host ("  modelSettings.{0}.effortLevel = {1}" -f $m, $(if (Get-ModelEffort $jv $m) { Get-ModelEffort $jv $m } else { '(없음)' })) }
foreach ($d in $agentDirs) {
    if (-not (Test-Path $d)) { continue }
    Write-Host "  $d"
    foreach ($lv in 'low','medium','high','xhigh') {
        $c = @(Get-ChildItem $d -Filter *.md | Where-Object {
            (Get-Content $_.FullName -Raw -Encoding UTF8) -match "(?m)^effort:\s*$lv\s*$"
        }).Count
        Write-Host ("    {0,-6} {1} 개" -f $lv, $c)
    }
}
Write-Host '  high / xhigh 가 0 개면 정상입니다.'

Write-Host ''
Write-Host '  ★ 새 설정은 세션을 다시 켜야 걸립니다.'
Write-Host "  ★ 되돌리려면 : $backup 의 파일을 원래 자리로 복사 (agents_N 폴더의 _원래위치.txt 참고)"
Write-Host ''
