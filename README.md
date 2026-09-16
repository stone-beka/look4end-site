# Look4End

`look4end.com` 的网站源码。纯静态 HTML + CSS —— 没有框架、没有构建步骤、没有外部依赖（不引字体、不引 CDN），断网打开也是完整的。

> 「不引外部资源」讲的是**读者侧** —— 断网也要能读完，这是网站的性格，不是技术洁癖。
> 它只约束这个文件夹。写作台是本机工具，不受这条限制。

## 项目结构

```
look4end-site/
├── index.html            首页
├── style.css             全站共用样式（所有页面的外观都在这一个文件里）
├── 404.html              访问不存在的地址时显示的页面
├── og-image.png          分享到微信 / QQ 时显示的预览图（1200×630）
├── robots.txt            告诉搜索引擎可以抓什么
├── sitemap.xml           给搜索引擎的页面清单
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

### 发一篇文章

**不用手写。** 文章页和列表页由本机的**写作台**生成 —— 写、改、发布、撤回都在它里面点。

> **为什么文章用数字命名？** 网址最短最干净（`look4end.com/posts/001.html`），编号还能保证排序。中文文件名在网址里会变成 `%E6%88%91...` 一长串，所以不用。
> **这个结构别改。** 改成日期目录或语义化网址，已经分享出去的链接会全部失效。

**`posts/` 和 `games/` 里的 html 请不要手动编辑** —— 写作台按自己的规矩生成它们，
手改会被下一次发布覆盖掉。

### 加一整个新板块

比如想加个"关于我"：

1. 建文件夹 `about/`，里面放 `index.html`（从 `posts/index.html` 复制来改）
2. 打开首页 `index.html`，在 `<nav class="nav">` 里照葫芦画瓢加一行：

```html
<a href="about/"><span class="br" aria-hidden="true">[</span>关于我<span class="br" aria-hidden="true">]</span></a>
```

（`<span class="br">` 就是左右方括号，`aria-hidden` 是让读屏软件别把方括号念出来。照抄就行。）

### 改分享卡片的预览图

把链接发到微信 / QQ 时对方看到的那张卡片，由每个页面 `<head>` 里的 `og:` 标签决定。

- **换预览图**：替换 `og-image.png`（保持 1200×630 最保险）
- **换卡片文字**：改对应页面里的 `og:title` 和 `og:description`

> ⚠️ `og:image` **必须写完整网址**（`https://look4end.com/og-image.png`），写相对路径微信认不出来。

**新加页面时，一定要加一套自己的 og 标签**——直接复制 `posts/index.html` 里那段改就行，但记得把 `og:url` 和标题换成这一页自己的。忘了换的话，分享出去会显示成别的页面的标题。

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
