# Public Deploy Checklist

Use this reference when `remote-deployment-handover` is active and the task is
about a remote host, a public deployment, or drift between `main` and the live
Autoreport server.

## Contract Anchors

Read these tracked sources before deciding what "correct" means:

- `autoreport/web/app.py`: current public homepage HTML and API behavior
- `autoreport/web/debug_app.py`: intentionally separate debug surface
- `tests/test_web_app.py`: homepage assertions and public-app image rejection
- `deploy/aws-ec2/autoreport.service`: tracked systemd entrypoint
- `Dockerfile`: tracked container entrypoint
- `docs/deployment/aws-ec2.md`: EC2 bootstrap assumptions
- `docs/deployment/remote-codex-handover.md`: operator-facing command flow

## Current Public Homepage Signals

The public app should currently:

- include `Edit the starter deck and generate an Autoreport PPTX.`
- include `Starter Deck YAML`
- include `debug app or CLI`
- exclude `Image Uploads`
- exclude `Remove Upload`

If the public URL still shows `Image Uploads`, the likely root causes are:

- the host checkout is behind `origin/main`
- the process or container was not restarted after update
- the host is exposing `autoreport.web.debug_app:app`
- the app is correct on loopback but stale content is being served by `nginx`,
  a reverse proxy, a load balancer, or a CDN

## Host Check Order

1. Confirm the checkout.

```bash
cd ~/autoreport
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git log --oneline -5
```

2. When the image-upload-removal boundary matters, confirm the fixing commit is present.

```bash
git merge-base --is-ancestor 235a415 HEAD && echo "public image-removal commit present"
```

3. Confirm the public app contract on loopback.

```bash
source .venv/bin/activate 2>/dev/null || true
python -m uvicorn autoreport.web.app:app --host 127.0.0.1 --port 8000
```

In another shell:

```bash
curl http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/ | grep -n "Starter Deck YAML"
curl -s http://127.0.0.1:8000/ | grep -n "debug app or CLI"
curl -s http://127.0.0.1:8000/ | grep -n "Image Uploads" && echo "unexpected upload UI present"
```

4. Confirm what the host is actually serving.

```bash
sudo systemctl status autoreport
sudo systemctl cat autoreport
ps -ef | grep uvicorn
docker ps
```

5. Confirm the public entrypoint through nginx.

```bash
curl -s http://127.0.0.1/ | grep -n "Starter Deck YAML"
curl -s http://127.0.0.1/ | grep -n "Image Uploads" && echo "unexpected upload UI present"
journalctl -u autoreport -n 100 --no-pager
```

## Refresh Commands

For editable-install EC2 deployments:

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
```

For container-based deployments:

```bash
cd ~/autoreport
git checkout main
git pull --ff-only origin main
docker build -t autoreport:latest .
docker ps
```

## Troubleshooting Branches

1. The host SHA is old.
Pull `origin/main`, reinstall, and restart.

2. The service is running `autoreport.web.debug_app:app`.
Switch it back to `autoreport.web.app:app` and restart.

3. Loopback looks right but the public domain still looks stale.
Inspect `nginx`, upstream routing, proxy layers, and caches before editing app code.

4. The service entrypoint is right but the HTML is still old.
Reinstall with `python -m pip install -e .` and restart the process that serves traffic.
