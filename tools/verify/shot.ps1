<#
  shot.ps1 —— 用无头浏览器给每个界面状态截图

  用法：
    powershell -ExecutionPolicy Bypass -File .\verify\shot.ps1 -Page "C:\...\视频工作流\soviet-press\index.html" -Out "C:\...\视频工作流\soviet-press\_shots"

    # 自定义状态（标题=hash）：
    powershell -ExecutionPolicy Bypass -File .\verify\shot.ps1 -Page "C:\...\视频工作流\soviet-press\index.html" -States @{
      '首页' = ''; '海报1' = '#/p/0'; '文章展开' = '#/p/0/a' }

  设计要点（踩过的坑）：
    * 每个状态用 URL 直接落位再截，【不要】靠脚本驱动后截图 —— 时机不可控
    * --virtual-time-budget 可让外部字体等请求尽快完成
    * 截图必须【逐张看】。布局遮挡、颜色翻车这类问题读代码发现不了
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Page,
  [string]$Out = '_shots',
  [hashtable]$States,
  [int[]]$Widths = @(1440),          # 传多个宽度可一次出桌面 + 移动
  [int]$Height = 900,
  [int]$BudgetMs = 7000,
  [string]$Edge
)

$ErrorActionPreference = 'Continue'

if (-not $Edge) {
  $cands = @(
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
  )
  $Edge = $cands | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Edge) { Write-Host '找不到 Edge/Chrome，可用 -Edge 手动指定' -ForegroundColor Red; exit 1 }

$Page = (Resolve-Path -LiteralPath $Page).Path
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Force -Path $Out | Out-Null }
$Out = (Resolve-Path -LiteralPath $Out).Path

if (-not $States) {
  $States = [ordered]@{ '首页' = '' }
}

$base = 'file:///' + ($Page -replace '\\', '/')
$i = 0
foreach ($label in $States.Keys) {
  $hashUrl = $States[$label]
  foreach ($w in $Widths) {
    $i++
    $suffix = if ($Widths.Count -gt 1) { "-$w" } else { '' }
    $file = Join-Path $Out ('{0:D2}-{1}{2}.png' -f $i, ($label -replace '[\\/:*?"<>|]', '_'), $suffix)
    Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $Edge -ArgumentList @(
      '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
      "--window-size=$w,$Height", "--virtual-time-budget=$BudgetMs",
      "--screenshot=$file", ($base + $hashUrl)
    ) -Wait -NoNewWindow -RedirectStandardError (Join-Path $env:TEMP 'shot.err') | Out-Null

    if (Test-Path -LiteralPath $file) {
      $kb = [math]::Round((Get-Item -LiteralPath $file).Length / 1KB)
      Write-Host ("  [OK] {0}  ({1} KB)" -f (Split-Path $file -Leaf), $kb) -ForegroundColor Green
    } else {
      Write-Host ("  [XX] {0}" -f (Split-Path $file -Leaf)) -ForegroundColor Red
    }
  }
}
Write-Host "`n输出目录: $Out" -ForegroundColor Cyan
Write-Host '⚠️ 记得逐张打开看 —— 遮挡、溢出、配色翻车都只能这样发现。' -ForegroundColor Yellow
