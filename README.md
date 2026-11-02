# Look4End

`look4end.com` 的网站源码。纯静态 HTML + CSS —— 没有框架、没有运行时构建。

站点主线是**按时代陈列视觉美学**：首页是一道极简的「时间门」，每个时代是一个自包含的世界
（苏联构成主义，之后会有蒸汽/侦探等新的美学时代）。每个时代自带页面、样式、素材、设计笔记与动效，
彼此零共享、零引用。

## 项目结构

```
look4end-site/
├── index.html                   首页「时间门」（构建生成）
├── core/
│   ├── gate.css                 门的基础排版
│   └── eras.json                注册表（构建生成）
├── eras/
│   ├── _template/               新时代脚手架：复制即开工
│   └── soviet-1923/             苏联构成主义
│       ├── index.html           报纸首页（手写）
│       ├── era.css / era.js     首页样式与两级状态机
│       ├── src/                 笔记与动效的 Markdown 源 + build.py
│       ├── notes/               11 篇设计笔记（构建产物）
│       └── motion/              20 秒无缝循环动效原型 + 3 篇经验
├── tools/
│   ├── build_all.py             构建调度 + 五项体检
│   ├── era_lib.py               规则层
│   ├── tests/                   纯逻辑单测
│   ├── verify/                  静态检查 / 交互链路 / 截图 / 一键验收
│   └── render-frames.cjs        离线逐帧出片
├── docs/
│   ├── ERA-CONTRACT.md          时代契约
│   └── superpowers/             设计 / 计划文档
├── sitemap.xml  _redirects      构建生成
├── 404.html  style.css  robots.txt  og-image.png
└── publish.bat                  双击发布
```

## 改内容

**`notes/` 和 `motion/` 里的 HTML 是构建产物，不是手写源。** 正文以 Markdown 为源，
改 `eras/soviet-1923/src/` 里的 `.md`，然后：

```bash
pip install markdown          # 唯一依赖
python tools/build_all.py     # 重建所有时代 + 门 + sitemap + 301
```

只有这几样是直接手改的：

| 想改什么 | 改哪儿 |
|---|---|
| 门的样子 | `tools/templates/gate.html` + `core/gate.css` |
| 某个时代的页面 | `eras/<slug>/index.html` / `era.css` / `era.js` |
| 时代的元数据（名称、年代、排序） | `eras/<slug>/era.json` |
| 笔记与动效正文 | `eras/<slug>/src/**/*.md` |
| 错误页 | `404.html` |

## 加一个新时代

```bash
cp -r eras/_template eras/<slug>
# 改 era.json（slug 必须等于目录名）、写页面、写 src/notes/*.md
python tools/build_all.py
```

契约见 [`docs/ERA-CONTRACT.md`](docs/ERA-CONTRACT.md)，工作流见 [`WORKFLOW.md`](WORKFLOW.md)。

## 验证

```bash
python tools/verify/run_all.py            # 构建 + 单测 + 路由 + 静态检查
python tools/verify/run_all.py --browser  # 另加交互链路与截图
```

## 发布

**双击 `publish.bat`。** 它把改动收集起来、记一笔提交、推到 GitHub；
Cloudflare Pages 随即自动重建，**约 30 秒后刷新 look4end.com 就是新的。**

手动也行：

```bash
git add -A
git commit -m "说明你改了什么"
git push
```

## 部署信息

| 项目 | 在哪 |
|---|---|
| 代码仓库 | GitHub `stone-beka/look4end-site` |
| 托管 | Cloudflare Pages（连着仓库，一推送就自动重新部署） |
| 域名 | look4end.com（在**阿里云**注册，DNS 托管在 **Cloudflare**） |

> ⚠️ 域名解析已经交给 Cloudflare 管了。**以后加 DNS 记录要去 Cloudflare 后台，不在阿里云改。**
