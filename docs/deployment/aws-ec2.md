# AWS EC2 Deployment

This document captures the minimum Ubuntu EC2 setup for hosting the
Autoreport user-facing web app behind `nginx`.

For a remote Codex handoff on an already-provisioned EC2 host, use
`docs/deployment/remote-codex-handover.md`.

## What This Repo Provides

- `deploy/aws-ec2/bootstrap.sh`: installs packages, creates the virtualenv,
  installs the project, writes `systemd`, and enables `nginx`
- `deploy/aws-ec2/autoreport.service`: template for the `systemd` unit
- `deploy/aws-ec2/nginx-autoreport.conf`: template for the `nginx` site

The default assumptions match the common first EC2 setup:

- app user: `ubuntu`
- app directory: the checked-out repo root, with the bootstrap default resolving
  under the app user's home directory
- app bind: `127.0.0.1:8000`
- public entrypoint: `nginx` on port `80`

## Ubuntu Package Setup

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx
```

## One-Step Bootstrap

From the repo root on the EC2 instance:

```bash
chmod +x deploy/aws-ec2/bootstrap.sh
./deploy/aws-ec2/bootstrap.sh
```

Optional overrides:

```bash
APP_DIR="$(pwd)" \
APP_WORKERS=2 \
SERVER_NAME=_ \
./deploy/aws-ec2/bootstrap.sh
```

Use a real domain in `SERVER_NAME` once DNS is attached to the instance.

## Manual Service Checks

```bash
sudo systemctl status autoreport
journalctl -u autoreport -n 100 --no-pager
curl http://127.0.0.1:8000/healthz
```

## Nginx Checks

```bash
sudo nginx -t
sudo systemctl status nginx
curl http://127.0.0.1/
```

## AWS Security Group

Allow these inbound rules:

- `22/tcp` from your admin IP only
- `80/tcp` from the public internet
- `443/tcp` from the public internet once TLS is enabled

Do not expose `8000/tcp` publicly. `uvicorn` stays bound to loopback and
`nginx` is the only public entrypoint.

## HTTPS

For a quick single-instance setup, add TLS after HTTP is working:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.example
```

For a more AWS-native setup, place an Application Load Balancer in front and
terminate TLS there with ACM.

## Notes

- This setup serves the user-facing app: `autoreport.web.app:app`
- The debug app is intentionally separate and should not be exposed publicly by
  default
- `pip install -e .` installs the `uvicorn` dependency declared in
  `pyproject.toml`, so you do not need `apt install uvicorn`
