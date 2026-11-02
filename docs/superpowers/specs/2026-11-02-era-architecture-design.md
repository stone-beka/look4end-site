# Look4End 多时代架构设计：时间门 + 时代包

> 状态：已确认（2026-11-02）
> 范围：站点信息架构、目录约定、构建与验证链路、迁移步骤
> 不包含：单个时代的美学内容本身（下一步另立「学习美学的工作流」）

---

## 0. 一句话

站点 = **一个与时代无关的极简根层（时间门）** + **N 个物理独立的时代包**。
加一个美学时代 = 新增一个目录，根层代码零改动。

## 1. 背景与目标

现状（2026-11-02 实测）：`index.html` + `press.css` + `press.js` 本身就是苏联报纸，
`/notes/`、`/motion/` 是平级散件，全站没有「时代」维度。加第二个美学时，必须回改根层的
导航、样式、路由、构建脚本，并重读苏联那套代码——上下文会被上一个时代占满。

目标：

1. **可扩展**：新增时代只新增目录，不改既有时代的任何文件。
2. **上下文专注**：做新时代时只需要读 3 份文件（契约、模板说明、本时代说明）。
3. **易读框架**：源 / 产物 / 工具 / 文档四者边界清楚，任何一份文件都能单独解释自己。
4. **读者体验**：进站 → 选时代 → 整页进入一个世界（穿越感由时代页面承担）；
   时代之间互不串味。

## 2. 非目标

- 不做 SPA、不做全站统一转场系统、不做时间轴主页的视觉设计（门只做功能性索引）。
- 不引入新框架 / 打包器 / 运行时依赖。仍是纯静态 + Python 构建。
- 不重写苏联时代的视觉内容。迁移是「搬家」，不是「重做」。
- 本次不定义「如何研究一个美学」的方法论细节（下一步单独出规格）。

## 3. 术语

| 词 | 含义 |
|---|---|
| **门 / 时间门** | 根路径 `/` 的极简索引页，列出所有已发布时代，提供进入链接 |
| **时代 / era** | 一个美学世界，如「苏联构成主义 1923」「欧洲蒸汽时代 1891」 |
| **时代包** | `eras/<slug>/` 整个目录：页面、样式、脚本、素材、源、产物、说明 |
| **注册表** | 构建生成的 `core/eras.json`（门的渲染数据来源） |
| **到场节拍** | 时代页面加载时的入场动效，由时代自带，可选 |
| **旧地址** | 迁移前存在的 URL（`/notes/…`、`/motion/…`、`/assets/…`） |

## 4. 架构

```
读者
 └─ /（门，构建生成，无 JS）
     ├─ /soviet-1923/          时代包：报纸首页
     │    ├─ /soviet-1923/notes/…   该时代设计笔记（构建产物）
     │    └─ /soviet-1923/motion/…  该时代动效原型与经验（产物 + 手写）
     └─ /gaslight-1891/        （以后）另一个时代包
```

### 4.1 根层职责（只有三件）

1. 由构建生成极简索引页 `/index.html`（读注册表，静态输出）。
2. 生成 `sitemap.xml` 与 `_redirects`。
3. 提供与时代无关的基础样式（`core/gate.css`，几十行，可内联进生成页）。

**根层不做**：转场动画、时代切换状态机、字体加载、任何时代专属文案或色值。

### 4.2 时代包职责

时代包**自包含**：页面、样式、脚本、字体、素材、Markdown 源、构建脚本、说明文档全在自己的目录里。
时代之间零共享样式、零共享脚本、零相互引用。

### 4.3 生成物 vs 手写物

| 生成（不手改） | 手写 |
|---|---|
| `/index.html`（门） | `eras/<slug>/index.html` |
| `core/eras.json` | `eras/<slug>/era.css` / `era.js` |
| `sitemap.xml` | `eras/<slug>/motion/index.html`（动效原型） |
| `_redirects` | `eras/<slug>/src/**/*.md` |
| `eras/<slug>/notes/*.html` | `eras/<slug>/AGENTS.md` |
| `eras/<slug>/motion/*.html`（文档部分） | `tools/**`、`docs/**` |

## 5. 目标目录

```
网页制作工作区/
├── index.html                 ← 生成：时间门
├── core/
│   ├── gate.css               根层基础排版（无时代专属样式）
│   └── eras.json              ← 生成：注册表
├── eras/
│   ├── _template/             新时代脚手架（复制即开工，不发布）
│   │   ├── era.json
│   │   ├── index.html
│   │   ├── era.css
│   │   ├── entry.css          可选：到场节拍
│   │   ├── build.py
│   │   ├── AGENTS.md
│   │   ├── assets/
│   │   └── src/
│   │       ├── notes/README.md
│   │       └── doc.css
│   └── soviet-1923/           苏联包（现有内容整体迁入）
│       ├── era.json
│       ├── index.html         报纸（原 index.html）
│       ├── era.css / era.js   原 press.css / press.js
│       ├── entry.css          红幕拉开（可选）
│       ├── assets/lissitzky-wedge.jpg
│       ├── src/
│       │   ├── notes/01…10 + README.md + doc.css + kit/
│       │   └── motion/README.md + 01 + 02
│       ├── notes/             ← 构建产物（11 篇）
│       ├── motion/            ← 产物 + 手写原型 index.html
│       ├── build.py
│       └── AGENTS.md
├── tools/
│   ├── build_all.py           调度器：跑各 era build.py → 生成门/注册表/sitemap/redirects → 体检
│   ├── era_lib.py             纯函数：slug/order 校验、sitemap URL 映射、redirects 生成、门渲染
│   ├── templates/gate.html    门模板
│   ├── tests/                 纯逻辑单元测试（python -m unittest）
│   └── verify/                参数化检查脚本（沿用现有四个 + 新增隔离检查）
├── docs/
│   ├── ERA-CONTRACT.md        唯一的跨时代文档
│   └── superpowers/           设计/计划文档（不进 sitemap）
├── AGENTS.md                  根入口：≤80 行，只讲门 + 契约 + 命令
├── WORKFLOW.md                ← 重写为「门 + 时代包」版本
├── 404.html  style.css  robots.txt  og-image.png  publish.bat  保留
├── _redirects                 ← 生成：旧地址 301 + 私有路径 404
└── _本地素材-作品截图/         本地素材，不发布（按 `<slug>/` 分子目录存截图）
```

## 6. 时代包契约

### 6.1 `era.json` 字段

| 字段 | 必需 | 类型 | 说明 |
|---|---|---|---|
| `slug` | 是 | string | `^[a-z0-9]+(-[a-z0-9]+)*$`，建议 `<风格>-<代表年份>`；**等于目录名，发布后不可改**（改了等于换 URL） |
| `order` | 是 | int | 门上的排序（时间线顺序），全局唯一 |
| `name` | 是 | string | 门上的名称，如「苏联构成主义」 |
| `years` | 是 | string | 展示用年代，如「1919–1925」 |
| `summary` | 是 | string | 一句话，≤40 字，门上的副标题 |
| `status` | 是 | `published` \| `draft` | `draft` 不出现在门、不进 sitemap，但仍可构建与预览 |
| `entry` | 否 | string | 时代入口，默认 `index.html` |
| `notes` | 否 | `{dir,label}` | 笔记目录，默认 `{dir:"notes",label:"设计笔记"}`；无笔记则省略 |
| `motion` | 否 | `{entry,label}` | 动效入口，如 `{entry:"motion/index.html",label:"动效原型"}` |
| `arrival` | 否 | string | 到场节拍样式，默认 `entry.css`；文件不存在则跳过 |
| `legacy` | 否 | string[] | 旧路径前缀，如 `["/notes/","/motion/","/assets/"]`，构建生成 301 |
| `build` | 否 | string | 构建脚本，默认 `build.py` |

示例：

```json
{
  "slug": "soviet-1923",
  "order": 10,
  "name": "苏联构成主义",
  "years": "1919–1925",
  "summary": "红黑白三色、几何原语、硬边斜切——把海报当论证。",
  "status": "published",
  "entry": "index.html",
  "notes": { "dir": "notes", "label": "设计笔记" },
  "motion": { "entry": "motion/index.html", "label": "动效原型" },
  "arrival": "entry.css",
  "legacy": ["/notes/", "/motion/", "/assets/"]
}
```

### 6.2 必需 / 可选文件

必需：`era.json`、`index.html`、`AGENTS.md`、`build.py`（从 `_template` 复制）。
可选：`era.css`、`era.js`、`entry.css`、`assets/`、`src/`、`notes/`、`motion/`、`verify/`。

### 6.3 URL 规则

> **勘误（2026-11-02 实施时）**：时代包物理目录是 `eras/<slug>/`，静态托管下 URL 直接映射文件路径，
> 所以线上地址带 `eras/` 前缀。这样门可以用相对链接 `eras/<slug>/`，本地双击也能预览，
> 不需要 `_redirects` 代理层。以下表格为准。

| 内容 | 地址 |
|---|---|
| 门 | `/` |
| 时代入口 | `/eras/<slug>/` |
| 时代笔记 | `/eras/<slug>/notes/…` |
| 时代动效 | `/eras/<slug>/motion/…` |
| 时代素材 | `/eras/<slug>/assets/…` |

- 站内链接**一律相对路径**，禁止以 `/` 开头（保证本地双击可预览、迁移目录不炸）。
- 旧地址 301：`/<legacy>/*` → `/eras/<slug>/<legacy>:splat`。例：`/notes/01-…` → `/eras/soviet-1923/notes/01-…`。
- `_redirects` 由构建生成，不手写。

### 6.4 边界规则（构建期强制）

1. era 内文件不得引用其他 era、`core/` 内部实现或根 `tools/`。
2. 根层文件（`index.html`、`core/`）不得出现任何时代专属文案、色值、字体名。
3. era 的 CSS 只服务自己的文档；不得依赖别的 era 的 CSS 变量。
4. 每个 era 自带的字体声明只在自己的页面生效；门不加载任何 Web 字体。
5. 违反 1–4 任一条，`tools/build_all.py` 以非零退出码失败并指出文件与行号。

### 6.5 到场节拍（可选）

时代可以自带 `entry.css`，在页面加载时播放一段本时代的入场（如苏联红幕从上落下、蒸汽黑场渐显）。
约定：

- 只用 CSS 动画，不用 JS；时长 ≤ 900ms；不得阻塞可交互。
- 必须包在 `@media (prefers-reduced-motion: no-preference)` 内。
- 门不提供转场；从时代回门是普通链接跳转（硬切）。

## 7. 时间门规格（极简索引）

- **生成物**，由 `tools/templates/gate.html` + 注册表渲染；无 JS、无 Web 字体、无图片。
- 内容顺序：站点名（Look4End）→ 一句说明 → 时代列表 → 页脚（仓库链接 / 说明）。
- 每个时代一行：`年代 · 名称` + 一句话 summary + `进入 →`（用 `<a>` 真链接，不用按钮）。
- 排序按 `order`；`status:"draft"` 不出现。
- 样式上限：`core/gate.css` ≤ 80 行，系统字体，白底黑字，正文对比度 ≥ 4.5:1。
- 不做视觉设计——门只负责「能进得去」。

## 8. 学习美学的工作流（骨架，下一步细化）

每个时代都走同一条流水线；产物固定落在 `eras/<slug>/src/`，供后续阶段引用。

| 阶段 | 做什么 | 产物（固定路径） | 验收门槛 |
|---|---|---|---|
| 0 立项 | 定时代、slug、年代、研究问题、来源清单 | `era.json`（draft） | slug 合法、order 不冲突 |
| 1 考据 | 谱系、代表作、形式法则 | `src/notes/01-美学考据.md` | 每条结论标注来源；未验证的明确写「未验证」 |
| 2 设计系统 | 色板 / 字体 / 网格 / 动效 / 对比度 | `src/notes/02-设计系统.md` | 色值有对比度实测，字体有字符覆盖核实 |
| 3 素材与授权 | 素材来源、许可证、验证方式 | `src/notes/03-素材与授权.md` | 每个 URL 实际访问过；无法验证写「未找到」 |
| 4 技术配方 | 可复制 CSS/SVG/JS + 坑 + 兼容性 | `src/notes/04-技术配方.md` | 配方能在本仓跑通；兼容性有出处 |
| 5 页面实现 | 入口页 + 组件 + 到场节拍 | `index.html` / `era.css` / `era.js` | 静态检查通过；本地可预览 |
| 6 验证 | 静态 / 截图 / 功能 / 移动端 / reduced-motion | 截图归档到 `_本地素材-作品截图/<slug>/` | 逐张看过；链接 0 断 |
| 7 交付 | 构建、进 sitemap、发布 | `status:"published"` | 门上有入口；线上 200；301 实测 |

**上下文边界（做新时代时只读这些）**：

1. `docs/ERA-CONTRACT.md`（本契约的浓缩版）
2. `eras/_template/AGENTS.md`
3. `eras/<slug>/AGENTS.md`
4. 本 era 的 `src/`

不读：其他 era、根层实现、历史笔记。需要跨时代规则时，先改契约，再按契约改。

## 9. 构建与生成

### 9.1 `tools/build_all.py`

1. 扫描 `eras/*/era.json`（跳过 `_` 开头），校验字段与 slug/order 唯一性。
2. 依次运行每个 era 的 `build.py`（子进程，失败即整体失败并报 era 名）。
3. 生成 `core/eras.json`（只含 published）、`/index.html`、`sitemap.xml`、`_redirects`
   （旧地址 301 来自各 era 的 `legacy`；sitemap 不含 lastmod，保证构建幂等）。
4. 跑体检（9.3），任一失败退出码 1。

### 9.2 幂等

连续两次 `python tools/build_all.py`，`git diff --exit-code` 必须为空。
生成物内不得写入时间戳、绝对路径、随机数。

### 9.3 体检项

1. **断链**：产物 HTML 内所有相对链接指向存在的文件。
2. **隔离**：era 内无跨 era / `core/` / `tools/` 引用；根层无时代专属文案与色值。
3. **注册表**：slug 合法、order 唯一、draft 不出门、notes/motion 目录存在。
4. **产物类型**：产物目录只含 `.html`/`.css`/`.js`/图片，无 `.md`。
5. **门**：无 `<script>`、无 `fonts.googleapis.com`、无图片。

## 10. 验证与测试

| 层 | 手段 | 通过标准 |
|---|---|---|
| 纯逻辑 | `python -m unittest discover -s tools/tests -v`（注册表排序、slug 校验、redirects 生成、sitemap 映射、断链扫描） | 全绿 |
| 静态 | `tools/verify/static-check.ps1 -Era eras/soviet-1923`（沿用现有脚本，参数化） | 0 失败 |
| 截图 | `shot.ps1`：门、苏联入口、一张海报、文章抽屉、移动端 | 逐张人工看过 |
| 功能 | `flow-test.ps1`：报纸→海报→抽屉→ESC 逐级返回 | 状态与 URL 一致 |
| 线上 | 301 实测、sitemap 200、关键页 200、404 正常 | 全部符合 |

## 11. 迁移计划

| 阶段 | 内容 | 线上变化 | 验收 |
|---|---|---|---|
| **P0 骨架** | 建 `eras/_template`、`tools/build_all.py`、`tools/templates/gate.html`、`docs/ERA-CONTRACT.md`；不动现有页面 | 无 | `build_all.py` 跑通且 `git diff` 为空（0 个 era） |
| **P1 迁移** | 苏联整体迁入 `eras/soviet-1923/`；旧地址 301；`/` 暂 302 到 `/soviet-1923/` | URL 变、内容不变 | 旧 URL 全部 301 到新址；报纸两级返回正常；截图与迁移前一致 |
| **P2 切换** | `/` 换成生成的极简索引；删临时 302 | 首页变化 | 门列出 1 个时代，可进入；无 JS/字体/图片请求 |
| **P3 分层** | 根 `AGENTS.md` 瘦身、每 era `AGENTS.md`、`WORKFLOW.md` 重写、验证脚本参数化、归档本机旧克隆副本 | 无 | 新会话按根 AGENTS 能独立完成一次小改动 |

## 12. 风险与未决项

| 风险 | 对策 |
|---|---|
| 首页从报纸变成门，品牌观感变化 | 已接受；P1 期间 `/` 仍是报纸（302），随时可回滚 |
| 外链（作品集、视频推广）断掉 | 301 + 上线后逐条实测 |
| 整仓被 Cloudflare Pages 公开（含 `docs/`、`tools/`） | 已核实：`_redirects` 不支持 404 改写，无法用它挡住。当前**接受公开**（与现状一致）；若要隐藏，需改 Pages 构建输出目录，另立任务 |
| 两份工作副本改错（本机另有一份旧克隆） | 迁移完成后归档/删除该副本 |
| 字体越加越重 | 每个时代字体只在本时代页面加载；门零 Web 字体 |
| 新时代的构建脚本各写一份 | 从 `_template/build.py` 复制；构建逻辑本地化是刻意的（一改不会全炸） |

未决（实施前确认即可，不阻塞设计）：

- 第二个时代的 slug 与年份（暂定 `gaslight-1891`，以实际考据为准）。
- 门上的站点一句说明文案。
- 是否给门加一个「按年代排序 / 按开发顺序」切换（当前只按 `order`）。

## 13. 参考

- 现有工作流：[`../../WORKFLOW.md`](../../WORKFLOW.md)
- 现有入口说明：[`../../AGENTS.md`](../../AGENTS.md)
- 现有设计笔记（将整体迁入苏联包）：`src/notes/`、`notes/`
- 现有动效原型（将整体迁入苏联包）：`motion/`、`src/motion/`
