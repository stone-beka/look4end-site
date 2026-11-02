# src/ —— 源与工具

这个目录装的是**生成站点页面的源**，以及配套的工具。仓库根的 `notes/` 和 `motion/`
里的 `.html` 都是从这里构建出来的产物。

> 为什么要放在公开仓库里：这样任何人（或 AI）clone 下来就能读懂工作流、
> 重新构建、跑验证。完整说明见仓库根的 [`../WORKFLOW.md`](../WORKFLOW.md)。

```
src/
├── notes/                     → 构建出 notes/
│   ├── 01-*.md … 10-*.md       设计笔记正文（Markdown 源）
│   ├── README.md               经验库总览
│   ├── doc.css                 文档页版式
│   ├── kit/                    样式套件（kv.css）+ 样式指南页
│   └── build.py                构建脚本
│
├── motion/                    → 构建出 motion/
│   ├── README.md               视频设计总览
│   ├── 01-动效设计理念.md
│   ├── 02-视频制作·结构主义经验.md
│   └── build.py                构建脚本（不碰 motion/index.html）
│
├── verify/                    验证脚本（参数化，换项目改路径即可）
│   ├── static-check.ps1        HTML/CSS/JS 静态检查 + id 引用 + 文档链接
│   ├── shot.ps1                多状态无头截图
│   ├── flow-test.ps1           交互链路功能测试
│   ├── example-flow-test.js    功能测试模板
│   └── route-test.js           纯逻辑单元测试（不需要浏览器）
│
└── tools/
    └── render-frames.cjs       离线逐帧渲染（CDP 驱动无头 Chrome），出片用
```

## 怎么构建

只依赖 **Python 3 + `markdown`**：

```bash
pip install markdown
python src/notes/build.py      # → notes/
python src/motion/build.py     # → motion/
```

两个脚本都会自动判断产物目录（放在 `src/<名字>/` 下就写仓库的 `<名字>/`），
也可以用 `--out` 显式指定。

**改正文就改这里的 `.md`**，不要改仓库根 `notes/` / `motion/` 里的 `.html` —— 那是产物。

## 注意

- `.ps1` 都带 UTF-8 BOM。PowerShell 5.1 读没有 BOM 的 UTF-8 会乱码并报假语法错，
  改完这些脚本要确认 BOM 还在。
- 文档里提到的本机路径做了脱敏（`C:\...\xxx\`），只表达目录关系，不是可直接粘贴的路径。
