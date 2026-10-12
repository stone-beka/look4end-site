<#
  static-check.ps1 —— 静态检查：HTML 标签配平 / CSS 语法与变量 / JS 语法 / id 引用一致性

  用法：
    powershell -ExecutionPolicy Bypass -File .\verify\static-check.ps1 -Dir "C:\...\视频工作流\soviet-press"
    powershell -ExecutionPolicy Bypass -File .\verify\static-check.ps1 -Dir "C:\...\视频工作流\soviet-press" -Html index.html -Css press.css -Js press.js

  退出码：0 = 全部通过，1 = 有失败项（便于接进 CI）
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Dir,
  [string]$Html = 'index.html',
  [string]$Css  = 'press.css',
  [string]$Js   = 'press.js'
)

$ErrorActionPreference = 'Continue'
$fail = 0
function Fail($m) { $script:fail++; Write-Host "  [XX] $m" -ForegroundColor Red }
function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }

if (-not (Test-Path -LiteralPath $Dir)) { Write-Host "目录不存在: $Dir" -ForegroundColor Red; exit 1 }
$Dir = (Resolve-Path -LiteralPath $Dir).Path
Write-Host "检查目录: $Dir`n" -ForegroundColor Cyan

# ---------- 1) HTML 标签栈式配平 ----------
$htmlPath = Join-Path $Dir $Html
if (Test-Path -LiteralPath $htmlPath) {
  Write-Host '1) HTML 结构'
  $h = [IO.File]::ReadAllText($htmlPath, [Text.Encoding]::UTF8)
  # 去掉 script / style 内容，避免里面的 < > 干扰
  $clean = [regex]::Replace($h, '(?s)<script\b.*?</script>', '')
  $clean = [regex]::Replace($clean, '(?s)<style\b.*?</style>', '')

  $void = @('area','base','br','col','embed','hr','img','input','link','meta',
            'param','source','track','wbr')
  $stack = New-Object System.Collections.ArrayList
  $errs  = New-Object System.Collections.ArrayList
  $line  = 1
  foreach ($m in [regex]::Matches($clean, '<(\/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*?)(\/?)>')) {
    $line += ([regex]::Matches($clean.Substring(0, $m.Index), "`n")).Count
    $closing = $m.Groups[1].Value -eq '/'
    $name    = $m.Groups[2].Value.ToLower()
    $self    = $m.Groups[4].Value -eq '/'
    if ($void -contains $name -or $self) { continue }
    if (-not $closing) { [void]$stack.Add([pscustomobject]@{ N = $name; L = $line }) }
    else {
      if ($stack.Count -eq 0) { [void]$errs.Add("第 $line 行：多余的 </$name>") ; continue }
      $top = $stack[$stack.Count - 1]
      if ($top.N -eq $name) { $stack.RemoveAt($stack.Count - 1) }
      else { [void]$errs.Add("第 $line 行：</$name> 与第 $($top.L) 行的 <$($top.N)> 不匹配") }
    }
  }
  if ($errs.Count) { $errs | Select-Object -First 8 | ForEach-Object { Fail $_ } } else { Ok '标签嵌套配平' }
  if ($stack.Count) { $stack | ForEach-Object { Fail "未闭合 <$($_.N)> @ 第 $($_.L) 行" } } else { Ok '无未闭合标签' }

  $dup = ([regex]::Matches($h, '<[^>]*\sclass="[^"]*"[^>]*\sclass="')).Count
  if ($dup) { Fail "重复 class 属性 $dup 处" } else { Ok '无重复 class 属性' }
} else { Fail "找不到 $Html" }

# ---------- 2) CSS ----------
$cssPath = Join-Path $Dir $Css
if (Test-Path -LiteralPath $cssPath) {
  Write-Host "`n2) CSS"
  $c = [IO.File]::ReadAllText($cssPath, [Text.Encoding]::UTF8)
  $o = ([regex]::Matches($c, '\{')).Count
  $l = ([regex]::Matches($c, '\}')).Count
  if ($o -eq $l) { Ok "大括号配平 $o/$l" } else { Fail "大括号不配平：开=$o 闭=$l" }

  # 注释配平
  $co = ([regex]::Matches($c, '/\*')).Count
  $cc = ([regex]::Matches($c, '\*/')).Count
  if ($co -eq $cc) { Ok "注释配平 $co/$cc" } else { Fail "注释不配平：开=$co 闭=$cc" }

  # 变量定义 / 使用
  $def  = @([regex]::Matches($c, '(--[a-zA-Z0-9-]+)\s*:') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
  $used = @([regex]::Matches($c, 'var\((--[a-zA-Z0-9-]+)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
  $undef = @($used | Where-Object { $def -notcontains $_ })
  if ($undef.Count) { Fail "使用了未定义的变量：$($undef -join ', ')" }
  else { Ok "变量一致：定义 $($def.Count) / 使用 $($used.Count)" }

  # --- 可移植的设计规则自查（可按项目开关）---
  # 注意：先剥掉 /* */ 注释再查，否则「禁止 ease-in-out」这种说明文字会被误报。
  $code = [regex]::Replace($c, '(?s)/\*.*?\*/', '')
  $warn = @()
  if ($code -match 'ease-in-out') { $warn += '出现 ease-in-out（机械风格里通常是笔误）' }
  if ($code -match 'border-radius:\s*(?!0)\d') { $warn += '存在非零圆角（零圆角体系下应确认）' }
  # 硬阴影的模糊值应为 0：box-shadow 的第三个长度
  foreach ($m in [regex]::Matches($code, 'box-shadow:\s*([^;]+);')) {
    foreach ($layer in ($m.Groups[1].Value -split ',(?![^()]*\))')) {
      $nums = [regex]::Matches($layer, '(-?[\d.]+)px') | ForEach-Object { [double]$_.Groups[1].Value }
      if ($nums.Count -ge 3 -and $nums[2] -ne 0) { $warn += "硬阴影出现模糊值：$($layer.Trim())" }
    }
  }
  if ($warn.Count) { $warn | Sort-Object -Unique | ForEach-Object { Write-Host "  [!!] $_" -ForegroundColor Yellow } }
  else { Ok '设计规则自查（缓动 / 圆角 / 阴影模糊值）通过' }
} else { Fail "找不到 $Css" }

# ---------- 3) JS 语法 ----------
$jsPath = Join-Path $Dir $Js
if (Test-Path -LiteralPath $jsPath) {
  Write-Host "`n3) JS"
  $node = Get-Command node -ErrorAction SilentlyContinue
  if ($node) {
    & node --check $jsPath 2>&1 | ForEach-Object { Write-Host "      $_" }
    if ($LASTEXITCODE -eq 0) { Ok 'node --check 通过' } else { Fail "node --check 失败（退出码 $LASTEXITCODE）" }
  } else { Write-Host '  [!!] 本机没有 node，跳过 JS 语法校验' -ForegroundColor Yellow }

  # 引用的 id 是否都存在
  if (Test-Path -LiteralPath $htmlPath) {
    $h = [IO.File]::ReadAllText($htmlPath, [Text.Encoding]::UTF8)
    $ids = @([regex]::Matches([IO.File]::ReadAllText($jsPath, [Text.Encoding]::UTF8),
             "getElementById\('([^']+)'\)") | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
    $missing = @($ids | Where-Object { $h -notmatch ('id="' + [regex]::Escape($_) + '"') })
    if ($missing.Count) { Fail "JS 引用了 HTML 里不存在的 id：$($missing -join ', ')" }
    else { Ok "JS 引用的 $($ids.Count) 个 id 全部存在" }
  }
} else { Fail "找不到 $Js" }

# ---------- 4) 文档相对链接 ----------
$md = @(Get-ChildItem -File $Dir -Filter *.md -ErrorAction SilentlyContinue)
if ($md.Count) {
  Write-Host "`n4) 文档相对链接"
  $bad = 0; $total = 0
  foreach ($f in $md) {
    $t = [IO.File]::ReadAllText($f.FullName, [Text.Encoding]::UTF8)
    foreach ($m in [regex]::Matches($t, '\]\((\.\.?/[^)#]+)')) {
      $rel = $m.Groups[1].Value; $total++
      $p = [IO.Path]::GetFullPath((Join-Path $f.DirectoryName $rel))
      if (-not (Test-Path -LiteralPath $p)) { Fail "$($f.Name) -> $rel"; $bad++ }
    }
  }
  if ($bad -eq 0) { Ok "检查 $total 条链接，全部有效" }
}

Write-Host ''
if ($fail -eq 0) { Write-Host '全部通过 ✅' -ForegroundColor Green; exit 0 }
else { Write-Host "失败 $fail 项 ❌" -ForegroundColor Red; exit 1 }
