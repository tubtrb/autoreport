# Remote Release Handoff for v0.4.1

This note is for a Codex session or operator working directly on the Ubuntu
Lightsail host for the `v0.4.1` release cycle.

Use this file when the goal is to validate the current release candidate on the
remote host or to roll the public service forward after `main` has been updated.

## Current Release State

As of `2026-04-05`:

- release candidate branch: `origin/codex/v0.4-master`
- release candidate SHA: `c20427a`
- current `origin/main` SHA: `c2c107c`
- current public app entrypoint: `autoreport.web.app:app`
- current debug app entrypoint: `autoreport.web.debug_app:app`
- public host: `3.36.96.47`
- default remote user: `ubuntu`

The public server should continue to follow `main`.
Do not replace the public service with `codex/v0.4-master` directly unless that
branch has already been promoted and the user explicitly wants the candidate
served publicly.

## Two Safe Modes

Choose one mode before touching the service.

### Mode A: candidate validation only

Use this before promotion to `main`.
This mode must not replace the live public service.

- create a separate checkout or worktree for `codex/v0.4-master`
- run the candidate on a loopback-only alternate port
- verify the manual homepage contract there
- leave the `nginx` plus `systemd` public service on `main`

### Mode B: public rollout

Use this only after `main` contains the approved `v0.4.1` release commit.

- update `/home/ubuntu/autoreport` to the latest `origin/main`
- reinstall the editable package
- restart the tracked `autoreport` systemd service
- reload `nginx`
- verify the homepage and `healthz` through loopback and the public entrypoint

## Expected Homepage Signals for v0.4.1

The public app should show the screenshot-first manual flow.

Expected signals:

- `Manual Procedure Starter`
- `Refresh Slide Assets`
- `Generate PPTX`
- `PowerPoint Slide Preview`
- `Generation complete. Your Autoreport deck download should begin shortly.`

If those manual-flow signals are missing from the loopback app or the public
domain, treat that as deployment drift or the wrong entrypoint being served.

## Mode A: Candidate Validation Steps

Run these commands on the Lightsail host without touching the live service:

```bash
cd /home/ubuntu
rm -rf autoreport-v0.4.1-rc
git clone /home/ubuntu/autoreport autoreport-v0.4.1-rc
cd autoreport-v0.4.1-rc
git fetch origin
git checkout codex/v0.4-master
git reset --hard origin/codex/v0.4-master
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[e2e]
python -m uvicorn autoreport.web.app:app --host 127.0.0.1 --port 8011
```

In a second shell:

```bash
curl http://127.0.0.1:8011/healthz
curl -s http://127.0.0.1:8011/ | grep -n "Manual Procedure Starter"
curl -s http://127.0.0.1:8011/ | grep -n "Refresh Slide Assets"
curl -s http://127.0.0.1:8011/ | grep -n "PowerPoint Slide Preview"
```

If local browser tooling is available on the host and you want the same evidence
shape as the repo-local release prep:

```bash
source .venv/bin/activate
python tests/e2e/run_public_web_playwright.py --version 0.4.1 --route http://127.0.0.1:8011/
```

Stop the temporary `uvicorn` process after the checks finish.

## Mode B: Public Rollout Steps

Run these commands only after `main` has been updated to the approved release
commit:

```bash
cd /home/ubuntu/autoreport
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse --short HEAD
git log --oneline -5
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
sudo systemctl daemon-reload
sudo systemctl restart autoreport
sudo systemctl reload nginx
```

Then verify the deployed service:

```bash
sudo systemctl status autoreport --no-pager
sudo systemctl status nginx --no-pager
curl http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/ | grep -n "Manual Procedure Starter"
curl -s http://127.0.0.1:8000/ | grep -n "Refresh Slide Assets"
curl -s http://127.0.0.1:8000/ | grep -n "PowerPoint Slide Preview"
curl -s http://127.0.0.1/ | grep -n "Manual Procedure Starter"
journalctl -u autoreport -n 100 --no-pager
```

## Rollout Stop Rules

Stop and report the issue instead of guessing when:

- `origin/main` still does not contain the approved `v0.4.1` release commit
- the service is serving `autoreport.web.debug_app:app`
- `curl http://127.0.0.1:8000/healthz` fails
- loopback looks correct but the public URL still serves stale HTML
- `nginx` or `systemd` restart fails

## Completion Signal

The remote `v0.4.1` rollout is complete when:

- the host checkout is on the intended branch and SHA
- `autoreport` and `nginx` are healthy
- `curl http://127.0.0.1:8000/healthz` returns `{"status":"ok"}`
- the homepage shows the manual-flow signals listed above
- no machine-specific secrets or key paths were written back into the repository
