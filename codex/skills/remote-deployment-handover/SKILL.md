---
name: remote-deployment-handover
description: Operate and hand off the Autoreport public deployment on a remote host. Use when Codex needs to debug why the hosted server differs from `main`, verify that the public service is running `autoreport.web.app:app` instead of the debug app, refresh the EC2 systemd/nginx or container rollout, or prepare a remote handover for the public web server.
---

# Remote Deployment Handover

## Overview

Use this skill for remote-host deployment drift, EC2 handover, and public-web
server verification in the `autoreport` repository. It keeps the public app,
debug app, deployment assets, and current homepage contract aligned so Codex
can tell the difference between stale code, stale processes, and the wrong
entrypoint being exposed.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/public-deploy-checklist.md`.
- Read `../../../docs/deployment/aws-ec2.md`.
- Read `../../../docs/deployment/remote-codex-handover.md` when a human-readable
  operator note is needed.
- Read `../../../deploy/aws-ec2/autoreport.service`.
- Read `../../../Dockerfile` when container rollout is possible.
- Read `../../../tests/test_web_app.py`.
- Read `../../../autoreport/web/app.py`.
- Read `../../../autoreport/web/debug_app.py` when the host may be serving the
  wrong surface.
- If the task also changes this skill, `AGENTS.md`, or tracked deployment
  handover guidance as part of the shared operating surface, also read
  `../repo-ops-policy-sync/SKILL.md`.
- Read `../public-repo-safety/SKILL.md` before any public push, publish, or
  documentation handoff that promotes tracked deployment notes outside the
  private workspace.

## Workflow

1. Confirm the source of truth before touching the host.
- Use `autoreport/web/app.py` and `tests/test_web_app.py` as the public homepage
  contract.
- Use `deploy/aws-ec2/autoreport.service` and `Dockerfile` as the tracked
  public entrypoint references.
- Treat the debug app as intentionally different: it may still expose upload
  controls for developer workflows.

2. Identify the active deployment topology.
- Determine whether the remote host uses the tracked `systemd` plus `nginx`
  flow, a containerized flow, or an extra reverse-proxy or CDN layer.
- Prefer the tracked EC2 deployment assets when the host matches the repository
  assumptions.

3. Check drift in order.
- Verify branch and SHA on the host before blaming the service.
- When a regression boundary matters, verify the specific fixing commit is
  present on the host checkout.
- Inspect what is actually serving traffic with `systemctl cat autoreport`,
  `ps -ef | grep uvicorn`, and `docker ps` as needed.
- Check loopback responses before diagnosing the public domain.

4. Refresh the service with minimal ambiguity.
- For editable installs, reinstall with `python -m pip install -e .`, then
  reload and restart the tracked services.
- For container deployments, rebuild and replace the image instead of assuming a
  pull alone updated runtime state.
- Do not call the rollout fixed until the homepage checks pass locally through
  loopback and through the public entrypoint.

5. Separate public-app issues from debug-app behavior.
- If the public URL shows `Image Uploads`, treat that as a deployment or
  entrypoint problem, not as evidence that the code change failed.
- If the loopback public app is correct but the public domain is stale, inspect
  `nginx`, load balancers, proxies, or CDN caching before editing application
  code.

6. Finish with an operator handover.
- Record the checked SHA, deployment mode, active entrypoint, commands run, and
  remaining blockers.
- If the task updates repo-tracked deployment guidance, keep
  `docs/deployment/remote-codex-handover.md`, this skill, and the routing notes
  in sync.
- When the task changes the shared operating guidance itself, do not stop at
  the document edit; hand the finish loop over to `repo-ops-policy-sync`.

## Current Repo Defaults

- The tracked public service entrypoint is `autoreport.web.app:app`.
- The tracked debug service entrypoint is `autoreport.web.debug_app:app`.
- The public homepage is text-first and should not render `Image Uploads`.
- The debug app may still render `Image Uploads` for upload-backed developer
  flows.
- The tracked EC2 bootstrap flow lives under `deploy/aws-ec2/`.

## Output Contract

- State the deployment topology that was inspected.
- State the SHA or branch observed on the host.
- State which entrypoint was actually serving traffic.
- State which homepage checks passed or failed.
- List the exact restart or rebuild commands run.
- Call out any blocker that still prevents the public server from matching the
  current repo contract.
