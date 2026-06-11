# semantic-blog-search 零基础学习指南

这份文档写给“刚开始接触工程项目”的自己。

你不需要先懂搜索引擎、后端、服务器、Cloudflare、向量数据库。我们从最朴素的问题开始：

```txt
我有一堆 Markdown 博客文章。
我想输入一句自然语言问题。
程序能帮我找出语义相关的文章片段。
```

这就是这个项目在做的事。

## 1. 我一开始想做什么？

你的网站 `keronshans.top` 里有很多博客文章，尤其是算法、数据结构、学习笔记。

普通搜索通常只能做关键词匹配。例如你搜：

```txt
线段树懒标记为什么要 pushdown
```

传统搜索可能只会找包含“线段树”“懒标记”“pushdown”这些字的文章。

但你真正想要的是：

```txt
即使文章里没有完全一样的搜索句子，
只要意思相关，也能被找出来。
```

这就叫“语义搜索”。

所以这个项目的目标是：

```txt
给你的 Hexo/Markdown 博客做一个本地语义搜索服务。
```

它不是聊天机器人，也不是 AI 问答系统。它只负责：

```txt
输入一句查询 -> 返回相关博客片段
```

## 2. 这个项目不是什么？

这个项目很克制，故意没有做复杂。

它不是：

- 不是完整 RAG 系统
- 不是 ChatGPT 问答机器人
- 不是商业级搜索引擎
- 不是用户系统
- 不是复杂前端
- 不接 OpenAI API
- 不用 Docker
- 不依赖 Qdrant server

它现在只是一个学习性质的 MVP：

```txt
Markdown -> chunk -> embedding -> Qdrant -> search API
```

MVP 的意思是 Minimum Viable Product，最小可用版本。

## 3. 从头到尾我们做了什么？

整个过程可以分成 7 步。

### 第一步：写 Python 项目

我们在本地创建了项目：

```txt
C:\Users\31802\Documents\semantic-blog-search
```

这个项目负责：

- 读取 Markdown 博客
- 解析 frontmatter
- 把文章切成小片段
- 调用 embedding 模型
- 写入 Qdrant 本地向量库
- 提供命令行搜索
- 提供 FastAPI 搜索接口
- 支持增量索引

### 第二步：构建本地语义搜索

最开始你可以在本地运行：

```powershell
python scripts/build_index.py --config config.yaml
python scripts/search.py --config config.yaml "线段树懒标记为什么要 pushdown"
```

这证明项目本地能跑。

### 第三步：升级成常驻 API

命令行搜索有个问题：

```txt
每搜一次，就重新加载一次 embedding 模型。
```

模型加载很慢，所以我们后来加了：

```txt
scripts/server.py
```

它启动一个 FastAPI 服务，让模型常驻内存。

也就是说：

```txt
服务启动时加载一次模型
之后每次搜索都复用这个模型
```

### 第四步：做增量索引

一开始每次更新博客都要全量重建索引，这很慢。

后来我们加了：

```txt
scripts/sync_index.py
```

它会记录每篇 Markdown 的内容 hash。

以后更新博客时：

- 新文章：加入索引
- 改过的文章：重新索引
- 删除的文章：从索引删除
- 没变的文章：跳过

这就是“增量索引”。

### 第五步：部署到腾讯云服务器

你的搜索服务不能直接跑在 Cloudflare Pages 上，因为 Cloudflare Pages 不适合常驻 Python 模型。

所以我们买/使用了一台腾讯云服务器：

```txt
175.178.216.243
```

服务器上放了：

```txt
/opt/semantic-blog-search
```

博客 Markdown 源文件放在：

```txt
/opt/keronshans_blogsorce/content/posts
```

### 第六步：接入 Cloudflare Tunnel

一开始我们试过让 `api.keronshans.top` 直接指向腾讯云公网 IP：

```txt
api.keronshans.top -> 175.178.216.243
```

但这种方式容易碰到备案页、端口暴露、DNS-only/proxied 混用等问题。

后来我们改成了 Cloudflare Tunnel：

```txt
api.keronshans.top
  -> Cloudflare Tunnel
  -> 腾讯云服务器 127.0.0.1:8000
```

主站：

```txt
keronshans.top
```

还是 Cloudflare Pages 管。

搜索 API：

```txt
api.keronshans.top
```

由 Cloudflare Tunnel 转发到腾讯云服务器上的 FastAPI 服务。

### 第七步：跑通公网搜索接口

现在这个接口已经能用：

```txt
https://api.keronshans.top/search?q=线段树&top_k=5
```

但它需要 token。

不带 token 会返回：

```json
{"detail":"Unauthorized"}
```

这是好事，说明接口没有裸奔。

## 4. 整体架构是什么？

现在的架构是：

```txt
你的 Markdown 博客文章
        |
        v
sync_index.py 增量索引
        |
        v
embedding 模型 BAAI/bge-small-zh-v1.5
        |
        v
Qdrant local 向量数据库
        |
        v
FastAPI 搜索服务
        |
        v
Cloudflare Tunnel
        |
        v
Cloudflare
        |
        v
https://api.keronshans.top
```

以后网站页面接入后会变成：

```txt
浏览器
  -> keronshans.top 页面
  -> /api/blog-search
  -> https://api.keronshans.top/search
  -> Cloudflare Tunnel
  -> 127.0.0.1:8000
  -> 搜索结果
```

## 5. 每个核心概念是什么意思？

### Markdown

Markdown 是你写博客文章的格式，例如：

```md
---
title: 线段树懒标记入门
tags:
  - 数据结构
---

线段树是一种维护区间信息的数据结构。
```

上面 `---` 包住的部分叫 frontmatter，里面有标题、标签、日期等元数据。

### frontmatter

frontmatter 是 Markdown 文件开头的配置区。

项目用 `python-frontmatter` 解析它。

我们会从里面提取：

- title
- date
- tags
- slug

### chunk

chunk 就是“文章片段”。

为什么不直接把整篇文章丢给模型？

因为一篇文章可能很长。如果整篇文章只变成一个向量，搜索结果会很粗糙。

所以我们把文章拆成小块：

```txt
文章 -> chunk1
文章 -> chunk2
文章 -> chunk3
```

搜索时返回的是最相关的 chunk。

### embedding

embedding 是“把文字变成数字向量”。

例如：

```txt
线段树懒标记
```

会变成类似：

```txt
[0.012, -0.34, 0.88, ...]
```

这些数字本身人看不懂，但机器可以用它们判断语义距离。

意思相近的文本，向量距离更近。

### BAAI/bge-small-zh-v1.5

这是我们使用的中文 embedding 模型。

它不是聊天模型。

它只做一件事：

```txt
中文文本 -> 向量
```

我们用它把文章 chunk 和用户查询都变成向量。

### Qdrant

Qdrant 是向量数据库。

普通数据库擅长查：

```sql
title = "线段树"
```

向量数据库擅长查：

```txt
找出和这个查询向量最接近的 5 个文章片段
```

我们用的是 Qdrant local mode。

意思是：

```txt
不用单独启动 Qdrant server
数据存在本地磁盘
```

### FastAPI

FastAPI 是 Python 后端框架。

它让我们可以提供 HTTP 接口：

```txt
GET /health
GET /search
```

你的搜索服务就是一个 FastAPI 应用。

### Cloudflare Tunnel

FastAPI 服务只监听：

```txt
127.0.0.1:8000
```

这个地址只能服务器自己访问。

Cloudflare Tunnel 负责把公网请求安全地转发进去：

```txt
https://api.keronshans.top
  -> Cloudflare Tunnel
  -> 127.0.0.1:8000
```

服务器上运行的 `cloudflared` 是 Tunnel 连接器。它主动连到 Cloudflare，所以你不需要把 `8000` 端口暴露到公网。

### Cloudflare

Cloudflare 负责域名解析和 HTTPS 入口。

现在：

```txt
api.keronshans.top
```

通过 Cloudflare Tunnel 指向你的腾讯云服务器本机服务。

## 6. 项目目录怎么看？

核心目录：

```txt
semantic-blog-search/
├── scripts/
├── src/semantic_blog_search/
├── docs/
├── deploy/
├── integrations/
├── tests/
├── config.example.yaml
└── requirements.txt
```

### scripts/

放命令行入口。

```txt
scripts/build_index.py
scripts/sync_index.py
scripts/search.py
scripts/server.py
```

你日常最常用的是：

```txt
sync_index.py
server.py
```

### src/semantic_blog_search/

放真正的项目代码。

```txt
config.py              读取配置
parser.py              解析 Markdown
chunker.py             切分文章
embedder.py            加载模型并生成向量
vector_store.py        操作 Qdrant
indexer.py             全量建索引
incremental_indexer.py 增量建索引
searcher.py            搜索服务逻辑
api.py                 FastAPI 接口
```

### docs/

放文档。

当前重要文档：

```txt
docs/deploy-to-keronshans.md
docs/website-agent-handoff.md
docs/learning-guide.md
```

### deploy/

放部署模板。

```txt
semantic-blog-search.service.example
Caddyfile.example
```

现在公网入口实际使用 Cloudflare Tunnel；这些模板保留为反向代理部署的参考。

### integrations/

放和其他项目对接的示例。

```txt
integrations/cloudflare-pages/app-api-blog-search-route.ts
```

这是给网站端 Next.js 使用的代理接口模板。

## 7. 配置文件 config.yaml 是什么？

`config.yaml` 是本地或服务器的私人配置。

它不提交 GitHub。

示例：

```yaml
posts_dir: "/opt/keronshans_blogsorce/content/posts"
url_prefix: "/posts"

qdrant:
  db_path: "./data/qdrant"
  collection_name: "blog_chunks"

embedding:
  model_name: "BAAI/bge-small-zh-v1.5"

chunk:
  chunk_size: 600
  chunk_overlap: 100

search:
  top_k: 5

index:
  manifest_path: "./data/index_manifest.json"

server:
  host: "127.0.0.1"
  port: 8000
  api_token: "你的私有token"
```

### posts_dir

Markdown 文章目录。

服务器上现在是：

```txt
/opt/keronshans_blogsorce/content/posts
```

### url_prefix

生成文章链接用的前缀。

如果文章 slug 是 `segment-tree`，URL 会像：

```txt
/posts/segment-tree
```

### qdrant.db_path

Qdrant 本地数据存放位置。

```txt
./data/qdrant
```

这个目录不要提交 GitHub。

### embedding.model_name

embedding 模型名称。

现在用：

```txt
BAAI/bge-small-zh-v1.5
```

线上服务器因为访问 Hugging Face 慢，所以实际运行时用了本地缓存和离线模式：

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
```

### chunk.chunk_size

每个 chunk 大概多少字符。

现在是：

```txt
600
```

### chunk.chunk_overlap

相邻 chunk 保留一点重叠内容，避免边界处语义断开。

现在是：

```txt
100
```

### server.api_token

搜索接口的私有 token。

请求 `/search` 时必须带：

```txt
Authorization: Bearer <token>
```

不要把它写到前端代码里。

## 8. 每条常用命令是什么意思？

### 创建虚拟环境

```bash
python3 -m venv .venv
```

意思是：给这个项目创建一个独立 Python 环境。

这样项目依赖不会污染系统 Python。

### 激活虚拟环境

```bash
. .venv/bin/activate
```

意思是：告诉当前 shell，接下来使用 `.venv` 里的 Python 和 pip。

激活后命令行前面会出现：

```txt
(.venv)
```

### 安装依赖

```bash
python -m pip install -r requirements.txt
```

意思是：读取 `requirements.txt`，安装项目需要的包。

例如：

- sentence-transformers
- qdrant-client
- fastapi
- uvicorn
- tqdm

### 增量同步索引

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/sync_index.py --config config.yaml
```

意思是：

```txt
使用离线模型缓存
读取 config.yaml
扫描 posts_dir
只处理新增/修改/删除的文章
更新 Qdrant 向量库
```

### 命令行搜索

```bash
python scripts/search.py --config config.yaml "线段树懒标记为什么要 pushdown"
```

意思是：在命令行里搜索一次。

缺点是每次都要加载模型，所以会慢。

### 启动 API 服务

```bash
python scripts/server.py --config config.yaml
```

意思是：启动 FastAPI 搜索服务。

服务会监听：

```txt
127.0.0.1:8000
```

### 查看 systemd 服务状态

```bash
systemctl status semantic-blog-search --no-pager
```

意思是：看搜索服务是不是正在后台运行。

### 查看服务日志

```bash
journalctl -u semantic-blog-search -n 100 --no-pager
```

意思是：看最近 100 行搜索服务日志。

### 测试健康状态

```bash
curl https://api.keronshans.top/health
```

意思是：问服务器“你活着吗？”

正常返回：

```json
{"status":"ok","collection_name":"blog_chunks"}
```

### 测试搜索接口

```bash
curl -H "Authorization: Bearer <token>" "https://api.keronshans.top/search?q=线段树&top_k=5"
```

意思是：

```txt
带着 token 请求搜索接口
查询“线段树”
返回前 5 个结果
```

## 9. 数据是怎么流动的？

索引阶段：

```txt
Markdown 文件
  -> parser.py 解析 frontmatter 和正文
  -> chunker.py 切成片段
  -> embedder.py 生成向量
  -> vector_store.py 写入 Qdrant
```

搜索阶段：

```txt
用户查询
  -> embedder.py 生成查询向量
  -> Qdrant 找最相近的 chunk
  -> FastAPI 返回 JSON
```

## 10. 增量索引背后的原理

每篇文章都有一个内容 hash。

hash 可以理解成“内容指纹”。

如果文章内容没变，hash 就不变。

如果改了一个字，hash 就会变。

项目会把状态记录到：

```txt
./data/index_manifest.json
```

里面记录：

- source_file
- content_hash
- chunk_ids
- indexed_at

下次同步时：

```txt
当前文件 hash == 上次记录 hash
```

就跳过。

```txt
当前文件 hash != 上次记录 hash
```

就重新索引。

如果 manifest 里有某个文件，但现在磁盘上没有了，就说明文章被删除了，于是删除对应 chunk。

## 11. 为什么服务器上要离线模式？

腾讯云服务器访问 Hugging Face 经常超时。

之前你看到过：

```txt
timed out while requesting HEAD https://huggingface.co/...
```

所以我们把模型缓存传到服务器，再用：

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
```

告诉程序：

```txt
不要联网下载模型
只用本地已有缓存
```

这样更稳定。

## 12. 为什么搜索命令慢，API 快？

命令行搜索：

```txt
启动 Python
加载模型
搜索
退出 Python
```

每搜一次都加载一次模型。

API 服务：

```txt
启动服务
加载模型一次
等待请求
搜索
继续等待请求
```

模型常驻内存，所以后续搜索更快。

## 13. 什么是混合搜索？

一开始项目主要用向量搜索：

```txt
查询语句 -> embedding 向量 -> Qdrant 找语义最接近的 chunk
```

这种方式适合找“意思相近”的内容，但有时会漏掉非常具体的词，例如：

```txt
按秩合并
并查集
pushdown
lazy tag
```

混合搜索就是多加一个信号：

```txt
语义相似度 + 关键词匹配 = 最终排序
```

现在的流程是：

```txt
1. 先用向量搜索召回更多候选结果，比如 top 20 或 top 30
2. 再检查标题、标签、正文里是否出现查询词
3. 如果标题/标签/正文命中关键词，就给这个 chunk 加分
4. 最后重新排序，只返回 top_k 个结果
```

这不是重新训练模型，也不是接入新的大模型。它只是让排序更懂你的算法术语。

相关配置在 `config.yaml`：

```yaml
search:
  top_k: 5
  hybrid_enabled: true
  hybrid_candidate_multiplier: 4
  hybrid_candidate_limit: 30
  hybrid_keyword_weight: 0.25
```

含义：

- `hybrid_enabled`：是否启用混合搜索。
- `hybrid_candidate_multiplier`：先多拿一些候选，例如 `top_k=5` 时先拿约 20 个。
- `hybrid_candidate_limit`：候选数量上限，避免太慢。
- `hybrid_keyword_weight`：关键词加分权重。

因为混合搜索需要检查完整 chunk 文本，所以新版索引会把完整 `text` 存进 Qdrant payload。旧索引升级后，最好跑一次：

```bash
python scripts/build_index.py --config config.yaml
```

服务器上如果使用离线模型缓存，就继续带上：

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/build_index.py --config config.yaml
```

## 14. 为什么要按四级标题切 chunk？

你的算法博客里很多 `####` 是具体题目名，例如：

```md
### 并查集
#### [家谱](https://www.luogu.com.cn/problem/P2814)
```

旧切法只按空行和长度切，不知道“这段属于家谱这道题”。如果一个大章节里有很多题，搜索可能返回一个比较泛的片段。

新切法会先看 Markdown 标题结构：

```txt
# 到 #### 都作为 section 边界
##### 及以下默认不切
```

然后每个 chunk 都带上标题路径：

```txt
文章标题：数据结构
标签：数据结构
小节路径：数据结构 > 并查集 > 家谱
正文：
...
```

这样搜索“家谱”“按秩合并”“线段树 pushdown”时，模型不仅看正文，也能看见这段笔记所在的小节语境。

默认配置是：

```yaml
chunk:
  chunk_size: 700
  chunk_overlap: 120
  split_heading_max_level: 4
  include_heading_path: true
```

这不是无脑切碎。规则是：

```txt
先按四级以内标题切 section
如果某个 section 很长，再按 chunk_size 继续切
chunk_overlap 只在同一个 section 内发生
```

所以不同题目之间不会互相混上下文。

升级这个切分策略后，要重建索引：

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/build_index.py --config config.yaml
```

## 15. 当前项目已经做到什么程度？

已经做到：

- 本地 Python 项目完成
- GitHub private repo 已创建并推送
- 腾讯云服务器已部署搜索项目
- 博客 Markdown 已同步到服务器
- embedding 模型已通过本地缓存跑通
- Qdrant local 索引已建立
- 命令行搜索能搜出结果
- FastAPI 服务已跑通
- Cloudflare Tunnel 已在 Cloudflare 侧创建
- `api.keronshans.top` 已切到 Tunnel CNAME
- `/search` 有 Bearer Token 保护
- 网站端 `/api/blog-search` 代理 route 已部署
- 网站端 `SEARCH_API_URL` 已改为 `https://api.keronshans.top/search`

还没做到：

- 服务器上的 `cloudflared` 连接器还需要安装并启动
- 文章同步还是手动 `scp`
- 没有自动备份 Qdrant 数据
- 没有公开搜索限流

## 16. 我现在怎么自己测试？

### 测 health

```bash
curl https://api.keronshans.top/health
```

成功说明服务在线。

### 测未授权搜索

```bash
curl "https://api.keronshans.top/search?q=线段树&top_k=5"
```

应该返回：

```json
{"detail":"Unauthorized"}
```

这说明接口被保护了。

### 测授权搜索

```bash
curl -H "Authorization: Bearer <token>" "https://api.keronshans.top/search?q=线段树&top_k=5"
```

成功会返回搜索结果。

## 17. 日常更新博客后怎么办？

本地文章更新后，在本地 PowerShell：

```powershell
scp -r "C:\Users\31802\Documents\keronshans_blogsorce\content\posts" ubuntu@175.178.216.243:/home/ubuntu/
```

然后在服务器：

```bash
rm -rf /opt/keronshans_blogsorce/content/posts
mv /home/ubuntu/posts /opt/keronshans_blogsorce/content/posts
cd /opt/semantic-blog-search
. .venv/bin/activate
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/sync_index.py --config config.yaml
```

通常不用重启服务。

## 18. 如果服务挂了怎么办？

先看服务状态：

```bash
systemctl status semantic-blog-search --no-pager
```

看日志：

```bash
journalctl -u semantic-blog-search -n 100 --no-pager
```

重启：

```bash
sudo systemctl restart semantic-blog-search
```

再测：

```bash
curl https://api.keronshans.top/health
```

## 19. 如果搜索不到新文章怎么办？

按顺序检查：

### 1. 文章是否在服务器上

```bash
ls /opt/keronshans_blogsorce/content/posts | head
```

### 2. 是否跑过增量索引

```bash
cd /opt/semantic-blog-search
. .venv/bin/activate
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/sync_index.py --config config.yaml
```

### 3. 搜索 API 是否在线

```bash
curl https://api.keronshans.top/health
```

### 4. 是否带 token

搜索接口必须带：

```txt
Authorization: Bearer <token>
```

## 20. 这个项目适合怎么继续学？

建议阅读顺序：

1. `README.md`
2. `docs/learning-guide.md`
3. `src/semantic_blog_search/chunker.py`
4. `src/semantic_blog_search/parser.py`
5. `src/semantic_blog_search/incremental_indexer.py`
6. `src/semantic_blog_search/searcher.py`
7. `src/semantic_blog_search/api.py`

你可以按这个问题链学习：

```txt
一篇 Markdown 是怎么被读进来的？
一篇文章是怎么切成 chunk 的？
chunk 是怎么变成向量的？
向量是怎么存进 Qdrant 的？
搜索时查询语句怎么变成向量？
FastAPI 怎么把搜索结果变成 HTTP JSON？
Cloudflare Tunnel 怎么把公网请求转到 FastAPI？
Cloudflare DNS 怎么把域名转到 Tunnel？
```

## 21. Cloudflare Tunnel 这一步是在做什么？

一开始我们尝试过让 `api.keronshans.top` 直接指向腾讯云服务器公网 IP。

这个思路看起来很直观：

```txt
api.keronshans.top -> 175.178.216.243 -> 服务器上的搜索服务
```

但实际会遇到几个问题：

- 腾讯云公网域名访问可能出现备案页。
- 直接暴露服务器端口不够优雅。
- Cloudflare 的 DNS-only、Proxied、Worker 访问裸 IP 容易混在一起。
- 网站端请求搜索服务时，链路不稳定，排错也麻烦。

所以我们改成 Cloudflare Tunnel。

### Cloudflare Tunnel 是什么？

你可以把它理解成：

```txt
服务器主动连出去，建立一条到 Cloudflare 的安全通道。
```

以前是外部请求直接找你的服务器：

```txt
用户 -> Cloudflare -> 腾讯云公网 IP -> 服务器端口
```

现在变成：

```txt
用户 -> Cloudflare -> Tunnel -> 服务器本机 127.0.0.1:8000
```

服务器上运行的 `cloudflared` 就是这个通道的连接器。

### 这一步实际改了什么？

Cloudflare 侧：

```txt
Tunnel name: semantic-blog-search
Public hostname: api.keronshans.top
Service URL: http://127.0.0.1:8000
DNS: api.keronshans.top CNAME <tunnel-id>.cfargotunnel.com
```

网站侧：

```txt
SEARCH_API_URL=https://api.keronshans.top/search
```

服务器侧需要运行两个常驻服务：

```txt
semantic-blog-search 负责真正搜索
cloudflared 负责把 Cloudflare 请求送进服务器
```

### 为什么搜索服务还监听 127.0.0.1？

`127.0.0.1` 的意思是“只允许本机访问”。

也就是说：

```txt
公网用户不能直接访问 127.0.0.1:8000
只有服务器自己能访问 127.0.0.1:8000
```

Cloudflare Tunnel 的好处是：`cloudflared` 就运行在服务器本机，所以它能访问 `127.0.0.1:8000`，再把结果安全地带回 Cloudflare。

这比直接开放公网端口更适合你的项目。

### 安装 cloudflared 的命令是什么意思？

```bash
cd /tmp
```

进入临时目录，下载的安装包放这里就行。

```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
```

下载 Cloudflare Tunnel 的 Linux 安装包。

```bash
sudo dpkg -i cloudflared.deb
```

安装 `cloudflared`。

```bash
sudo cloudflared service install '<cloudflare-tunnel-token>'
```

把这个 Tunnel 注册成 Linux 后台服务。以后服务器重启时，它会自动启动。

`<cloudflare-tunnel-token>` 是连接密钥，不要提交到 GitHub，不要公开截图。

### 怎么判断 Tunnel 已经通了？

先看服务器上的连接器：

```bash
systemctl status cloudflared --no-pager
```

再看公网健康检查：

```bash
curl https://api.keronshans.top/health
```

成功时应该看到：

```json
{"status":"ok","collection_name":"blog_chunks"}
```

如果看到 Cloudflare `1033`，意思是：

```txt
Cloudflare 上的 Tunnel 和 DNS 已经存在，
但是服务器上的 cloudflared 还没有连上。
```

这通常要检查：

```bash
systemctl status cloudflared --no-pager
journalctl -u cloudflared -n 100 --no-pager
```

### 最终网站访问链路

现在完整链路是：

```txt
浏览器
  -> keronshans.top/blog-search-lab
  -> /api/blog-search
  -> https://api.keronshans.top/search
  -> Cloudflare Tunnel
  -> 腾讯云服务器 127.0.0.1:8000
  -> FastAPI /search
  -> Qdrant 向量搜索
  -> 返回 JSON 结果
```

浏览器看不到 Bearer Token，因为 token 只存在网站服务端环境变量和搜索服务器配置里。

## 22. 当前最大的维护风险

### token 泄露

如果 token 泄露，别人可以调用你的搜索接口。

解决：

```bash
nano /opt/semantic-blog-search/config.yaml
sudo systemctl restart semantic-blog-search
```

改掉 `server.api_token`。

### 服务器数据丢失

Qdrant 数据在：

```txt
/opt/semantic-blog-search/data/qdrant
```

如果服务器重装，这些数据会丢。

不过可以重新跑：

```bash
python scripts/sync_index.py --config config.yaml
```

重新生成。

### 模型缓存丢失

如果模型缓存丢了，服务器可能又连不上 Hugging Face。

解决方式是重新从本地传模型缓存，或者把模型保存成普通目录上传。

### 手动同步麻烦

现在文章同步靠 `scp`。

以后可以优化成：

- GitHub Actions 自动同步
- Webhook 触发服务器拉取
- 定时任务自动同步

### Tunnel 连接器停止

如果 `cloudflared` 停了，`api.keronshans.top` 可能返回 Cloudflare `1033`。

解决：

```bash
sudo systemctl restart cloudflared
systemctl status cloudflared --no-pager
curl https://api.keronshans.top/health
```

## 23. 一句话总结

这个项目做的是：

```txt
给你的个人博客增加一个语义搜索后端。
它读取 Markdown 博客，切成片段，生成向量，存进 Qdrant。
用户搜索时，它把查询也变成向量，然后找出最相关的文章片段。
现在后端和网站代理都已部署，最后一步是让服务器上的 cloudflared 连接器连上 Cloudflare Tunnel。
```

你做的不只是“装了一个工具”，而是完整走了一遍：

```txt
本地 Python 项目
-> GitHub 仓库
-> 云服务器部署
-> 模型缓存处理
-> 向量数据库
-> API 服务
-> Cloudflare Tunnel
-> Cloudflare 域名
-> 网站端代理接口
```

这就是一个真实的小型工程链路。
