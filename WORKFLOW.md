# 工作流（给接手的人 / AI）

> **这份文件的目的**：把仓库 clone 下来，只看仓库里的东西，就能理解这套工作怎么运转、
> 并且能真的把内容改出来、重新构建、发布。
>
> 不需要任何仓库之外的信息。文中的本机路径都做了脱敏，只表达"有这么个目录"。

---

## 一、这个站是什么

`look4end.com` —— 一个纯静态的个人站，主线是**按时代陈列视觉美学**（穿越感来自每个时代自己的整页设计）。
没有框架、没有构建步骤、没有后端。托管在 Cloudflare Pages，连的是本仓库。

站点分两层：

| 层级 | 地址 | 是什么 |
|---|---|---|
| **时间门** | `/` | 极简索引：列出所有已发布时代，点进去。无 JS、无 Web 字体、无图片 |
| **时代包** | `/eras/<slug>/` | 一个美学世界，自包含：页面、样式、脚本、素材、笔记、动效、说明 |

当前只有一个时代：

| 时代 | 地址 | 内容 |
|---|---|---|
| 苏联构成主义 | `/eras/soviet-1923/` | 《ЛЕФ》报纸首页 → 三张海报（КЛИН / КНИГИ / БАШНЯ）→ 文章抽屉；`notes/` 11 篇设计笔记；`motion/` 20 秒无缝循环动效 + 3 篇经验 |

---

## 二、仓库结构（哪些是源、哪些是产物）

```
look4end-site/
├── index.html  core/eras.json  sitemap.xml  _redirects   ← 构建生成，不手改
├── core/gate.css                                          ← 门的基础样式（手写）
├── eras/
│   ├── _template/                                          ← 新时代脚手架（复制即开工）
│   └── soviet-1923/                                        ← 一个时代包
│       ├── era.json  index.html  era.css  era.js  AGENTS.md
│       ├── assets/
│       ├── src/notes/*.md  src/motion/*.md  build.py       ← 源与构建脚本
│       ├── notes/*.html                                    ← 产物
│       └── motion/index.html（手写原型）+ *.html（产物）
├── tools/
│   ├── build_all.py    era_lib.py    templates/gate.html
│   ├── tests/          纯逻辑单测（python -m unittest）
│   ├── verify/         static-check / flow-test / shot / route-test / run_all
│   └── render-frames.cjs                                   ← 离线逐帧出片
├── docs/
│   ├── ERA-CONTRACT.md                                     ← 时代契约
│   └── superpowers/                                        ← 设计 / 计划文档
├── 404.html  style.css  robots.txt  og-image.png  publish.bat
└── _本地素材-作品截图/                                       ← 本地素材，不发布
```

### 铁律：产物不要手改

`index.html`、`core/eras.json`、`sitemap.xml`、`_redirects`、`eras/*/notes/*.html`、
`eras/*/motion/*.html`（动效原型 `motion/index.html` 除外）都是**构建产物**，下一次构建会整个覆盖。

**手改的只有**：`core/gate.css`、`tools/templates/gate.html`、`eras/<slug>/` 下的
`index.html` / `era.css` / `era.js` / `entry.css` / `era.json` / `build.py` / `AGENTS.md`。

---

## 三、改内容 / 加时代

### 改某个时代的内容

```bash
# 笔记正文：改 eras/soviet-1923/src/notes/*.md
python eras/soviet-1923/build.py      # 或 python tools/build_all.py
```

### 加一个新时代

```bash
cp -r eras/_template eras/<slug>
# 改 era.json（slug 必须等于目录名 / order / name / years / summary / status）
# 改 AGENTS.md、index.html、era.css，写 src/notes/*.md
python tools/build_all.py             # 门里会自动出现这个时代
```

做新时代时**只需要读** `docs/ERA-CONTRACT.md` + `eras/_template/AGENTS.md` + 本时代的 `src/`。

---

## 四、构建 / 验证 / 发布

### 依赖

只有一个：**Python 3 + `markdown` 包**。

```bash
pip install markdown
```

### 构建

```bash
python tools/build_all.py
```

它会：依次跑每个时代的 `build.py` → 生成 `index.html` / `core/eras.json` / `sitemap.xml` / `_redirects`
→ 跑五项体检（断链 / 跨时代引用 / 注册表 / 产物类型 / 门无脚本无字体无图）。
任何一项失败退出码为 1。构建必须幂等：连续两次构建 `git diff` 为空。

### 验证

```bash
python tools/verify/run_all.py            # 构建 + 单测 + 路由 + 静态检查
python tools/verify/run_all.py --browser  # 再加无头浏览器交互链路与截图
```

单项也可以跑：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\verify\static-check.ps1 -Dir .\eras\soviet-1923
powershell -ExecutionPolicy Bypass -File .\tools\verify\flow-test.ps1 -Page .\eras\soviet-1923\index.html -TestScript .\tools\verify\example-flow-test.js
powershell -ExecutionPolicy Bypass -File .\tools\verify\shot.ps1 -Page .\index.html -Out .\_shots
```

> Windows 默认禁止运行未签名 `.ps1`，所以要加 `-ExecutionPolicy Bypass`。
> 这些脚本都带 UTF-8 BOM —— PowerShell 5.1 读没有 BOM 的 UTF-8 会乱码并报假语法错，改完要确认 BOM 还在。

**经验之谈**：能靠"读代码"发现的 bug 是少数。绝大多数问题要么靠**截图逐张看**、
要么靠**把数值算一遍**、要么靠**在真实浏览器里跑一遍**才能发现。
详见 `eras/soviet-1923/notes/09-踩坑清单.html`。

### 发布

**双击 `publish.bat`**，或手动：

```bash
git add -A
git commit -m "说明你改了什么"
git push
```

Cloudflare Pages 从仓库自动重建，约 30 秒后 `look4end.com` 就是新的。

---

## 五、视频线（出片）

`tools/render-frames.cjs` 是**离线逐帧渲染**脚本：用 CDP 驱动无头 Chrome，
按精确时刻 `t` 抓帧，不受浏览器垂直同步/光栅调度影响。出片走这条路，**不要在线录屏**。

```bash
node tools/render-frames.cjs <调试端口> <输出目录> <fps> <总帧数> [起始帧] [帧数] [宽] [高]
```

前置条件：本机要有 **ffmpeg**（编码用；抓帧本身不需要）。
完整管线、验收清单、本机环境的坑，见 `eras/soviet-1923/motion/02-视频制作·结构主义经验.html`。

---

## 六、站点技术事实（省得重新踩）

- **纯静态**，无框架、无构建步骤（构建是本地跑、产物进 git）。
- **有外部字体依赖**：时代页面引 Google Fonts；断网或大陆网络下会退化成系统字体，
  版面不塌，但风格特征会失去。门不加载任何 Web 字体。
- **中文文件名没问题**：`eras/soviet-1923/notes/01-美学谱系与形式法则.html` 线上正常。
- **`.html` 会 308 跳转**：Cloudflare Pages 会把 `x.html` 跳到 `x`（干净 URL），这是正常行为。
- **`.bat` 里不要写中文注释**：cmd.exe 会在某些字节位置从汉字中间切开一行。
- **旧地址 301**：`/notes/*`、`/motion/*`、`/assets/*` → `/eras/soviet-1923/…`，由 `_redirects` 生成。
- **部署链路**：GitHub `stone-beka/look4end-site` → Cloudflare Pages → `look4end.com`。
  域名在阿里云注册，DNS 托管在 Cloudflare——加解析记录要去 Cloudflare 后台。

---

## 七、2026-11-02 重构历史

站点原来是「根目录就是苏联报纸 + `/notes/` + `/motion/` 平级散件」。为了让以后每个美学时代
互不干扰，重构为「时间门 + 时代包」：

| 阶段 | 结果 |
|---|---|
| P0 | 规则层 / 门模板 / 调度器 / 脚手架 / 契约文档 |
| P1 | 苏联内容整体迁入 `eras/soviet-1923/`，产物哈希比对只允许 2 个文件变化（og:url + 3 条绝对链接）；旧地址 301 |
| P2 | `/` 换成生成的极简索引 |
| P3 | 文档分层（根 AGENTS / WORKFLOW / 每时代 AGENTS / 契约）、验证脚本参数化、一键验收 |

设计文档：`docs/superpowers/specs/2026-11-02-era-architecture-design.md`
实施计划：`docs/superpowers/plans/2026-11-02-era-refactor-plan.md`

---

## 八、一句话交接

> 改 `eras/<slug>/src/*.md` → `python tools/build_all.py` → `git push`。
> 别手改产物；加时代就复制 `eras/_template`。
