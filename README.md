# semantic-blog-search

一个面向 Hexo Markdown 博客的本地语义搜索实验项目。

这个项目的目标是做一个结构清晰、容易学习和维护的 MVP：读取本地博客文章，切分成 chunk，生成 embedding，并写入 Qdrant local mode。之后可以在命令行里输入查询语句，得到相关博客片段。

## 这个项目不是什么

- 不是完整 RAG 系统
- 不是商业级搜索引擎
- 不是大模型问答系统
- 不接入 OpenAI API
- 不包含登录、前端、Docker 或 CI/CD

## 项目结构

```txt
semantic-blog-search/
├── README.md
├── requirements.txt
├── .gitignore
├── config.example.yaml
├── src/
│   └── semantic_blog_search/
│       ├── __init__.py
│       ├── config.py
│       ├── parser.py
│       ├── chunker.py
│       ├── embedder.py
│       ├── vector_store.py
│       ├── indexer.py
│       └── searcher.py
├── scripts/
│   ├── build_index.py
│   └── search.py
├── examples/
│   └── posts/
│       └── sample.md
└── tests/
    └── test_chunker.py
```

## 安装依赖

建议先创建虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows 用户激活虚拟环境：

```bash
.venv\Scripts\activate
```

## 准备配置文件

```bash
cp config.example.yaml config.yaml
```

Windows PowerShell 可以使用：

```powershell
Copy-Item config.example.yaml config.yaml
```

然后检查 `config.yaml` 里的 `posts_dir` 是否指向你的 Hexo Markdown 文章目录。

## 构建索引

```bash
python scripts/build_index.py --config config.yaml
```

第一次运行会下载 embedding 模型，可能需要一些时间。

## 执行搜索

```bash
python scripts/search.py --config config.yaml "线段树懒标记为什么要 pushdown"
```

搜索结果会输出标题、URL、相似度分数、来源文件和片段。

## 增量同步索引

日常更新博客后，建议使用增量同步：

```bash
python scripts/sync_index.py --config config.yaml
```

它会记录每篇 Markdown 文件的内容 hash：

- 新增文章：解析、切块、embedding、写入 Qdrant
- 修改文章：删除旧 chunk，再写入新 chunk
- 删除文章：删除对应 chunk
- 未变化文章：跳过，不重新 embedding

索引状态默认保存在：

```txt
./data/index_manifest.json
```

`data/` 已经在 `.gitignore` 中，不应该提交到 GitHub。

## 启动常驻搜索 API

如果你希望接入个人网站后台，可以启动本地 API 服务：

```bash
python scripts/server.py --config config.yaml
```

启动前需要在 `config.yaml` 里配置私有 token：

```yaml
server:
  host: "127.0.0.1"
  port: 8000
  api_token: "replace-with-a-long-random-token"
```

默认地址：

```txt
http://127.0.0.1:8000
```

健康检查：

```bash
curl "http://127.0.0.1:8000/health"
```

搜索接口：

```bash
curl -H "Authorization: Bearer replace-with-a-long-random-token" "http://127.0.0.1:8000/search?q=线段树懒标记为什么要 pushdown&top_k=5"
```

这个服务启动时会加载一次 embedding 模型，并让模型常驻内存。之后每次搜索请求都会复用同一个模型实例，因此比反复执行命令行搜索更适合网站后台调用。

部署到 `api.keronshans.top` 的详细步骤见：

```txt
docs/deploy-to-keronshans.md
```

## Cloudflare Tunnel 接入方式

当前线上推荐使用 Cloudflare Tunnel 暴露搜索 API，而不是直接把服务器公网 IP 或 `8080` 端口暴露出去。

整体链路是：

```txt
keronshans.top 页面
  -> /api/blog-search
  -> https://api.keronshans.top/search
  -> Cloudflare Tunnel
  -> 腾讯云服务器 127.0.0.1:8000
  -> semantic-blog-search FastAPI
```

这样做的原因：

- Python 搜索服务仍然只监听 `127.0.0.1:8000`，不直接暴露公网端口。
- Cloudflare 负责 HTTPS 和公网入口。
- 避免直接访问腾讯云 IP、备案页、DNS-only/proxied 混用带来的不稳定。
- 网站前端仍然只请求主站自己的 `/api/blog-search`，不会暴露 Bearer Token。

当前 Cloudflare 侧配置：

```txt
Tunnel name: semantic-blog-search
Public hostname: api.keronshans.top
Tunnel service: http://127.0.0.1:8000
DNS: api.keronshans.top CNAME <tunnel-id>.cfargotunnel.com
```

服务器上需要常驻两个服务：

```bash
systemctl status semantic-blog-search --no-pager
systemctl status cloudflared --no-pager
```

验证公网入口：

```bash
curl https://api.keronshans.top/health
curl "https://api.keronshans.top/search?q=线段树&top_k=5"
curl -H "Authorization: Bearer <token>" "https://api.keronshans.top/search?q=线段树&top_k=5"
```

预期结果：

- `/health` 返回 `status: ok`。
- 不带 token 的 `/search` 返回 `401`。
- 带 token 的 `/search` 返回 JSON 搜索结果。

## 配置项说明

- `posts_dir`：Hexo Markdown 文章目录。
- `url_prefix`：生成文章 URL 时使用的前缀，例如 `/posts`。
- `qdrant.db_path`：Qdrant local mode 的本地数据目录。
- `qdrant.collection_name`：Qdrant collection 名称。
- `embedding.model_name`：sentence-transformers 使用的 embedding 模型。
- `chunk.chunk_size`：每个 chunk 目标字符数。
- `chunk.chunk_overlap`：相邻 chunk 之间保留的重叠字符数。
- `search.top_k`：默认返回的搜索结果数量。
- `index.manifest_path`：增量索引状态文件路径。
- `server.host`：API 服务监听地址。本地使用 `127.0.0.1`，云平台可能需要 `0.0.0.0`。
- `server.port`：API 服务端口。
- `server.api_token`：保护 `/search` 接口的 Bearer Token，不要提交到 GitHub。

## 后续 TODO

- 支持更好的 Markdown 清洗，例如去掉代码块或图片语法。
- 支持按 tags、日期范围过滤搜索结果。
- 支持更友好的 snippet 生成策略。
- 增加更多解析和搜索测试。

## 当前限制

这个 MVP 只做语义检索 API 和命令行搜索。它不会生成答案，也不会理解复杂查询语法。chunk 切分策略比较朴素，主要按段落拼接；如果文章里有大量代码或表格，搜索片段可能还不够理想。
