# User Guide

Version: `v0.4.1`
Release date: `2026-04-05`
Status: `draft`

This guide is for the hosted Autoreport demo. It covers the public browser flow: open the built-in manual starter, refresh the slide assets, upload the matching screenshots, generate the deck, and confirm the downloaded PowerPoint result.

For version-specific changes, see the release notes.

## Live service

As of `2026-04-05`, the public site and hosted demo are available at:

- Home: `http://auto-report.org/`
- Guide: `http://auto-report.org/guide/`
- Updates: `http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/`
- Hosted demo: `http://3.36.96.47/`

## Hosted demo flow

1. Open the hosted demo. The page starts with `Manual Procedure Starter` and the built-in manual example.
2. Select `Refresh Slide Assets`. The page creates upload rows beside the matching PowerPoint slide previews.
3. Upload one screenshot for each required image slot. Keep each screenshot aligned with the preview row it belongs to.
4. Review the preview rows and select `Generate PPTX`.
5. Wait for the success state: `Generation complete. Your Autoreport deck download should begin shortly.`

### 1. Starter deck

The public page opens directly with the built-in manual starter so the user can begin from a fixed, visible procedure flow.

![Manual starter loaded](guide-image-v0.4.1/01-manual-starter-loaded.png)

### 2. Screenshot upload and preview alignment

After `Refresh Slide Assets`, the hosted demo shows the upload rows beside the matching slide previews. This is the public upload step for the manual flow.

![Slide assets refreshed](guide-image-v0.4.1/02-refresh-slide-assets-complete.png)

Upload each screenshot into the row that belongs to the visible preview and keep the order unchanged.

![Upload row filled](guide-image-v0.4.1/03-upload-row-filled.png)

### 3. Generate and download

When the required screenshots are in place, select `Generate PPTX` and wait for the browser download.

![Generation success](guide-image-v0.4.1/05-generate-success.png)

## Expected result

- The browser download starts as `autoreport_demo.pptx`
- The downloaded deck follows the manual procedure slide order from the hosted starter
- Uploaded screenshots stay aligned with the matching image slots from the public flow

## Browser check

The hosted demo flow and the `autoreport_demo.pptx` download were checked in the browser on `2026-04-05`.
