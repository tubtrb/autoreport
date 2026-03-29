# v0.4 Editorial Template Translation

## Intent

This branch-local template is not meant to imitate the local PresentationGo
references slide-for-slide.
It translates only the parts that help `autoreport` right now:

- stronger editorial hierarchy
- a calmer report palette
- decorative shapes pushed to the edges
- one safe primary body placeholder that the current contract-first editorial
  engine can fill

## Reference Inputs

- `modern-business-16x9.potx`
  - used for mixed-layout awareness and title/content pacing
- `datawave-insights-16x9.potx`
  - used for the main palette and calmer reporting tone
- `modern-navy-horizon-16x9.potx`
  - used only for edge-weighted color blocking and stronger accent energy

## Translation Choices

- Palette
  - deep navy `#0E2841`
  - teal `#156082`
  - coral `#E97132`
  - soft paper background `#F7F8FA`
- Typography
  - `Aptos Display` for titles
  - `Aptos` for subtitle/body text
- Layout
  - title slide: asymmetrical left navy block plus clean right-side reading area
  - body slide: one dominant white content card and a smaller right-side editorial rail

## Safety Choices

- The body layout keeps exactly one main body text placeholder.
- Decorative elements are regular shapes, not extra content placeholders.
- No image placeholder is used in this template because the current profiler
  boundary still admits image-capable placeholders as text candidates.

## Current Role

Treat this template as a `text-first, reference-inspired` fixture.
It is meant to show that the branch can move beyond neutral baseline styling
without waiting for the mixed image/text runtime patch.
