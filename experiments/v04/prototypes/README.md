# v0.4 Prototypes

Prototype code in this directory is intentionally isolated from the production
runtime. It exists so the branch can explore APIs and data flow without forcing
premature decisions into `autoreport/`.

Rules:

- keep prototypes self-contained
- prefer explicit inputs and outputs
- avoid side effects by default
- do not import these modules from runtime entrypoints
- delete or rewrite freely when the design changes
