# Deploy to AWS Lightsail

This guide deploys the quiz app (Flask API + Vue SPA + JSON files) on **one Lightsail Ubuntu server** with **nginx** and **gunicorn**. It matches how the app runs locally, but in production mode.

---

## Overview

| Layer | What runs |
|-------|-----------|
| Public URL | `https://your-domain.com` |
| Web server | nginx (port 80/443) |
| Static files | `frontend/dist/` (Vue build) |
| API | gunicorn → Flask on `127.0.0.1:5000` |
| Data | `backend/data/users.json`, `questions.json` |
| Secret | `JWT_SECRET` environment variable |

---

## Part 1 — Prerequisites (on your Windows machine)

### 1.1 AWS account

- Sign up at [https://aws.amazon.com](https://aws.amazon.com) if you don't have an account.
- Have a credit card ready (Lightsail is ~$5–10/month).

### 1.2 Your code in Git (recommended)

Push the project to GitHub, GitLab, or Bitbucket. Example:

```bash
cd "C:\deeploy\projects\claude test"
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USER/quiz-app.git
git push -u origin main
```

If you don't use Git, you can upload files with **SCP** or **SFTP** instead (covered in step 4.3).

### 1.3 Optional: a domain name

- You can use the Lightsail public IP initially (`http://YOUR_IP`).
- For HTTPS with a custom domain, buy one (Route 53, Namecheap, etc.) and point DNS at Lightsail later.

### 1.4 Generate a JWT secret

On your PC, run in PowerShell:

```powershell
[Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
```

Save the output — you'll use it as `JWT_SECRET`.

---

## Part 2 — Create the Lightsail instance

### 2.1 Open Lightsail

1. Go to [https://lightsail.aws.amazon.com](https://lightsail.aws.amazon.com)
2. Sign in to AWS
3. Click **Create instance**

### 2.2 Instance settings

| Setting | Value |
|---------|--------|
| Region | Closest to your users (e.g. `us-east-1`) |
| Platform | **Linux/Unix** |
| Blueprint | **OS Only → Ubuntu 22.04 LTS** |
| Plan | **$5/month** (1 GB RAM) is fine to start; use $10 if builds feel slow |

### 2.3 Name and create

- Name: `quiz-app`
- Click **Create instance**
- Wait until status is **Running**

### 2.4 Note the public IP

On the instance page, copy the **Public IP** (e.g. `3.15.xx.xx`).

### 2.5 Open firewall ports

1. Instance → **Networking** tab
2. Under **IPv4 Firewall**, add:
   - **HTTP** (port 80)
   - **HTTPS** (port 443)
3. SSH (22) is usually already open

---

## Part 3 — Connect to the server

### 3.1 SSH from Lightsail browser

1. Instance page → **Connect using SSH** (opens browser terminal)

### 3.2 Or SSH from Windows PowerShell

1. Lightsail → **Account** → **SSH keys** → download default key
2. Connect:

```powershell
ssh -i "C:\path\to\your-key.pem" ubuntu@YOUR_PUBLIC_IP
```

Default user is **`ubuntu`**.

---

## Part 4 — Install server software

Run these on the server:

```bash
sudo apt update && sudo apt upgrade -y
```

### 4.1 Python, nginx, Git

```bash
sudo apt install -y python3 python3-pip python3-venv nginx git
```

### 4.2 Node.js 20 (for building the frontend)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v   # should show v20.x
npm -v
```

---

## Part 5 — Get your app onto the server

### 5.1 Clone from Git (recommended)

```bash
cd ~
git clone https://github.com/YOUR_USER/quiz-app.git
cd quiz-app
```

Your layout should look like:

```
~/quiz-app/
  backend/
    app.py
    requirements.txt
    data/
  frontend/
    package.json
    src/
```

### 5.2 Or upload without Git

From your Windows machine:

```powershell
scp -i "C:\path\to\your-key.pem" -r "C:\deeploy\projects\claude test" ubuntu@YOUR_PUBLIC_IP:~/quiz-app
```

Then on the server:

```bash
cd ~/quiz-app
```

### 5.3 Confirm data files exist

```bash
ls -la backend/data/
```

You should see `users.json` and `questions.json`. These hold all users and questions — **back them up** before going live.

---

## Part 6 — Set up the backend

### 6.1 Create a virtual environment

```bash
cd ~/quiz-app/backend
python3 -m venv venv
source venv/bin/activate
```

Your prompt should show `(venv)`.

### 6.2 Install Python dependencies + gunicorn

`requirements.txt` has Flask but not gunicorn. Install both:

```bash
pip install -r requirements.txt gunicorn
```

### 6.3 Set JWT secret

The app reads this from the environment (`JWT_SECRET` in `backend/app.py`). Create an env file (not committed to Git):

```bash
sudo nano /etc/quiz-app.env
```

Add:

```bash
JWT_SECRET=paste-your-long-random-secret-here
```

Save: `Ctrl+O`, Enter, `Ctrl+X`.

Lock it down:

```bash
sudo chmod 600 /etc/quiz-app.env
```

### 6.4 Test gunicorn manually

```bash
cd ~/quiz-app/backend
source venv/bin/activate
set -a && source /etc/quiz-app.env && set +a
gunicorn -w 2 -b 127.0.0.1:5000 app:app
```

In another SSH session (or from the server):

```bash
curl http://127.0.0.1:5000/api/quiz
```

You should get JSON (or a 401 if that route needs auth — try a public route if you have one). If it responds, press `Ctrl+C` to stop gunicorn.

---

## Part 7 — Build the frontend

```bash
cd ~/quiz-app/frontend
npm install
npm run build
```

This creates `frontend/dist/` with static HTML/JS/CSS.

Verify:

```bash
ls dist/
# index.html, assets/, etc.
```

The frontend calls `/api/...` (relative URLs), so nginx must proxy `/api` to Flask — no code changes needed.

---

## Part 8 — Run gunicorn as a system service

So the API restarts on reboot and stays running.

### 8.1 Create systemd unit

```bash
sudo nano /etc/systemd/system/quiz-backend.service
```

Paste (adjust paths if your folder name differs):

```ini
[Unit]
Description=Quiz App Flask Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/quiz-app/backend
EnvironmentFile=/etc/quiz-app.env
ExecStart=/home/ubuntu/quiz-app/backend/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 8.2 Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable quiz-backend
sudo systemctl start quiz-backend
sudo systemctl status quiz-backend
```

Status should show **active (running)**. If not:

```bash
sudo journalctl -u quiz-backend -n 50 --no-pager
```

---

## Part 9 — Configure nginx

### 9.1 Create site config

```bash
sudo nano /etc/nginx/sites-available/quiz-app
```

Paste:

```nginx
server {
    listen 80;
    server_name _;   # replace with yourdomain.com after DNS is set

    root /home/ubuntu/quiz-app/frontend/dist;
    index index.html;

    # Vue SPA — history mode needs fallback to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (same as Vite dev proxy)
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 9.2 Enable site and disable default

```bash
sudo ln -sf /etc/nginx/sites-available/quiz-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 9.3 Test in browser

Open:

```
http://YOUR_PUBLIC_IP
```

You should see the login page. Register a user — the **first registered user becomes admin** per your app logic.

---

## Part 10 — HTTPS (recommended)

### Option A: Lightsail built-in certificate (easiest)

1. Lightsail → **Networking** → **Certificates**
2. **Create certificate** → add your domain (`quiz.example.com`)
3. Add the DNS validation records Lightsail shows (at your domain registrar)
4. After validated: **Create distribution** (CDN) or attach cert to instance per Lightsail docs
5. Point domain **A record** to the Lightsail static IP

### Option B: Certbot on the instance (if using a domain pointing to the IP)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Certbot updates nginx for HTTPS and auto-renewal.

Update nginx `server_name`:

```nginx
server_name yourdomain.com;
```

Then:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## Part 11 — Smoke test checklist

| Test | Expected |
|------|----------|
| `http://YOUR_IP/` | Login page loads |
| Register | New account works |
| Login | Redirects to `/quiz` |
| Take quiz | Questions load, timer works |
| Submit | Results page shows |
| `/admin` (first user) | Admin panel loads |
| Reboot server | App still works after `sudo reboot` |

After reboot:

```bash
sudo systemctl status quiz-backend
sudo systemctl status nginx
```

---

## Part 12 — Deploying updates later

When you change code:

```bash
cd ~/quiz-app
git pull   # or re-upload files

# Backend changes
cd backend
source venv/bin/activate
pip install -r requirements.txt gunicorn
sudo systemctl restart quiz-backend

# Frontend changes
cd ../frontend
npm install
npm run build
# nginx serves new dist/ automatically — no restart needed
```

---

## Part 13 — Backups (important)

All state lives in two files:

- `backend/data/users.json` — users, passwords (hashed), quiz results
- `backend/data/questions.json` — questions

### Manual backup

```bash
cp backend/data/users.json backend/data/users.json.bak
cp backend/data/questions.json backend/data/questions.json.bak
```

### Download to your PC

```powershell
scp -i "C:\path\to\your-key.pem" ubuntu@YOUR_PUBLIC_IP:~/quiz-app/backend/data/users.json .
```

Consider weekly backups or Lightsail **snapshots** of the whole disk.

---

## Part 14 — Troubleshooting

### Blank page or 502 on `/api`

```bash
sudo systemctl status quiz-backend
sudo journalctl -u quiz-backend -f
curl http://127.0.0.1:5000/api/quiz
```

### 404 on `/quiz` or `/admin` after refresh

nginx must have `try_files $uri $uri/ /index.html;` in the `/` location.

### Login works but admin doesn't

Only the **first registered user** is admin. Check `users.json` on the server.

### "Invalid token" after deploy

`JWT_SECRET` changed → all users must log in again. Keep the same secret across redeploys.

### Permission errors on JSON files

```bash
ls -la ~/quiz-app/backend/data/
# ubuntu user must own and write these files
sudo chown -R ubuntu:ubuntu ~/quiz-app/backend/data
```

### nginx error

```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

---

## Part 15 — Security checklist

- [ ] `JWT_SECRET` is a long random value, not `change-me-in-production`
- [ ] `/etc/quiz-app.env` is mode `600`
- [ ] HTTPS enabled before sharing publicly
- [ ] SSH key only (disable password SSH if you customized sshd)
- [ ] Regular backups of `backend/data/`
- [ ] Lightsail firewall: only 22, 80, 443 open

---

## Quick reference

| Item | Location |
|------|----------|
| App root | `/home/ubuntu/quiz-app` |
| Backend | `/home/ubuntu/quiz-app/backend` |
| Frontend build | `/home/ubuntu/quiz-app/frontend/dist` |
| Data | `/home/ubuntu/quiz-app/backend/data/` |
| Env file | `/etc/quiz-app.env` |
| systemd service | `quiz-backend` |
| nginx config | `/etc/nginx/sites-available/quiz-app` |

**Useful commands:**

```bash
sudo systemctl restart quiz-backend
sudo systemctl reload nginx
sudo journalctl -u quiz-backend -f
```
