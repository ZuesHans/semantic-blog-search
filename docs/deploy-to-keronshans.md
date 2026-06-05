# Deploy semantic-blog-search for keronshans.top

This guide keeps `keronshans.top` on Cloudflare Pages and runs the Python search API on a separate lightweight Ubuntu server.

## 1. Prepare the server

Use Ubuntu 24.04 with at least 2 GB RAM and 20 GB disk.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git caddy
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

## 4. Reverse proxy with Caddy

Copy the Caddy template into `/etc/caddy/Caddyfile` or merge it into the existing file:

```caddy
api.keronshans.top {
    reverse_proxy 127.0.0.1:8000
}
```

Reload Caddy:

```bash
sudo systemctl reload caddy
```

## 5. Add Cloudflare DNS

After buying the server, get its public IPv4 address.

In Cloudflare DNS for `keronshans.top`, add:

```txt
Type: A
Name: api
Content: <server public IPv4>
Proxy status: Proxied
TTL: Auto
```

Do not edit the existing root domain record for `keronshans.top`; it is managed by Cloudflare Pages.

Public checks:

```bash
curl https://api.keronshans.top/health
curl "https://api.keronshans.top/search?q=线段树&top_k=5"
curl -H "Authorization: Bearer replace-with-a-long-random-token" "https://api.keronshans.top/search?q=线段树&top_k=5"
```

The second command should return `401`; the third should return results.

## 6. Connect the Cloudflare Pages website

In the website repo `ZuesHans/ZuesHans.github.io`, add a server route:

```txt
app/api/blog-search/route.ts
```

Use the example in:

```txt
integrations/cloudflare-pages/app-api-blog-search-route.ts
```

Configure Cloudflare Pages environment variables:

```txt
SEARCH_API_URL=https://api.keronshans.top/search
SEARCH_API_TOKEN=<same token as config.yaml>
```

The browser should call the Pages route:

```txt
/api/blog-search?q=线段树&top_k=5
```

The browser must not call `api.keronshans.top/search` directly, because that would expose the Bearer token.

## 7. Update the index after blog changes

SSH into the server and run:

```bash
cd /opt/semantic-blog-search
. .venv/bin/activate
python scripts/sync_index.py --config config.yaml
sudo systemctl restart semantic-blog-search
```

Restarting the service is optional after index sync, but useful if you want a clean process after manual maintenance.
