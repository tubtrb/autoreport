# Remote Codex Handover

This note is for a Codex session running directly on the Ubuntu EC2 host that
will operate the public Autoreport web server.

For repo-local Codex execution guidance in this repository, use the companion
skill at `codex/skills/remote-deployment-handover/SKILL.md`.

## Current Repository State

- branch to use: `main`
- release backup tag: `v0.3.0`
- current public app entrypoint: `autoreport.web.app:app`
- current debug app entrypoint: `autoreport.web.debug_app:app`
- as of March 29, 2026, `main` already includes `235a415` (`web: hide image flow on public demo`)

The repository already includes reusable deployment assets:

- `deploy/aws-ec2/bootstrap.sh`
- `deploy/aws-ec2/autoreport.service`
- `deploy/aws-ec2/nginx-autoreport.conf`
- `docs/deployment/aws-ec2.md`

## Operating Rules

- Serve only the user-facing app publicly.
- Keep `uvicorn` bound to `127.0.0.1:8000`.
- Put `nginx` in front as the public HTTP entrypoint.
- Do not expose the debug app publicly by default.
- Do not commit machine-specific values such as real domains, IPs, private keys,
  or `.env` secrets back into the public repository.

## Expected Public Homepage

The public app now starts from the text-first starter editor and should not show
image-upload controls.

Expected homepage signals:

- the page includes `Edit the starter deck and generate an Autoreport PPTX.`
- the page includes `Starter Deck YAML`
- the page includes `debug app or CLI`
- the page does not include `Image Uploads`
- the page does not include `Remove Upload`

If `Image Uploads` still appears on the public URL, treat that as a deployment
drift issue rather than a product ambiguity. The most likely causes are:

- the EC2 checkout is not actually on the latest `main`
- the service was not restarted after pull or reinstall
- the server is exposing `autoreport.web.debug_app:app` instead of `autoreport.web.app:app`
- an older container or process is still serving traffic behind `nginx`

## Immediate Remote Tasks

1. Confirm the repository is on `main` and up to date.

```bash
cd ~/autoreport
git checkout main
git pull --ff-only origin main
git describe --tags --always
git log --oneline -5
```

2. Confirm the checkout includes the public image-removal change.

```bash
cd ~/autoreport
git rev-parse HEAD
git merge-base --is-ancestor 235a415 HEAD && echo "public image-removal commit present"
```

3. Confirm the app health and homepage shape before changing the web stack.

```bash
cd ~/autoreport
source .venv/bin/activate 2>/dev/null || true
python -m uvicorn autoreport.web.app:app --host 127.0.0.1 --port 8000
```

In another shell:

```bash
curl http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/ | grep -n "Edit the starter deck and generate an Autoreport PPTX."
curl -s http://127.0.0.1:8000/ | grep -n "Starter Deck YAML"
curl -s http://127.0.0.1:8000/ | grep -n "debug app or CLI"
curl -s http://127.0.0.1:8000/ | grep -n "Image Uploads" && echo "unexpected upload UI present"
```

4. Bootstrap or refresh the service stack from the tracked deployment assets.

```bash
cd ~/autoreport
chmod +x deploy/aws-ec2/bootstrap.sh
./deploy/aws-ec2/bootstrap.sh
```

5. Validate the running service and confirm it serves the public app.

```bash
sudo systemctl status autoreport
sudo systemctl status nginx
sudo systemctl cat autoreport
ps -ef | grep uvicorn
curl http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1/ | grep -n "Starter Deck YAML"
curl -s http://127.0.0.1/ | grep -n "debug app or CLI"
curl -s http://127.0.0.1/ | grep -n "Image Uploads" && echo "unexpected upload UI present"
journalctl -u autoreport -n 100 --no-pager
```

6. If the repo is correct but the public URL still shows upload controls, force a clean service refresh.

```bash
cd ~/autoreport
git checkout main
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
sudo systemctl daemon-reload
sudo systemctl restart autoreport
sudo systemctl reload nginx
curl -s http://127.0.0.1/ | grep -n "Image Uploads" && echo "unexpected upload UI present"
```

7. If the host is container-based instead of `systemd`, rebuild and replace the running image.

The tracked `Dockerfile` also serves `autoreport.web.app:app`, so a stale image
can produce the same symptom as a stale systemd process.

```bash
cd ~/autoreport
git checkout main
git pull --ff-only origin main
docker build -t autoreport:latest .
docker ps
```

8. If Node.js tooling or Codex CLI is needed on the host, prefer `nvm`.

```bash
sudo apt update
sudo apt install -y curl ca-certificates git build-essential
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && . "$NVM_DIR/bash_completion"
nvm install --lts
nvm alias default 'lts/*'
npm install -g @openai/codex
codex --help
```

## AWS-Side Checks

- security group should allow `22/tcp`, `80/tcp`, and later `443/tcp`
- security group should not expose `8000/tcp`
- if a domain is attached, enable TLS after HTTP is confirmed healthy

## Troubleshooting Branches

If the public URL still shows the upload section, use this decision tree:

1. `git rev-parse HEAD` is older than expected
   Pull `origin/main` and reinstall the app.

2. `systemctl cat autoreport` or `ps -ef | grep uvicorn` shows `autoreport.web.debug_app:app`
   Fix the service so it runs `autoreport.web.app:app`, then restart.

3. `curl http://127.0.0.1:8000/` looks correct but the public domain still looks old
   Check `nginx` upstreams, reverse proxies, load balancers, and any CDN or cache layer.

4. The repo and service are correct but the process still serves old HTML
   Reinstall with `python -m pip install -e .` and restart `autoreport`.

## Completion Signal

The remote Codex task is complete when:

- `systemctl status autoreport` is healthy
- `systemctl status nginx` is healthy
- `curl http://127.0.0.1:8000/healthz` returns `{"status":"ok"}`
- `curl http://127.0.0.1/` returns the Autoreport homepage through `nginx`
- the homepage includes `Starter Deck YAML`
- the homepage does not include `Image Uploads`
- no machine-specific secrets were written into the public repository
