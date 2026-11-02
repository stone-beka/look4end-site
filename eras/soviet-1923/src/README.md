# 苏联时代 · 源

这个目录装的是**生成苏联时代页面的源**。上一层 `notes/` 和 `motion/` 里的 `.html`
都是从这里构建出来的产物。

> 时代契约见 [`docs/ERA-CONTRACT.md`](../../../docs/ERA-CONTRACT.md)；
> 工作流总览见 [`WORKFLOW.md`](../../../WORKFLOW.md)。

```
src/
├── notes/                     → 构建出 ../notes/
│   ├── 01-*.md … 10-*.md       设计笔记正文（Markdown 源）
│   ├── README.md               经验库总览
│   ├── doc.css                 文档页版式
│   ├── kit/                    样式套件（kv.css）+ 样式指南页
│   └── build.py                构建脚本
└── motion/                    → 构建出 ../motion/
    ├── README.md               视频设计总览
    ├── 01-动效设计理念.md
    ├── 02-视频制作·结构主义经验.md
    └── build.py                构建脚本（不碰 motion/index.html）
```

## 怎么构建

只依赖 **Python 3 + `markdown`**：

```bash
python eras/soviet-1923/build.py     # 一次构建 notes/ + motion/
```

或者从仓库根跑 `python tools/build_all.py`（会调用本时代的 `build.py`）。

**改正文就改这里的 `.md`**，不要改上一层 `notes/` / `motion/` 里的 `.html` —— 那是产物。

## 注意

- `build.py` 会显式传 `--out`，不要依赖脚本里自动判定产物目录的逻辑。
- 笔记首页的 `og:url` 指向 `https://look4end.com/eras/soviet-1923/notes/`。
- 文档里提到的本机路径做了脱敏（`C:\...\xxx\`），只表达目录关系，不是可直接粘贴的路径。
