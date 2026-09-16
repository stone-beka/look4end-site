# Look4End

`look4end.com` 的网站源码。纯静态 HTML + CSS —— 没有框架、没有构建步骤、没有外部依赖（不引字体、不引 CDN），断网打开也是完整的。

## 项目结构

```
look4end-site/
├── index.html            首页
├── style.css             全站共用样式（所有页面的外观都在这一个文件里）
├── 404.html              访问不存在的地址时显示的页面
├── posts/index.html      思想笔记
├── games/index.html      游戏企划
├── timeseed/index.html   TimeSeed
├── publish.bat           双击就能发布的脚本
└── README.md             本文件
```

---

## 一、改内容

### 改首页文案

打开 `index.html`。文字全是明文，改完存盘就生效，不用做别的。

### 改颜色

打开 `style.css`，最上面 `:root` 里的六个变量管着全站外观：

| 变量 | 管什么 |
|---|---|
| `--bg` | 页面背景 |
| `--fg` | 标题、主文字 |
| `--fg-dim` | 正文、副标题 |
| `--fg-faint` | 方括号、返回链接 |
| `--accent` | 强调色（只在鼠标悬停时出现） |
| `--line` | 那两条发丝分隔线 |

**改一处，全部页面一起变。**

---

## 二、加东西

### 加一篇思想笔记

1. 在 `posts/` 下新建一个文件夹，比如 `posts/001-为什么是黑箱/`
2. 把 `posts/index.html` 复制进去，改名为 `index.html`
3. 打开新文件，把 `<h1 class="section-title">` 里的"思想笔记"换成你的标题
4. 把 `<p class="placeholder">内容建设中</p>` 那行换成正文
5. 打开 `posts/index.html`，在页面里加一条链接指向这个新文件夹
6. 双击 `publish.bat` 发布

> **文件夹名用英文或数字。** 中文文件夹在网址里会变成 `%E6%88%91%E7%9A%84...` 这样一长串，能看但难看。用 `001-xxx` 这种编号开头，以后排序也方便。

### 加一个游戏企划

一样，把 `games/index.html` 复制到 `games/你的项目名/index.html` 再改。

### 加一整个新板块

比如想加个"关于我"：

1. 建文件夹 `about/`，里面放 `index.html`（从 `posts/index.html` 复制来改）
2. 打开首页 `index.html`，在 `<nav class="nav">` 里照葫芦画瓢加一行：

```html
<a href="about/"><span class="br" aria-hidden="true">[</span>关于我<span class="br" aria-hidden="true">]</span></a>
```

（`<span class="br">` 就是左右方括号，`aria-hidden` 是让读屏软件别把方括号念出来。照抄就行。）

---

## 三、发布

**双击 `publish.bat`。** 它会自动做三件事：把改动收集起来、记一笔存档、传到 GitHub。

传完后 Cloudflare 会自动重新部署，**大约 30 秒后刷新 look4end.com 就是新的。**

想手动做也行，三条命令：

```bash
git add -A
git commit -m "说明你改了什么"
git push
```

---

## 四、部署信息

| 项目 | 在哪 |
|---|---|
| 代码仓库 | GitHub |
| 托管 | Cloudflare Pages（连着 GitHub 仓库，一推送就自动重新部署） |
| 域名 | look4end.com（在**阿里云**注册，DNS 托管在 **Cloudflare**） |

> ⚠️ 域名解析已经交给 Cloudflare 管了。**以后加 DNS 记录要去 Cloudflare 后台，不在阿里云改了。**
