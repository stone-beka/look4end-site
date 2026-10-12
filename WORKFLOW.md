# 工作流（给接手的人 / AI）

> **这份文件的目的**：把仓库 clone 下来，只看仓库里的东西，就能理解这套工作怎么运转、
> 并且能真的把内容改出来、重新构建、发布。
>
> 不需要任何仓库之外的信息。文中的本机路径都做了脱敏（`C:\...\xxx\`），
> 只表达"有这么个目录"，不暴露完整路径。

---

## 一、这个站是什么

`look4end.com` —— 一个纯静态个人站，主题是**构成主义（Constructivism）**。
没有框架、没有构建步骤、没有后端。托管在 Cloudflare Pages，连的是本仓库。

站上三层：

| 层级 | 地址 | 是什么 |
|---|---|---|
| **创作** | `/` | 《ЛЕФ》构成主义报纸 → 三张海报（КЛИН 楔子 / КНИГИ 书籍 / БАШНЯ 塔）。点击海报有红色幕布转场，底部文章条点击上滑展开，`ESC` 收回（与浏览器后退键同一条路径） |
| **设计笔记** | `/notes/` | HTML 设计经验 11 篇：构成主义美学考据 + 可跨项目复用的规则与踩坑 + 可运行的样式指南 |
| **视频设计** | `/motion/` | 动效原型（构成主义 20 秒无缝循环）+ 动效设计理念 + 视频制作经验 3 篇 |

---

## 二、仓库结构（哪些是源、哪些是产物）

```
look4end-site/
├── index.html  press.css  press.js  assets/     ← 首页（创作）。手写，不是产物
├── notes/                                        ← 设计笔记【构建产物】
├── motion/                                       ← 视频设计【构建产物】
│   └── index.html                                ← 例外：动效原型，手写单文件，不走构建
├── src/                                          ← ★ 全部源与工具
│   ├── notes/          .md 源 + build.py + kit/ + doc.css
│   ├── motion/         .md 源 + build.py
│   ├── verify/         验证脚本（静态检查 / 截图 / 功能测试 / 单元测试）
│   └── tools/          render-frames.cjs（离线逐帧出片）
├── WORKFLOW.md                                   ← 本文件
├── publish.bat                                   ← 双击发布
└── 404.html  style.css  robots.txt  sitemap.xml  og-image.png
```

### 铁律：`notes/` 和 `motion/` 里的 `.html` 不要手改

它们是构建产物，下一次构建会**整个覆盖**。要改正文，改 `src/` 里的 `.md`，然后重新构建。

**手改的只有这些**：

| 想改什么 | 改哪儿 |
|---|---|
| 首页（报纸 / 海报 / 转场） | `index.html` + `press.css` + `press.js` |
| 动效原型 | `motion/index.html`（独立单文件） |
| 配色、字体、间距、网格 | `src/notes/kit/kv.css` → 构建后进 `notes/kit/kv.css` |
| 文档页版式 | `src/notes/doc.css` → 构建后进 `notes/doc.css` |
| 错误页 | `404.html` |
| 分享卡片图 | `og-image.png` |

> ⚠️ 容易踩的坑：`notes/kit/kv.css` 看起来像"手改的样式表"，但它其实是
> `src/notes/kit/kv.css` 的副本。直接改 `notes/` 那份，下次构建就没了。

---

## 三、改内容 → 构建 → 发布

### 依赖

只有一个：**Python 3 + `markdown` 包**。

```bash
pip install markdown
```

（脚本只用标准库 + python-markdown，没有别的依赖。）

### 重新构建

两个脚本都会**自动判断产物目录**：放在 `src/<名字>/` 下就写到仓库的 `<名字>/`。
所以在仓库里直接跑就行，不用参数：

```bash
python src/notes/build.py      # 重建 notes/
python src/motion/build.py     # 重建 motion/（不碰 motion/index.html）
```

想指定别处就加 `--out`：

```bash
python src/notes/build.py --out /某处/notes
```

脚本会自己做四项自检，任何一项不过就在输出里告警：

1. **围栏代码块成对**（``` 出现奇数次 = 没闭合，会把后半篇整个吞成代码块）
2. **标题数对得上**（源里的 `#` 行数 vs 产物里的 `<h1..h4>` 数）
3. **链接改写数对得上**（源里几条站内 `.md` 链接，产物里就该有几个 `.html` 链接）
4. **产物里只有 `.html` 和 `.css`**

> 这三条不是摆设。构建这套站点时，第 1 条和第 3 条各抓到过一次真错
> ——一次是把整篇变成了代码块，一次是链接全废。

### 发布

```bash
git add -A
git commit -m "说明你改了什么"
git push
```

或者双击 `publish.bat`（它做的就是上面三步，外加"上次没推成功的补推"）。

**Cloudflare Pages 会从仓库自动重建，约 30 秒后 `look4end.com` 就是新的。**

---

## 四、验证（改完的东西真的对吗）

`src/verify/` 里有四个脚本。全部参数化（`-Dir` / `-Page`），换项目改路径就能用。

> Windows 默认禁止运行未签名 `.ps1`，所以要加 `-ExecutionPolicy Bypass`。
> 这些 `.ps1` 都带 UTF-8 BOM —— PowerShell 5.1 读**没有 BOM** 的 UTF-8 会乱码并报假语法错。

```powershell
# 1) 静态检查：HTML 标签配平 / CSS 语法与变量 / JS 语法 / id 引用 / 文档链接
powershell -ExecutionPolicy Bypass -File .\src\verify\static-check.ps1 -Dir .\notes

# 2) 纯逻辑单元测试（不需要浏览器）
node .\src\verify\route-test.js

# 3) 交互链路功能测试（无头浏览器，用 --dump-dom 读文本结果）
powershell -ExecutionPolicy Bypass -File .\src\verify\flow-test.ps1 `
  -Page .\index.html -TestScript .\src\verify\example-flow-test.js

# 4) 多状态截图（记得逐张看）
powershell -ExecutionPolicy Bypass -File .\src\verify\shot.ps1 `
  -Page .\index.html -Out .\_shots
```

**经验之谈**：能靠"读代码"发现的 bug 是少数。绝大多数问题要么靠**截图逐张看**、
要么靠**把数值算一遍**、要么靠**在真实浏览器里跑一遍**才能发现。
详见 `notes/09-踩坑清单.html`。

---

## 五、视频线（出片）

`src/tools/render-frames.cjs` 是**离线逐帧渲染**脚本：用 CDP 驱动无头 Chrome，
按精确时刻 `t` 抓帧，不受浏览器垂直同步/光栅调度影响。出片走这条路，**不要在线录屏**。

```bash
node src/tools/render-frames.cjs <调试端口> <输出目录> <fps> <总帧数> [起始帧] [帧数] [宽] [高]
```

前置条件：本机要有 **ffmpeg**（用来编码，抓帧本身不需要）。
完整管线、验收清单、以及本机环境踩过的坑，见 `motion/02-视频制作·结构主义经验.html`。

### 不在仓库里的东西

| 东西 | 为什么不在 | 怎么拿回来 |
|---|---|---|
| **600 帧母版**（30fps × 20s） | 约 **421 MB**，不该进 git | 用 `render-frames.cjs` 重渲一遍，几分钟 |
| 动效参考截图（212 张） | 约 15 MB 的中间产物 | 重新截 |
| 旧站归档 | 站主 2026-10-12 归档在 `D:\...\look4end-归档\` | 与本站无关，别再复活 |

---

## 六、站点技术事实（省得重新踩）

- **纯静态**，无框架、无构建步骤、无后端。
- **有外部字体依赖**：首页与文档页引 Google Fonts（`fonts.googleapis.com` /
  `fonts.gstatic.com`）。断网或大陆网络下会退化成系统字体——版面不塌，
  但构成主义的窄体/黑体特征会失去。这是已知的、**有意保留**的状态。
- **中文文件名没问题**：`notes/01-美学谱系与形式法则.html` 线上正常访问。
- **`.html` 会 308 跳转**：Cloudflare Pages 会把 `x.html` 跳到 `x`（干净 URL）。
  这是正常行为，不是故障。所以 `sitemap.xml` 里一律写**无后缀**的规范地址。
- **`.bat` 里不要写中文注释**：cmd.exe 会在某些字节位置从汉字中间切开一行，
  报出毫无线索的错。中文只放在 `echo` 输出的行里。
- **部署链路**：GitHub `stone-beka/look4end-site` → Cloudflare Pages → `look4end.com`。
  域名在阿里云注册，**DNS 托管在 Cloudflare**——加解析记录要去 Cloudflare 后台。

---

## 七、一句话交接

> 改 `src/` 里的 `.md` → `python src/notes/build.py`（或 `src/motion/build.py`）→ `git push`。
> 别手改 `notes/` 和 `motion/` 里的 `.html`，那是产物。
