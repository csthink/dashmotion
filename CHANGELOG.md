# Changelog

All notable changes to dashmotion. Versions follow the git tags; the skill's
`SKILL.md` frontmatter `version:` matches the released tag. The output contract is
unchanged across every version: one self-contained HTML file — no libraries, no
build step.

## [Unreleased] — `--render` finished-file path (perf)

Branch `feat/perf-render-path`. **Not released; pending local verification.**

### Changed

- **`layout.py --render out.html` writes the complete, ready-to-ship HTML** —
  geometry + the mode style layer + the model's copy — instead of the model
  hand-transcribing 35 rects and 38 path `d`s into a template. Plan A moved the
  *coordinate arithmetic* out of the model; this moves the *boilerplate
  transcription* out too. The semantic graph JSON now carries the human-facing copy
  (`subtitle`, a 3-card `summary`, optional `footer`); the model authors semantics +
  copy and runs the script, keeping final say by editing the JSON (re-render) or the
  emitted file. `--emit-svg` is kept as an alias; the hand-transcribe path remains
  the documented fallback when `python3` is unavailable.
- **Step 5** rewritten to the no-transcription flow; **Step 6** unchanged (still the
  authority — runs on the rendered file). The semantic `graph.json` is written to a
  **temp path**, not the output folder, so the user's folder holds only the `.html`.
- **Routing: shared per-source trunk lanes.** A node that fans out to several
  off-column targets (e.g. `InvestigationGraph → 5 core modules`) now shares one
  margin trunk with horizontal taps instead of N lanes marching into empty space.
  On the bianque graph this collapses 12 left lanes to 3 and shrinks the left-margin
  band ~64% (226px → 82px), with `check_diagram` still at 0 violations.
- **Journey dots speed up on long edges.** Dot travel time is now capped (`DOT_DUR_MAX`
  4s) so a dot riding a long cross-diagram edge no longer crawls — on bianque the
  slowest dots drop from ~11.6s to ≤4s; short-hop dots are unchanged.

### Performance

- Generation output the model must write drops **~84% aggregate** across the 11-case
  regression suite and **~79.5%** on the bianque-class benchmark (model emits 6.3 KB
  of JSON instead of hand-writing 30.9 KB of HTML). Regression stays green: 11/11
  `run_checks`, `check_diagram` 0 violations on all 12 graphs, `check_fidelity` PASS
  on all 7 Mermaid cases + bianque. End-to-end wall-clock confirmation is the
  local-test step (fresh medium-effort bianque, per the perf-gate protocol).

## 2.2.0 — Mermaid input + deterministic layout engine

A **feature** release, not a patch.

### Added

- **Mermaid input.** Paste a `flowchart`/`graph` or `stateDiagram-v2` source and it
  becomes the same animated diagram — every node, edge, edge label and subgraph
  containment preserved, edge kinds mapped (`-->` flows, `-.->` async dotted, `==>`
  main path). Layout is always recomputed top-down (`LR` sources re-laid out;
  structure preserved, geometry not). Unsupported diagram types (sequence, class,
  ER, gantt) are declined rather than lossily guessed.
  (`references/mermaid-input.md`, `references/layout-script.md`)
- **Deterministic layout engine — `scripts/layout.py`** (pure-stdlib Python). The
  model emits a *semantic* graph JSON (nodes/types/edges/groups/journeys), the
  script computes **all** geometry — row packing, branch-bar fan-out/in, nested
  boundary padding, collision-free orthogonal routing, semantic classDef strokes,
  chained journeys — and the model transcribes the result. This removes the
  minutes of hand-computed coordinates that dominated large diagrams: a 32-node
  architecture now generates in well under the prior time, with zero structural
  violations.
- **Mechanized fidelity self-check — `scripts/check_fidelity.py`** bundled into the
  skill. On Mermaid input, Step 6 runs it and fixes to `PASS`, so node/edge/legend
  labels are verified verbatim against the source — catching paraphrase the
  structural checker can't see.

### Changed

- **Step 5** produces files via the script path (semantic JSON → `layout.py` →
  transcribe geometry + style/copy layer), with a hand-computed fallback when
  `python3` is unavailable.
- **Step 6** is fully mechanized when `python3` is available: `check_diagram.py`
  (structural, C1–C8) **and** `check_fidelity.py` (Mermaid fidelity) run at
  generation time; browser-screenshot verification is banned.
- Architecture boundary classification is explicit: Kubernetes namespaces, VPCs,
  cloud regions/accounts → amber **region** (`8 4`); subnets, security groups,
  private/internal zones → rose **subnet** (`4 4`).

## 2.1.1 — Docs & onboarding

- Chinese README, demo GIFs for both modes, install / uninstall / manual-install
  migration notes.

## 2.1.0 — Structural self-check

- Step 6 post-generation structural self-check (overlaps, connectors through boxes,
  broken animation loops, out-of-viewBox coordinates) plus the paired evaluation
  harness in `eval/` with before/after evidence.

## 2.0.0 — Dashmotion v2

- Animated flow & architecture diagram skill: `stroke-dashoffset` flowing
  connectors + `animateMotion` traveling dots, two modes (flow / architecture),
  semantic palette, containment boundaries, request journeys — all as a single
  self-contained HTML file.
