# Repo Ops Finish Checklist

Use this reference when the task changes the shared operating surface of the
`autoreport` repository and should not stop at a local file edit.

## Files That Trigger This Skill

Typical trigger paths:

- `AGENTS.md`
- `codex/skills/**`
- `docs/deployment/remote-codex-handover.md`
- shared architecture or process docs that later Codex turns rely on

These are not ordinary product docs. They change how future work is routed,
validated, or published.

## Default Finish Rule

Unless the user explicitly asks to pause or keep the change local:

1. validate the changed operating surface
2. run `public-repo-safety`
3. commit the change on `main`
4. push `origin/main`
5. fast-forward `codex/next` from that pushed `main`
6. push `origin/codex/next`
7. return the local checkout to `main`

## Validation Order

1. Skill files changed:

```bash
python <path-to-skill-creator>/scripts/quick_validate.py <skill-folder>
```

Resolve `<path-to-skill-creator>` from the installed `$skill-creator` location
for the current machine instead of hard-coding a local absolute path into
tracked repo guidance.

2. Runtime claims changed:
Run the narrow matching tests from `AGENTS.md`.

3. Push safety:
Scan the staged or intended files with `public-repo-safety` criteria before
public push.

## Git Finish Loop

Prefer this order:

```bash
git status --short --branch
git add <intended-files>
git commit -m "<focused message>"
git push origin main
git checkout codex/next
git merge --ff-only main
git push origin codex/next
git checkout main
```

## Stop Conditions

Stop and realign instead of pretending the task is done when:

- unrelated tracked changes would be mixed into the repo-operation commit
- the working branch is not the intended shared base and the change has not been moved cleanly
- `public-repo-safety` finds a blocker
- `codex/next` cannot fast-forward from `main`

## Reporting Minimums

Always report:

- which shared operating-surface files changed
- what validation ran
- the pushed `main` SHA
- whether `codex/next` now matches that SHA
