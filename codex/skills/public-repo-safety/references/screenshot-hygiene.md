# Screenshot Hygiene

## Why screenshots are risky

OS-level captures often include more than the intended product surface:

- personal account names
- local folder trees
- chat or coding tools
- browser tabs unrelated to the product
- download folders or desktop clutter

These are easy to miss in text-only scans.

## Safe default

For public docs, prefer browser-native captures of the product surface, such as
Playwright full-page screenshots of the actual demo, over active-window desktop
captures.

## Review questions

- Does the image show only the product?
- Does it reveal a personal account, machine name, or local folder?
- Does it show internal tools, chat threads, or planning notes?
- Is the image currently ignored, or is it being promoted into a tracked docs path?

## Escalation

If a screenshot is repo-bound and contains unrelated or personal content, treat
it as a blocker rather than a low-priority cleanup item.
