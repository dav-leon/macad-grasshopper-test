# Deploy to AWS EC2

This guide deploys the quiz app (Flask API + Vue SPA + JSON files) on **one EC2 Ubuntu server** with **nginx** and **gunicorn**. It matches how the app runs locally, but in production mode.

EC2 gives you more control than Lightsail. This guide uses the **simplest path**: one instance, no load balancer, no Docker.

---

## Overview

| Layer | What runs |
|-------|-----------|
| Public URL | `https://your-domain.com` (or `http://YOUR_PUBLIC_IP`) |
| Web server | nginx (port 80/443) |
| Static files | `frontend/dist/` (Vue build) |
| API | gunicorn → Flask on `127.0.0.1:5000` |
| Data | `backend/data/users.json`, `questions.json` |
| Secret | `JWT_SECRET` environment variable |

---

## Part 1 — Prerequisites (on your Windows machine)

### 1.1 AWS account

- Sign up at [https://aws.amazon.com](https://aws.amazon.com) if you don't have an account.
- Have a credit card ready. A **t2.micro** or **t3.micro** instance is often free-tier eligible (~$0–10/month depending on region and usage).

### 1.2 Your code in Git (recommended)

Push the project to GitHub, GitLab, or Bitbucket. Example:

```bash
cd "C:\Users\david\dev\IAAC\GH-test\macad-grasshopper-test"
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USER/macad-grasshopper-test.git
git push -u origin main
```

If you don't use Git, you can upload files with **SCP** or **SFTP** instead (covered in step 5.2).

### 1.3 Optional: a domain name

- You can use the EC2 public IP initially (`http://YOUR_IP`).
- For HTTPS with a custom domain, buy one (Route 53, Namecheap, etc.) and point DNS at your EC2 IP later.

### 1.4 Generate a JWT secret

On your PC, run in PowerShell:

```powershell
[Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
```

Save the output — you'll use it as `JWT_SECRET`.

---

## Part 2 — Create the EC2 instance

### 2.1 Open EC2 console

1. Go to [https://console.aws.amazon.com/ec2](https://console.aws.amazon.com/ec2)
2. Sign in to AWS
3. Pick a **Region** close to your users (top-right, e.g. `eu-west-1`)
4. Click **Launch instance**

### 2.2 Instance settings

| Setting | Value |
|---------|--------|
| Name | `quiz-app` |
| Application and OS Images | **Ubuntu** → **Ubuntu Server 22.04 LTS (HVM), SSD Volume Type** |
| Architecture | **64-bit (x86)** |
| Instance type | **t2.micro** or **t3.micro** (free tier) — use **t3.small** if builds feel slow |
| Key pair | **Create new key pair** → name it `quiz-app-key` → type **RSA** → format **.pem** → **Create** (downloads the file — keep it safe) |
| Network settings | Click **Edit** (see 2.3 below) |
| Configure storage | **8–20 GB** gp3 is fine |
| Advanced details | Leave defaults |

### 2.3 Security group (firewall)

Under **Network settings**, create or select a security group with these **inbound rules**:

| Type | Port | Source | Purpose |
|------|------|--------|---------|
| SSH | 22 | **My IP** (recommended) or `0.0.0.0/0` | SSH access |
| HTTP | 80 | `0.0.0.0/0` | Web traffic |
| HTTPS | 443 | `0.0.0.0/0` | HTTPS (later) |

Restricting SSH to **My IP** is safer than opening port 22 to the world.

### 2.4 Launch

1. Review summary → **Launch instance**
2. Wait until **Instance state** is **Running**

### 2.5 Note the public IP

1. EC2 → **Instances** → click your instance
2. Copy **Public IPv4 address** (e.g. `54.78.xx.xx`)

This IP changes if you stop/start the instance. For a stable IP, see **Part 2.6** (optional but recommended).

### 2.6 Optional: Elastic IP (stable public IP)

1. EC2 → **Elastic IPs** → **Allocate Elastic IP address** → **Allocate**
2. Select the new IP → **Actions** → **Associate Elastic IP address**
3. Choose your instance → **Associate**

Use this Elastic IP everywhere instead of the temporary public IP.

---

## Part 3 — Connect to the server

### 3.1 Fix key permissions (Windows, one-time)

PowerShell may require restrictive permissions on the `.pem` file:

```powershell
icacls "C:\path\to\quiz-app-key.pem" /inheritance:r
icacls "C:\path\to\quiz-app-key.pem" /grant:r "$($env:USERNAME):(R)"
```

### 3.2 SSH from Windows PowerShell

```powershell
ssh -i "C:\path\to\quiz-app-key.pem" ubuntu@YOUR_PUBLIC_IP
```

Default user is **`ubuntu`**.

Type `yes` if asked to trust the host fingerprint.

### 3.3 Or use EC2 Instance Connect (browser)

1. EC2 → **Instances** → select instance → **Connect**
2. Tab **EC2 Instance Connect** → **Connect**

No key file needed, but PowerShell + `.pem` is easier for file uploads later.

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

Verify nginx installed (needed before Part 9):

```bash
nginx -v
ls /etc/nginx/sites-available/
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
git clone https://github.com/YOUR_USER/macad-grasshopper-test.git
cd macad-grasshopper-test
```

Your layout should look like:

```
~/macad-grasshopper-test/
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
scp -i "C:\path\to\quiz-app-key.pem" -r "C:\Users\david\dev\IAAC\GH-test\macad-grasshopper-test" ubuntu@YOUR_PUBLIC_IP:~/macad-grasshopper-test
```

Then on the server:

```bash
cd ~/macad-grasshopper-test
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
cd ~/macad-grasshopper-test/backend
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

Only `root` can read this file now. That is intentional — the systemd service in Part 8 loads it as root via `EnvironmentFile=`. For manual testing below, use `sudo cat` to read it into your shell.

### 6.4 Test gunicorn manually

```bash
cd ~/macad-grasshopper-test/backend
source venv/bin/activate
set -a && source <(sudo cat /etc/quiz-app.env) && set +a
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
cd ~/macad-grasshopper-test/frontend
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
Description=MACAD GH-Quiz Flask Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/macad-grasshopper-test/backend
EnvironmentFile=/etc/quiz-app.env
ExecStart=/home/ubuntu/macad-grasshopper-test/backend/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app
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

Requires nginx from **Part 4.1**. If `sites-available` does not exist, install nginx first:

```bash
sudo apt install -y nginx
ls /etc/nginx/sites-available/
```

### 9.1 Create site config

```bash
sudo nano /etc/nginx/sites-available/quiz-app
```

Paste:

```nginx
server {
    listen 80;
    server_name _;   # replace with yourdomain.com after DNS is set

    root /home/ubuntu/macad-grasshopper-test/frontend/dist;
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

### 9.2b Let nginx read the frontend files

nginx runs as `www-data`, but `/home/ubuntu` is mode `750` and blocks it — causing a **500** with `stat() ... failed (13: Permission denied)` in the error log. Grant traverse access along the path:

```bash
chmod o+x /home/ubuntu
chmod o+x /home/ubuntu/macad-grasshopper-test
chmod o+x /home/ubuntu/macad-grasshopper-test/frontend
sudo chmod -R o+rX /home/ubuntu/macad-grasshopper-test/frontend/dist
sudo systemctl reload nginx
```

Verify nginx can read the files:

```bash
sudo -u www-data stat /home/ubuntu/macad-grasshopper-test/frontend/dist/index.html
```

### 9.3 Test in browser

Open:

```
http://YOUR_PUBLIC_IP
```

You should see the login page. Register a user — the **first registered user becomes admin** per your app logic.

---

## Part 10 — HTTPS (recommended)

Once your domain's **A record** points to your EC2 Elastic IP (or public IP):

### Certbot on the instance (easiest on EC2)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Certbot updates nginx for HTTPS and sets up auto-renewal.

Update nginx `server_name` if needed:

```nginx
server_name yourdomain.com;
```

Then:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

**Note:** Your EC2 security group must allow inbound **443** (covered in Part 2.3).

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

## Part 12 — Modifying quiz questions

Questions are stored in `backend/data/questions.json` on the server. You can edit them in the browser (recommended) or directly on the server.

### 12.1 Admin panel (recommended)

1. Open your site: `http://YOUR_PUBLIC_IP/admin` (or `https://yourdomain.com/admin` after HTTPS).
2. Log in as an **admin** user. The **first registered account** is admin automatically; later users are not unless you change `users.json` manually.
3. Use the admin panel:

| Action | How |
|--------|-----|
| **Add** | Click **+ Add Question**, fill the form, save |
| **Edit** | Click **Edit** on a row |
| **Delete** | Click **Delete**, then **Confirm?** |
| **Change time limit** | Click the time value in the table (e.g. `30s`), type a new value, press Enter |

Each question needs:

- **Question text** — the prompt shown to students
- **Four options** — exactly four choices (A–D)
- **Correct answer** — radio button A, B, C, or D (stored as index `0`–`3`)
- **Time limit** — seconds per question (5–300)
- **Image** (optional) — upload a file (max 2 MB) or paste an image URL

Changes save immediately to `questions.json`. **No restart** of gunicorn or nginx is required — refresh `/quiz` to see updated questions.

### 12.2 Question file format

On the server, the file is:

```
/home/ubuntu/macad-grasshopper-test/backend/data/questions.json
```

Example entry:

```json
{
  "id": 1,
  "question": "What is 3 + 3?",
  "options": ["5", "6", "7", "8"],
  "answer": 1,
  "time_limit": 25
}
```

| Field | Meaning |
|-------|---------|
| `id` | Unique integer; must not be duplicated |
| `question` | Question text |
| `options` | Array of **exactly 4** strings |
| `answer` | Index of the correct option: `0` = A, `1` = B, `2` = C, `3` = D |
| `time_limit` | Seconds allowed for this question |
| `image` | Optional — URL or base64 data URL (added via admin upload) |

### 12.3 Edit on the server (bulk or offline)

Use this when replacing many questions at once or when you prefer a text editor over the UI.

**1. Back up first** (see Part 14):

```bash
cp ~/macad-grasshopper-test/backend/data/questions.json \
   ~/macad-grasshopper-test/backend/data/questions.json.bak
```

**2. Edit the file:**

```bash
nano ~/macad-grasshopper-test/backend/data/questions.json
```

Keep valid JSON (commas between objects, double quotes). Validate before saving:

```bash
python3 -m json.tool ~/macad-grasshopper-test/backend/data/questions.json > /dev/null && echo OK
```

If validation fails, restore the backup:

```bash
cp ~/macad-grasshopper-test/backend/data/questions.json.bak \
   ~/macad-grasshopper-test/backend/data/questions.json
```

**3. Fix ownership** if you edited with `sudo`:

```bash
sudo chown ubuntu:ubuntu ~/macad-grasshopper-test/backend/data/questions.json
```

The running app picks up changes on the next request — no service restart needed.

### 12.4 Edit locally and upload

On your Windows PC, edit `backend/data/questions.json` in the repo, then copy to the server:

```powershell
scp -i "C:\path\to\quiz-app-key.pem" backend\data\questions.json ubuntu@YOUR_PUBLIC_IP:~/macad-grasshopper-test/backend/data/questions.json
```

Fix the path if your repo layout differs. After upload, confirm the file on the server:

```bash
python3 -m json.tool ~/macad-grasshopper-test/backend/data/questions.json > /dev/null && echo OK
```

### 12.5 Seed questions from the Git repo

If you redeployed code and want the repo's default questions back (this **overwrites** live questions):

```bash
cd ~/macad-grasshopper-test
cp backend/data/questions.json backend/data/questions.json.bak
git checkout -- backend/data/questions.json
```

Or copy from a fresh clone on your PC and upload with `scp` (Part 12.4).

### 12.6 Tips

- **Backup before bulk edits** — see Part 14.
- **Don't edit `questions.json` while the quiz is running** for a large class; prefer the admin UI for live tweaks.
- **New question IDs** — the admin UI assigns the next free ID. If editing JSON by hand, use unique integers (e.g. max existing id + 1).
- **Images in JSON** — uploaded images are stored as base64 strings and can make the file large; prefer image URLs for many questions.

---

## Part 13 — Deploying updates later

When you change code:

```bash
cd ~/macad-grasshopper-test
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

### 13.1 One-command redeploy (recommended)

The repo ships with `redeploy.sh` at the project root. It runs the whole cycle above — `git pull`, backend deps + service restart, frontend build, dist permissions, and nginx reload — in one go. It never touches `backend/data/*.json`.

**One-time setup** on the server:

```bash
# Make the script executable
chmod +x ~/macad-grasshopper-test/redeploy.sh

# Install it as a global command called "redeploy"
sudo ln -sf ~/macad-grasshopper-test/redeploy.sh /usr/local/bin/redeploy
```

**Allow the restart/reload steps to run without a password prompt** (the script calls `sudo systemctl` and `sudo nginx`). Create a sudoers rule for the `ubuntu` user:

```bash
echo 'ubuntu ALL=(root) NOPASSWD: /bin/systemctl restart quiz-backend, /bin/systemctl status quiz-backend, /bin/systemctl reload nginx, /usr/sbin/nginx -t, /bin/chmod -R o+rX /home/ubuntu/macad-grasshopper-test/frontend/dist' | sudo tee /etc/sudoers.d/quiz-redeploy
sudo chmod 440 /etc/sudoers.d/quiz-redeploy
sudo visudo -c   # validate — must say "parsed OK"
```

> If you skip the sudoers rule, `redeploy` still works but will prompt for your password at the systemctl/nginx steps.

**From then on**, redeploy any time with a single command:

```bash
redeploy
```

You'll see coloured `==>` progress lines and, at the end, `Done. App redeployed.`

---

## Part 14 — Backups (important)

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
scp -i "C:\path\to\quiz-app-key.pem" ubuntu@YOUR_PUBLIC_IP:~/macad-grasshopper-test/backend/data/users.json .
```

Consider weekly backups or EC2 **snapshots** (EC2 → **Elastic Block Store** → **Snapshots**) of the root volume.

---

## Part 15 — Troubleshooting

### Can't SSH in

- Confirm security group allows **SSH (22)** from your IP
- Confirm you're using user **`ubuntu`** and the correct `.pem` key
- Confirm instance state is **Running**

### Blank page or 502 on `/api`

```bash
sudo systemctl status quiz-backend
sudo journalctl -u quiz-backend -f
curl http://127.0.0.1:5000/api/quiz
```

### 500 error, `stat() ... (13: Permission denied)` in nginx log

nginx (`www-data`) can't traverse `/home/ubuntu` (mode `750`). Grant path access — see **Part 9.2b**:

```bash
chmod o+x /home/ubuntu /home/ubuntu/macad-grasshopper-test /home/ubuntu/macad-grasshopper-test/frontend
sudo chmod -R o+rX /home/ubuntu/macad-grasshopper-test/frontend/dist
sudo systemctl reload nginx
```

A `rewrite or internal redirection cycle ... /index.html` error usually accompanies this — it clears once the permission issue is fixed.

### 404 on `/quiz` or `/admin` after refresh

nginx must have `try_files $uri $uri/ /index.html;` in the `/` location.

### Login works but admin doesn't

Only the **first registered user** is admin. Check `users.json` on the server.

### "Invalid token" after deploy

`JWT_SECRET` changed → all users must log in again. Keep the same secret across redeploys.

### Permission errors on JSON files

```bash
ls -la ~/macad-grasshopper-test/backend/data/
# ubuntu user must own and write these files
sudo chown -R ubuntu:ubuntu ~/macad-grasshopper-test/backend/data
```

### `Permission denied` when sourcing `/etc/quiz-app.env`

After `chmod 600`, only `root` can read the file. For manual gunicorn testing, use:

```bash
set -a && source <(sudo cat /etc/quiz-app.env) && set +a
```

The systemd service (Part 8) reads the file as root — no workaround needed there.

### `Directory '/etc/nginx/sites-available' does not exist`

nginx is not installed. Run Part 4.1:

```bash
sudo apt install -y nginx
```

### nginx error

```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### Public IP changed after stop/start

Associate an **Elastic IP** (Part 2.6) and update your DNS A record.

---

## Part 16 — Security checklist

- [ ] `JWT_SECRET` is a long random value, not `change-me-in-production`
- [ ] `/etc/quiz-app.env` is mode `600`
- [ ] HTTPS enabled before sharing publicly
- [ ] SSH restricted to your IP in the security group (not `0.0.0.0/0` on port 22)
- [ ] Regular backups of `backend/data/`
- [ ] Security group: only 22 (your IP), 80, 443 open to the internet

---

## Quick reference

| Item | Location |
|------|----------|
| App root | `/home/ubuntu/macad-grasshopper-test` |
| Backend | `/home/ubuntu/macad-grasshopper-test/backend` |
| Frontend build | `/home/ubuntu/macad-grasshopper-test/frontend/dist` |
| Data | `/home/ubuntu/macad-grasshopper-test/backend/data/` |
| Questions file | `/home/ubuntu/macad-grasshopper-test/backend/data/questions.json` |
| Admin panel | `http://YOUR_PUBLIC_IP/admin` (Part 12) |
| Env file | `/etc/quiz-app.env` |
| systemd service | `quiz-backend` |
| nginx config | `/etc/nginx/sites-available/quiz-app` |
| SSH key | `quiz-app-key.pem` on your PC |
| Firewall | EC2 **Security group** inbound rules |

**Useful commands:**

```bash
sudo systemctl restart quiz-backend
sudo systemctl reload nginx
sudo journalctl -u quiz-backend -f
```

**AWS console shortcuts:**

- Instances: [EC2 → Instances](https://console.aws.amazon.com/ec2/home#Instances:)
- Security groups: [EC2 → Security Groups](https://console.aws.amazon.com/ec2/home#SecurityGroups:)
- Elastic IPs: [EC2 → Elastic IPs](https://console.aws.amazon.com/ec2/home#Addresses:)
