# Deploy to Fly.io

This guide deploys the quiz app (Flask API + Vue SPA + JSON files) as **one Fly.io app** running a single container with **nginx** (static files + reverse proxy) and **gunicorn** (Flask API), managed by **supervisord**. A **Fly Volume** holds `backend/data/*.json` so it survives restarts and redeploys.

---

## Overview

| Layer | What runs |
|-------|-----------|
| Public URL | `https://your-app-name.fly.dev` (or your custom domain) |
| Container | nginx (port 8080) + gunicorn (127.0.0.1:8000), via supervisord |
| Static files | `frontend/dist/` (Vue build), baked into the image |
| API | gunicorn → Flask, proxied by nginx under `/api` |
| Data | Fly Volume mounted at `/data` → `users.json`, `questions.json`, `settings.json` |
| Secret | `JWT_SECRET` set as a Fly secret |

Fly machines have an **ephemeral root filesystem** — anything written outside a mounted volume is lost on redeploy or restart. Since this app stores all state as JSON files, a volume is required.

---

## Part 1 — Prerequisites (on your Windows machine)

### 1.1 Install flyctl

```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

Close and reopen your terminal, then confirm:

```powershell
fly version
```

### 1.2 Sign up / log in

```powershell
fly auth signup   # or: fly auth login
```

A card is required even on the free allowance (small apps + a small volume typically fit within it).

### 1.3 Your code in Git (recommended)

```powershell
cd "C:\Users\david\dev\IAAC\GH-test\macad-grasshopper-test"
git add .
git commit -m "Add Fly.io deployment files"
```

`fly deploy` builds from your local working directory, so Git isn't strictly required — but keep your work committed.

### 1.4 Generate a JWT secret

```powershell
[Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
```

Save the output — you'll set it as a Fly secret in Part 6.

---

## Part 2 — One code change: make `DATA_DIR` configurable

`backend/app.py` currently hardcodes the data directory next to the source file:

```python
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
```

For Fly, the data directory needs to point at the mounted volume instead. Change it to:

```python
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
```

This is backward compatible — running locally with `python app.py` still uses `backend/data` since `DATA_DIR` won't be set.

---

## Part 3 — Create the deployment files

Create a `deploy/` folder in the project root with the files below.

### 3.1 `deploy/nginx.conf`

```nginx
worker_processes 1;
pid /tmp/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    access_log    /dev/stdout;
    error_log     /dev/stderr;

    server {
        listen 8080;
        server_name _;

        root /app/frontend/dist;
        index index.html;

        # Vue SPA — history mode needs fallback to index.html
        location / {
            try_files $uri $uri/ /index.html;
        }

        # API proxy to gunicorn
        location /api {
            proxy_pass http://127.0.0.1:8000;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 3.2 `deploy/supervisord.conf`

```ini
[supervisord]
nodaemon=true
user=root
logfile=/dev/stdout
logfile_maxbytes=0

[program:gunicorn]
command=/app/backend/start-backend.sh
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:nginx]
command=nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

### 3.3 `deploy/start-backend.sh`

Seeds the volume from the JSON files baked into the image on first boot (the volume starts empty), then starts gunicorn. Existing files on the volume are never overwritten, so later writes (new users, quiz results, edited questions) persist across deploys.

```bash
#!/bin/sh
set -e

mkdir -p "$DATA_DIR"

for f in /app/backend/data-seed/*.json; do
    name=$(basename "$f")
    if [ ! -f "$DATA_DIR/$name" ]; then
        echo "Seeding $name into $DATA_DIR"
        cp "$f" "$DATA_DIR/$name"
    fi
done

cd /app/backend
exec gunicorn -w 2 -b 127.0.0.1:8000 app:app
```

Use LF line endings for this file (not CRLF) — save it with your editor set to Unix line endings, since it runs inside Linux.

### 3.4 `Dockerfile` (project root)

```dockerfile
# ---- Stage 1: build the Vue frontend ----
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: runtime image (nginx + gunicorn via supervisord) ----
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt gunicorn

COPY backend/ backend/
# Keep the committed JSON files as seed data; the running app writes to $DATA_DIR (the volume) instead.
RUN mv backend/data backend/data-seed

COPY --from=frontend-build /app/frontend/dist frontend/dist

COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY deploy/start-backend.sh backend/start-backend.sh
RUN chmod +x backend/start-backend.sh

EXPOSE 8080
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

### 3.5 `.dockerignore` (project root)

```
frontend/node_modules
frontend/dist
backend/__pycache__
backend/venv
.git
.claude
```

---

## Part 4 — Initialize the Fly app

From the project root:

```powershell
fly launch --no-deploy
```

- **App name**: choose one (e.g. `macad-quiz-app`) — must be globally unique on Fly.
- **Region**: pick the one closest to your users.
- **Postgres / Redis**: say **No** to both — this app doesn't use them.
- It detects the `Dockerfile` and generates a `fly.toml`. Say **no** if it asks to deploy immediately — the volume and secrets need to be set up first.

Open the generated `fly.toml` and make sure it looks like this (adjust `app` to the name you chose):

```toml
app = "macad-quiz-app"
primary_region = "iad"

[build]

[env]
  DATA_DIR = "/data"

[[mounts]]
  source = "quiz_data"
  destination = "/data"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 1

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512
```

`min_machines_running = 1` keeps the app warm — with `auto_stop_machines` on, a scaled-to-zero machine would need a moment to boot on the next request, which also means an in-progress quiz timer could stall. Set it to `0` instead if cost matters more than avoiding cold starts.

---

## Part 5 — Create the persistent volume

Match the `source` name used in `fly.toml` (`quiz_data` above):

```powershell
fly volumes create quiz_data --region iad --size 1
```

- `--region` must match `primary_region` in `fly.toml`.
- `--size 1` is 1 GB — far more than JSON files need, but it's the minimum.
- If you plan to run more than one machine, create a volume per region/machine (volumes are single-machine by default) or keep `min_machines_running`/scaling at 1 to avoid data-consistency issues between machines with separate volumes.

---

## Part 6 — Set secrets

```powershell
fly secrets set JWT_SECRET="paste-your-long-random-secret-here"
```

This restarts the app once the first deploy exists; for the very first deploy it just gets picked up automatically.

---

## Part 7 — Deploy

```powershell
fly deploy
```

This builds the Docker image (Fly's remote builder handles it — no local Docker required, though local Docker works too if installed), pushes it, creates a machine with the volume attached, and starts it.

Watch progress:

```powershell
fly logs
```

---

## Part 8 — Verify

```powershell
fly status
fly open
```

`fly open` launches your browser to `https://your-app-name.fly.dev`. Check:

| Test | Expected |
|------|----------|
| `/` | Login page loads |
| Register | New account works (first registered user becomes admin) |
| Login | Redirects to `/quiz` |
| Take quiz | Questions load, timer works |
| Submit | Results page shows |
| `/admin` | Admin panel loads for the first user |
| `fly machine restart <id>` | App comes back up, previously created users/results still there |

---

## Part 9 — Custom domain & HTTPS

Fly issues a free HTTPS cert for `*.fly.dev` automatically. For a custom domain:

```powershell
fly certs add quiz.example.com
```

Follow the printed instructions to add a `CNAME` (or `A`/`AAAA`) record at your DNS provider, then check status:

```powershell
fly certs show quiz.example.com
```

---

## Part 10 — Deploying updates

```powershell
cd "C:\Users\david\dev\IAAC\GH-test\macad-grasshopper-test"
fly deploy
```

Every `fly deploy` rebuilds the image (new frontend build + latest backend code) and replaces the running machine, but the volume — and everything in `/data` — is untouched.

---

## Part 11 — Backups

All state lives on the volume at `/data`: `users.json`, `questions.json`, `settings.json`.

### Download to your PC

```powershell
fly ssh sftp get /data/users.json ./users.json.bak
fly ssh sftp get /data/questions.json ./questions.json.bak
```

### Upload a restored/edited file

```powershell
fly ssh sftp shell
# then, inside the sftp shell:
put ./questions.json.bak /data/questions.json
```

### Snapshot the whole volume

Fly automatically takes daily volume snapshots (retained ~5 days on the free tier). List and restore:

```powershell
fly volumes list
fly volumes snapshots list <volume-id>
```

---

## Part 12 — Troubleshooting

### Build fails on `npm ci`

Make sure `frontend/package-lock.json` is committed — `npm ci` requires it.

### 502 / blank page

```powershell
fly logs
fly ssh console
curl http://127.0.0.1:8000/api/quiz/status
```

Check that both `gunicorn` and `nginx` show as running in the supervisord log output.

### "Invalid token" after a deploy

`JWT_SECRET` changed → all users must log in again. Don't rotate it unless you mean to invalidate sessions.

### Data reset after redeploy

The volume isn't mounted, or `DATA_DIR` isn't set to `/data`. Check:

```powershell
fly ssh console -C "env | grep DATA_DIR"
fly ssh console -C "ls -la /data"
```

Also confirm the `[[mounts]]` block in `fly.toml` matches an existing volume (`fly volumes list`).

### Machine keeps restarting

```powershell
fly logs
fly status
```

Usually a crash in `start-backend.sh` (bad line endings — must be LF, not CRLF) or a Python import error from `requirements.txt`.

---

## Part 13 — Security checklist

- [ ] `JWT_SECRET` set via `fly secrets`, not committed to Git
- [ ] `force_https = true` in `fly.toml` (already set above)
- [ ] Volume created and mounted at `/data` before real users register
- [ ] `backend/data-seed/*.json` in the image only used for first-boot seeding — no real user data baked into the image itself
- [ ] Regular backups via `fly ssh sftp` or volume snapshots

---

## Quick reference

| Item | Location |
|------|----------|
| App config | `fly.toml` (project root) |
| Dockerfile | `Dockerfile` (project root) |
| nginx/supervisord config | `deploy/nginx.conf`, `deploy/supervisord.conf` |
| Backend start script | `deploy/start-backend.sh` |
| Data (on the volume) | `/data/users.json`, `/data/questions.json`, `/data/settings.json` |
| Seed data (in the image) | `/app/backend/data-seed/` |

**Useful commands:**

```powershell
fly deploy
fly logs
fly status
fly ssh console
fly secrets list
fly volumes list
```
