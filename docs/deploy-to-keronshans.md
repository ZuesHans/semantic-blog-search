# Deploy semantic-blog-search for keronshans.top

This guide keeps `keronshans.top` on Cloudflare Pages / Workers and runs the Python search API on a separate lightweight Ubuntu server.

The current production path uses Cloudflare Tunnel:

```txt
keronshans.top
  -> /api/blog-search
  -> https://api.keronshans.top/search
  -> Cloudflare Tunnel
  -> 127.0.0.1:8000 on the Tencent Cloud server
```

## 1. Prepare the server

Use Ubuntu 24.04 with at least 2 GB RAM and 20 GB disk.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl
sudo mkdir -p /opt/semantic-blog-search
sudo chown -R ubuntu:ubuntu /opt/semantic-blog-search
```

Upload or clone this project into:

```txt
/opt/semantic-blog-search
```

Then install dependencies:

```bash
cd /opt/semantic-blog-search
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## 2. Configure the API

Create `config.yaml` from `config.example.yaml` and edit it:

```yaml
server:
  host: "127.0.0.1"
  port: 8000
  api_token: "replace-with-a-long-random-token"
```

Keep `config.yaml` private. It is ignored by Git because it contains the API token and local paths.

Run the first index sync:

```bash
python scripts/sync_index.py --config config.yaml
```

## 3. Run with systemd

Copy the service template:

```bash
sudo cp deploy/semantic-blog-search.service.example /etc/systemd/system/semantic-blog-search.service
sudo systemctl daemon-reload
sudo systemctl enable semantic-blog-search
sudo systemctl start semantic-blog-search
sudo systemctl status semantic-blog-search
```

Local health check:

```bash
curl http://127.0.0.1:8000/health
```

## 4. Connect with Cloudflare Tunnel

The search API should keep listening on `127.0.0.1:8000`. Do not expose port `8000` directly to the public internet.

Create or reuse this Cloudflare Tunnel:

```txt
Tunnel name: semantic-blog-search
Public hostname: api.keronshans.top
Service type: HTTP
Service URL: 127.0.0.1:8000
```

The DNS record should be a proxied CNAME created for the tunnel:

```txt
Type: CNAME
Name: api
Content: <tunnel-id>.cfargotunnel.com
Proxy status: Proxied
```

On the server, install and run `cloudflared` with the tunnel token from Cloudflare:

```bash
cd /tmp
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
sudo cloudflared service install '<cloudflare-tunnel-token>'
```

Do not commit or publish the tunnel token. It lets a server connect to this Cloudflare Tunnel.

Check the connector:

```bash
systemctl status cloudflared --no-pager
```

Public checks:

```bash
curl https://api.keronshans.top/health
curl "https://api.keronshans.top/search?q=线段树&top_k=5"
curl -H "Authorization: Bearer replace-with-a-long-random-token" "https://api.keronshans.top/search?q=线段树&top_k=5"
```

The second command should return `401`; the third should return results.

If `https://api.keronshans.top/health` returns Cloudflare error `1033`, the DNS and Tunnel exist, but the server-side `cloudflared` connector is not running yet.

## 5. Connect the Cloudflare Pages website

In the website repo, add or keep a server route:

```txt
app/api/blog-search/route.ts
```

Use the example in:

```txt
integrations/cloudflare-pages/app-api-blog-search-route.ts
```

Configure Cloudflare Workers / Pages environment variables:

```txt
SEARCH_API_URL=https://api.keronshans.top/search
SEARCH_API_TOKEN=<same token as config.yaml>
```

The browser should call the Pages route:

```txt
/api/blog-search?q=线段树&top_k=5
```

The browser must not call `api.keronshans.top/search` directly, because that would expose the Bearer token.

## 6. Update the index after blog changes

SSH into the server and run:

```bash
cd /opt/semantic-blog-search
. .venv/bin/activate
python scripts/sync_index.py --config config.yaml
sudo systemctl restart semantic-blog-search
```

Restarting the service is optional after index sync, but useful if you want a clean process after manual maintenance.
