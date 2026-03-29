# PresentationGo Reference Analysis

## Summary

- Source snapshot: `template-library/2026-03-28/presentationgo`
- Structure reference: `modern-business-16x9.potx`
- Palette reference: `datawave-insights-16x9.potx`
- Accent reference: `modern-navy-horizon-16x9.potx`
- Baseline control: `finance-business-16x9.potx`

## Reference Notes

- `datawave-insights-16x9.potx`
  tone: `calm data-reporting`
  layouts: `8`
  reuse bias: `palette + title rhythm`
  key theme colors: `dk1=000000, lt1=FFFFFF, dk2=0E2841, lt2=E8E8E8, accent1=156082, accent2=E97132`
  why it matters: Strong fit for Autoreport editorial tonality because the palette is restrained and the closing layout already mixes picture and body zones.
- `finance-business-16x9.potx`
  tone: `safe corporate baseline`
  layouts: `9`
  reuse bias: `baseline comparison only`
  key theme colors: `dk1=000000, lt1=FFFFFF, dk2=44546A, lt2=E7E6E6, accent1=4472C4, accent2=ED7D31`
  why it matters: Useful as a control because it stays close to stock Office structure.
- `modern-business-16x9.potx`
  tone: `broad layout library`
  layouts: `14`
  reuse bias: `mixed-layout patterns`
  key theme colors: `dk1=000000, lt1=FFFFFF, dk2=44546A, lt2=E7E6E6, accent1=4472C4, accent2=ED7D31`
  why it matters: Best source for structural ideas because it carries both `Content with Caption` and `Picture with Caption` plus multiple title/content variants.
- `modern-navy-horizon-16x9.potx`
  tone: `high-contrast editorial`
  layouts: `8`
  reuse bias: `accent system + edge decoration`
  key theme colors: `dk1=000000, lt1=FFFFFF, dk2=001F33, lt2=F2F2F2, accent1=F15F47, accent2=FBA91E`
  why it matters: Good source for stronger color blocking, but many layouts carry a decorative picture placeholder that could confuse template profiling.

## Translation Rules

### Keep

- 16:9 aspect ratio
- editorial title hierarchy
- calm navy + teal + coral palette
- decorative energy pushed to edges instead of behind the main text block

### Avoid

- layout-wide decorative picture placeholders on text-first slides
- dense multi-placeholder bodies before the runtime profiler boundary is patched
- theme defaults that collapse back to plain stock Office styling
