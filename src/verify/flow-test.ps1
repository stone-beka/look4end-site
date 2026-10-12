<#
  flow-test.ps1 —— 交互链路功能测试（用 --dump-dom 读文本结果）

  用法（本机执行策略默认禁止运行未签名脚本，加 -ExecutionPolicy Bypass）：
    powershell -ExecutionPolicy Bypass -File .\verify\flow-test.ps1 `
        -Page "C:\...\视频工作流\soviet-press\index.html" -TestScript .\verify\example-flow-test.js

    # 验真实动画路径（不加桩，更慢但测的是真路径）
    powershell -ExecutionPolicy Bypass -File .\verify\flow-test.ps1 `
        -Page "C:\...\视频工作流\soviet-press\index.html" -TestScript .\verify\example-flow-test.js -NoStub

  契约：TestScript 是一段 JS，运行完后必须写：
        document.body.setAttribute('data-test-result', '…结果…')

  四个关键设计（都是踩过的坑）：
    1. 测试页必须生成在【被测页同目录】—— 否则相对路径的 css/js 静默不加载，
       你会看到一堆"什么都没发生"的假失败。
    2. reduced-motion 桩必须插在【第一个业务 <script> 之前】—— 插在 </body> 前
       是无效的，业务脚本在解析到它之前就已经执行并捕获了真实的 matchMedia。
    3. --dump-dom 的输出【重定向到文件】再读 —— 走管道拿不到。
    4. 断言"转场层已归位"这类异步收尾状态时必须【轮询】，不能只读一次。
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Page,
  [Parameter(Mandatory = $true)][string]$TestScript,
  [switch]$NoStub,                                   # 跳过 reduced-motion 桩，走真实动画路径
  [int]$BudgetMs = 30000,
  [string]$Edge
)

$ErrorActionPreference = 'Continue'
$fail = 0
function Fail($m) { $script:fail++; Write-Host "  [XX] $m" -ForegroundColor Red }
function Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }

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
if (-not $Edge) { Write-Host '找不到 Edge/Chrome' -ForegroundColor Red; exit 1 }

$Page = (Resolve-Path -LiteralPath $Page).Path
$TestScript = (Resolve-Path -LiteralPath $TestScript).Path
$dir = Split-Path $Page -Parent
$html = [IO.File]::ReadAllText($Page, [Text.Encoding]::UTF8)
$body = [IO.File]::ReadAllText($TestScript, [Text.Encoding]::UTF8)

Write-Host "被测页  : $Page" -ForegroundColor Cyan
Write-Host "测试脚本: $TestScript" -ForegroundColor Cyan
Write-Host ("模式    : " + $(if ($NoStub) { '真实动画路径' } else { 'reduced-motion 快路径（隔离状态机）' })) -ForegroundColor Cyan
Write-Host ''

# ---------- 1) 构造注入 ----------
$stubBlock = ''
if (-not $NoStub) {
  $stubBlock = @'
<script>
(function(){
  var orig = window.matchMedia.bind(window);
  window.matchMedia = function (q) {
    if (String(q).indexOf('prefers-reduced-motion') >= 0) {
      return { matches: true, media: q, addEventListener:function(){},
               removeEventListener:function(){}, addListener:function(){}, removeListener:function(){} };
    }
    return orig(q);
  };
})();
</script>
'@
}
$testBlock = "<script>`n" + $body + "`n</script>"
$patched = $html

# 🔴 桩插到【第一个 <script> 之前】：必须早于业务脚本执行
if ($stubBlock) {
  $idx = $patched.IndexOf('<script')
  if ($idx -lt 0) {
    Write-Host '被测页里没有 <script>，无法插入桩，请改用 -NoStub' -ForegroundColor Red
    exit 1
  }
  $patched = $patched.Substring(0, $idx) + $stubBlock + "`n" + $patched.Substring($idx)
}

# 测试脚本插到 </body> 之前（此时业务脚本已跑完，监听器都已就位）
if ($patched -notmatch '</body>') { Write-Host '被测页里找不到 </body>，无法注入' -ForegroundColor Red; exit 1 }
# 用字面 .Replace()：注入内容含 $ 与正则元字符，.Replace() 不需要转义
$patched = $patched.Replace('</body>', ($testBlock + "`n</body>"))

# ---------- 2) 测试页写进【被测页同目录】 ----------
$testPath = Join-Path $dir '_flow-test.html'
[IO.File]::WriteAllText($testPath, $patched, (New-Object Text.UTF8Encoding($false)))

$url = 'file:///' + ($testPath -replace '\\', '/')
$outF = Join-Path $env:TEMP ('flowtest-dom-{0}.txt' -f ([guid]::NewGuid().ToString('N').Substring(0, 8)))

try {
  # ---------- 3) 输出重定向到文件再读 ----------
  Start-Process -FilePath $Edge -ArgumentList @(
    '--headless=new', '--disable-gpu', '--no-sandbox',
    "--virtual-time-budget=$BudgetMs", '--dump-dom', $url
  ) -Wait -NoNewWindow -RedirectStandardOutput $outF `
       -RedirectStandardError (Join-Path $env:TEMP 'flowtest-err.txt') | Out-Null

  $dom = [IO.File]::ReadAllText($outF, [Text.Encoding]::UTF8)
  $m = [regex]::Match($dom, 'data-test-result="([^"]*)"')

  if (-not $m.Success) {
    Fail "没有取到测试结果（DOM 长度 $($dom.Length)）。检查：测试脚本是否抛异常、是否真的写了 data-test-result"
  } else {
    foreach ($line in ($m.Groups[1].Value -split ' ;; ')) {
      $line = $line.Trim()
      if (-not $line) { continue }
      if ($line -like 'OK:*')     { Ok ($line -replace '^OK:', '') }
      elseif ($line -like 'XX:*') { Fail ($line -replace '^XX:', '') }
      else                        { Write-Host "  [--] $line" -ForegroundColor DarkGray }
    }
  }
} finally {
  Remove-Item -LiteralPath $testPath -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $outF -Force -ErrorAction SilentlyContinue
}

Write-Host ''
if ($fail -eq 0) { Write-Host '全部通过 ✅' -ForegroundColor Green; exit 0 }
else { Write-Host "失败 $fail 项 ❌" -ForegroundColor Red; exit 1 }
