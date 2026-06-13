# Changelog

All notable changes to dashmotion. Versions follow the git tags; the skill's
`SKILL.md` frontmatter `version:` matches the released tag. The output contract is
unchanged across every version: one self-contained HTML file — no libraries, no
build step.

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
