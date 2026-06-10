# semantic-blog-search Website Integration Handoff

这份文档给负责 `keronshans.top` 网站端的 agent 阅读。目标是让网站端用一个简单、好维护的方式接入已经部署好的本地语义搜索 API。

## 当前进度

- 搜索项目仓库：`https://github.com/ZuesHans/semantic-blog-search`
- 网站仓库：`https://github.com/ZuesHans/ZuesHans.github.io`
- 主站域名：`https://keronshans.top`
- 搜索 API 域名：`https://api.keronshans.top`
- Cloudflare DNS：`api.keronshans.top` 已指向腾讯云服务器 `175.178.216.243`，并开启 proxy。
- 腾讯云服务器：搜索项目已部署到 `/opt/semantic-blog-search`。
- 博客 Markdown 源文件：已同步到 `/opt/keronshans_blogsorce/content/posts`。
- 索引状态：`sync_index.py` 已经跑通，可以搜索出结果。
- 服务状态：FastAPI 常驻服务、Nginx 反代、Cloudflare HTTPS 链路已经跑通。

## 架构说明

主站仍然由 Cloudflare Pages 托管。Python embedding 模型不能直接跑在 Cloudflare Pages 里，所以搜索 API 单独部署在腾讯云服务器上。

```txt
Browser
  -> keronshans.top
  -> Cloudflare Pages / Next.js route: /api/blog-search
  -> https://api.keronshans.top/search
  -> Nginx
  -> FastAPI on 127.0.0.1:8000
  -> Qdrant local mode
```

浏览器不要直接请求 `api.keronshans.top/search`，因为 `/search` 需要 Bearer Token。网站端应该提供一个服务端代理接口，把 token 藏在 Cloudflare Pages 环境变量里。

## 搜索 API

### Health

```txt
GET https://api.keronshans.top/health
```

不需要 token。

正常返回：

```json
{
  "status": "ok",
  "collection_name": "blog_chunks"
}
```

### Search

```txt
GET https://api.keronshans.top/search?q=线段树&top_k=5
Authorization: Bearer <SEARCH_API_TOKEN>
```

需要 Bearer Token。不带 token 会返回 `401`。

正常返回格式：

```json
{
  "query": "线段树",
  "results": [
    {
      "title": "文章标题",
      "url": "/posts/xxx",
      "score": 0.8231,
      "snippet": "相关片段...",
      "source_file": "/opt/keronshans_blogsorce/content/posts/example.md"
    }
  ]
}
```

## 网站端接入方式

在 `ZuesHans.github.io` 仓库中添加 Next.js route：

```txt
app/api/blog-search/route.ts
```

当前搜索项目已经提供模板：

```txt
integrations/cloudflare-pages/app-api-blog-search-route.ts
```

把模板复制到网站仓库对应路径即可。它会读取 Cloudflare Pages 环境变量：

```txt
SEARCH_API_URL=https://api.keronshans.top/search
SEARCH_API_TOKEN=<服务器 config.yaml 里的 server.api_token>
```

前端页面只请求：

```txt
/api/blog-search?q=线段树&top_k=5
```

不要在前端代码里硬编码 `SEARCH_API_TOKEN`。

## 建议的网站端 UI

第一版保持简单：

- 做一个隐藏或后台使用的搜索页面，例如 `/admin/search` 或 `/blog-search-lab`。
- 页面包含一个输入框、一个搜索按钮、一个结果列表。
- 每条结果显示：
  - title
  - score
  - snippet
  - source_file 或文章链接
- 点击结果跳转到 `result.url`。
- 加一个 loading 状态和空结果提示。

暂时不要做：

- 登录系统
- 复杂筛选器
- 自动问答/RAG
- 前端直接连搜索 API

## 日常更新流程

本地博客 Markdown 更新后，先把 `posts` 同步到服务器。

在本地 Windows PowerShell：

```powershell
scp -r "C:\Users\31802\Documents\keronshans_blogsorce\content\posts" ubuntu@175.178.216.243:/home/ubuntu/
```

在服务器：

```bash
rm -rf /opt/keronshans_blogsorce/content/posts
mv /home/ubuntu/posts /opt/keronshans_blogsorce/content/posts
cd /opt/semantic-blog-search
. .venv/bin/activate
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/sync_index.py --config config.yaml
```

`sync_index.py` 是增量索引：

- 新增文章：写入新 chunk
- 修改文章：删除旧 chunk，再写入新 chunk
- 删除文章：删除对应 chunk
- 未变化文章：跳过

服务通常不需要重启。

## 服务器维护命令

查看服务状态：

```bash
systemctl status semantic-blog-search --no-pager
systemctl status nginx --no-pager
```

查看搜索服务日志：

```bash
journalctl -u semantic-blog-search -n 100 --no-pager
```

重启搜索服务：

```bash
sudo systemctl restart semantic-blog-search
```

本机测试：

```bash
curl http://127.0.0.1:8000/health
```

公网测试：

```bash
curl https://api.keronshans.top/health
curl "https://api.keronshans.top/search?q=线段树&top_k=5"
curl -H "Authorization: Bearer <SEARCH_API_TOKEN>" "https://api.keronshans.top/search?q=线段树&top_k=5"
```

第二条应该返回 `401`，第三条应该返回搜索结果。

## 重要安全事项

- 不要提交服务器上的 `config.yaml`。
- 不要把 `server.api_token` 写进前端代码。
- 不要把 `data/`、Qdrant 本地数据库、模型缓存提交到 GitHub。
- 如果 token 泄露，立刻改服务器 `/opt/semantic-blog-search/config.yaml` 里的 `server.api_token`，然后重启服务。

## 目前已知限制

- 搜索是语义检索，不是问答系统，不会生成答案。
- 搜索质量取决于 chunk 切分和 embedding 模型。
- 腾讯云服务器访问 Hugging Face 不稳定，所以线上使用本地缓存和离线模式。
- 日常 Markdown 同步目前是手动 `scp`，之后可以升级为 GitHub Actions、Webhook 或定时同步。
- 当前 API 适合先做后台私用；如果公开给访客，需要再加限流、缓存和更完整的错误处理。
