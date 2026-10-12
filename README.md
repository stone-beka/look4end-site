# Look4End

`look4end.com` 的网站源码。纯静态 HTML + CSS —— 没有框架、没有构建步骤。

站上现在是一组关于**「设计 HTML」这件事本身**的文档：一个具体风格（构成主义）的美学考据，
加上实现过程中沉淀下来的、可跨项目复用的规则与踩坑。
所有关键数值都经过实测或精算，未验证的部分明确标注。

## 项目结构

```
look4end-site/
├── index.html                   首页
├── press.css / press.js         首页自己的样式与脚本
├── assets/                      页面里用到的图
├── notes/                       文档（全部在这里）
│   ├── 01-美学谱系与形式法则.html  A 组 · 美学考据
│   ├── 02-设计系统规格.html
│   ├── 03-资源清单.html
│   ├── 04-技术实现手册.html
│   ├── 05-前端技术方案.html
│   ├── 06-素材情报报告.html
│   ├── 07-设计规则速查.html       B 组 · 可跨项目复用的规则
│   ├── 08-交互模式.html
│   ├── 09-踩坑清单.html
│   ├── 10-验证工作流.html
│   ├── README.html              总览页（经验库自己的 README）
│   ├── kit/index.html           可运行的样式套件 + 样式指南
│   ├── kit/kv.css               构成主义样式套件：配色 / 字体 / 网格的唯一来源
│   └── doc.css                  文档页版式：正文栏、目录、表格
├── motion/                      视频设计（动效这条线）
│   ├── index.html               动效原型：构成主义 20 秒无缝循环（手写单文件，不走构建）
│   ├── README.html              视频设计总览
│   ├── 01-动效设计理念.html       时间结构、动效语汇、循环点规范、卡顿诊断
│   └── 02-视频制作·结构主义经验.html 五轮排查复盘、出片管线、验收清单、本机环境的坑
├── src/                         源与工具（上面两层的产物都从这里构建）
│   ├── notes/                   设计笔记的 .md 源 + build.py + kit/ + doc.css
│   ├── motion/                  视频设计的 .md 源 + build.py
│   ├── verify/                  验证脚本：静态检查 / 截图 / 功能测试 / 单元测试
│   └── tools/render-frames.cjs  离线逐帧出片（CDP 驱动无头 Chrome）
├── WORKFLOW.md                  工作流：怎么改、怎么构建、怎么验证、怎么发
├── style.css                    旧版样式，现在只有 404.html 还在用
├── 404.html                     访问不存在的地址时显示
├── og-image.png                 分享卡片预览图（1200×630）
├── robots.txt / sitemap.xml     给搜索引擎
└── publish.bat                  双击发布
```

## 改内容

**`notes/` 和 `motion/` 里的 HTML 是构建产物，不是手写源。** 正文以 Markdown 为源，
源和构建脚本都在 [`src/`](src/)。直接手改 HTML，下一次构建就会把它盖掉。

```bash
pip install markdown           # 唯一依赖
python src/notes/build.py      # 重建 notes/
python src/motion/build.py     # 重建 motion/（不碰 motion/index.html）
```

两个脚本会自动判断产物目录，也可以用 `--out` 指定。

只有这几样是直接手改的：

| 想改什么 | 改哪儿 |
|---|---|
| 配色、字体、间距、网格 | `src/notes/kit/kv.css`（`:root` 里的变量） |
| 文档页版式（正文栏、目录、表格） | `src/notes/doc.css` |
| 首页 | `index.html` + `press.css` / `press.js` |
| 动效原型 | `motion/index.html`（独立单文件，不走构建） |
| 错误页 | `404.html` |

> ⚠️ `notes/kit/kv.css` 看起来像"手改的样式表"，其实是 `src/notes/kit/kv.css` 的副本。

完整工作流——验证脚本怎么用、视频怎么出片、站点有哪些已知技术事实——见
**[WORKFLOW.md](WORKFLOW.md)**。

## 发布

**双击 `publish.bat`。** 它把改动收集起来、记一笔提交、推到 GitHub；
Cloudflare Pages 随即自动重建，**约 30 秒后刷新 look4end.com 就是新的。**

上一次没推成功的，双击它也能补上 —— 哪怕没有新改动，它也会检查有没有
「已经提交、卡在本机没上去」的提交，有就补推一次。

想手动做也行：

```bash
git add -A
git commit -m "说明你改了什么"
git push
```

## 部署信息

| 项目 | 在哪 |
|---|---|
| 代码仓库 | GitHub |
| 托管 | Cloudflare Pages（连着仓库，一推送就自动重新部署） |
| 域名 | look4end.com（在**阿里云**注册，DNS 托管在 **Cloudflare**） |

> ⚠️ 域名解析已经交给 Cloudflare 管了。**以后加 DNS 记录要去 Cloudflare 后台，不在阿里云改。**
