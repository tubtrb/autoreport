# Remote Codex Handover

This note is for a Codex session running directly on the Ubuntu EC2 host that
will operate the public Autoreport web server.

## Current Repository State

- branch to use: `main`
- release backup tag: `v0.3.0`
- current public app entrypoint: `autoreport.web.app:app`
- current debug app entrypoint: `autoreport.web.debug_app:app`

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

## Immediate Remote Tasks

1. Confirm the repository is on `main` and up to date.

```bash
cd ~/autoreport
git checkout main
git pull --ff-only origin main
git describe --tags --always
```

2. Confirm Python app health before changing the web stack.

```bash
source .venv/bin/activate 2>/dev/null || true
python -m uvicorn autoreport.web.app:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/healthz
```

3. Bootstrap the service stack from the tracked deployment assets.

```bash
cd ~/autoreport
chmod +x deploy/aws-ec2/bootstrap.sh
./deploy/aws-ec2/bootstrap.sh
```

4. Validate the running service.

```bash
sudo systemctl status autoreport
sudo systemctl status nginx
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1/
journalctl -u autoreport -n 100 --no-pager
```

5. If Node.js tooling or Codex CLI is needed on the host, prefer `nvm`.

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

## Completion Signal

The remote Codex task is complete when:

- `systemctl status autoreport` is healthy
- `systemctl status nginx` is healthy
- `curl http://127.0.0.1:8000/healthz` returns `{"status":"ok"}`
- `curl http://127.0.0.1/` returns the Autoreport homepage through `nginx`
- no machine-specific secrets were written into the public repository
