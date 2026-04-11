## Autoreport v0.4.1 Release Notes

Version: `v0.4.1`
Release date: `2026-04-05`
Status: `draft`

Autoreport `v0.4.1` refines the public hosted-demo flow around the manual procedure starter. This release keeps the visible browser path narrow and predictable: review the starter, refresh the slide assets, upload the matching screenshots, and download the generated PowerPoint.

## Live service

As of `2026-04-05`, the public site and hosted demo are available at:

- Home: `http://auto-report.org/`
- Guide: `http://auto-report.org/guide/`
- Updates: `http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/`
- Hosted demo: `http://3.36.96.47/`

## What's included in this release

- The hosted demo opens directly with the built-in `Manual Procedure Starter`
- `Refresh Slide Assets` builds screenshot upload rows beside the matching slide previews
- `Generate PPTX` returns `autoreport_demo.pptx` as the browser download
- The success state tells the user that the deck download should begin shortly

## Browser check

- The hosted demo flow and the `autoreport_demo.pptx` download were checked in the browser on `2026-04-05`

## Current limitations

- The public hosted demo is focused on the built-in manual procedure flow
- Users need to prepare screenshots that match the required upload rows in the starter
- A public custom-template upload path is not part of this release
