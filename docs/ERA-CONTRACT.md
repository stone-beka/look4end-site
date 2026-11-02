# 时代契约（ERA-CONTRACT）

> 做任何一个新美学时代，只读这份 + `eras/_template/AGENTS.md` + 本时代的 `src/`。
> 设计依据：`docs/superpowers/specs/2026-11-02-era-architecture-design.md`

## 1. 一个时代包是什么

`eras/<slug>/` 一个目录，自包含：页面、样式、脚本、素材、Markdown 源、构建脚本、说明。
时代之间零共享样式 / 零共享脚本 / 零相互引用。

## 2. 必需文件

| 文件 | 说明 |
|---|---|
| `era.json` | 元数据，见 §3 |
| `index.html` | 时代入口 |
| `build.py` | 构建脚本（从 `_template` 复制） |
| `AGENTS.md` | 本时代的工作说明 |

可选：`era.css`、`era.js`、`entry.css`、`assets/`、`src/`、`notes/`、`motion/`、`verify/`。

## 3. `era.json`

| 字段 | 必需 | 说明 |
|---|---|---|
| `slug` | 是 | `^[a-z0-9]+(-[a-z0-9]+)*$`，等于目录名；发布后不可改 |
| `order` | 是 | 整数，全局唯一，决定门上的顺序 |
| `name` | 是 | 门上的名称 |
| `years` | 是 | 展示用年代 |
| `summary` | 是 | ≤60 字，门上的副标题 |
| `status` | 是 | `published` / `draft`；draft 不进门、不进 sitemap |
| `notes` | 否 | `{ "dir": "notes", "label": "设计笔记" }` |
| `motion` | 否 | `{ "entry": "motion/index.html", "label": "动效原型" }` |
| `arrival` | 否 | 到场节拍 CSS，默认 `entry.css`（文件不存在就跳过） |
| `legacy` | 否 | 旧路径前缀数组，如 `["/notes/"]`，构建生成 301 |
| `build` | 否 | 构建脚本，默认 `build.py` |

## 4. URL

| 内容 | 地址 |
|---|---|
| 门 | `/` |
| 时代入口 | `/eras/<slug>/` |
| 笔记 | `/eras/<slug>/notes/…` |
| 动效 | `/eras/<slug>/motion/…` |
| 素材 | `/eras/<slug>/assets/…` |

- 站内链接一律相对路径，禁止以 `/` 开头。
- 旧地址：`legacy` 里每条前缀 `p` 生成 `/p → /eras/<slug>/p` 与 `/p/* → /eras/<slug>/p/:splat` 的 301。
- `_redirects`、`sitemap.xml`、`index.html`、`core/eras.json` 都由构建生成，不手写。

## 5. 边界（构建会强制检查）

1. 时代内文件不得引用其他时代、`core/` 内部实现、根 `tools/`。
2. 根层不得出现时代专属文案、色值、字体名。
3. 每个时代自带字体声明只在本时代页面生效。
4. 产物目录只含 `.html` `.css` `.js` 和图片。
5. 违反任一条，`python tools/build_all.py` 失败并指出文件。

## 6. 开工清单

```bash
cp -r eras/_template eras/<slug>
# 改 era.json（slug/order/name/years/summary/status）
# 改 AGENTS.md 标题、index.html、era.css
python tools/build_all.py
```

## 7. 学习美学的工作流（骨架，下一步单独出规格）

0 立项 → 1 考据 → 2 设计系统 → 3 素材与授权 → 4 技术配方 → 5 页面实现 → 6 验证 → 7 交付。
每阶段产物路径与验收门槛见设计文档第 8 节。

## 8. 验收命令

```bash
python tools/build_all.py
python -m unittest discover -s tools/tests -t tools -v
python tools/verify/run_all.py
```
