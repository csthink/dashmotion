# Changelog

All notable changes to dashmotion. Versions follow the git tags; the skill's
`SKILL.md` frontmatter `version:` matches the released tag. The output contract is
unchanged across every version: one self-contained HTML file — no libraries, no
build step.

## Versioning

Semantic versioning, with one project-specific rule of thumb: the dividing line is
the **user-facing capability surface** — what you can ask for and what you get back —
not how the generator produces it.

- **MAJOR** (`x.0.0`) — the output contract changes, or the skill is redefined
  wholesale. Reserved for a break in the "one self-contained HTML file" promise, or a
  next-generation rewrite (`2.0.0`). Hasn't happened within v2.
- **MINOR / feature** (`2.x.0`) — a new thing the user can *do*: a new accepted
  **input**, a new **output** mode or style, or a new refinement they can ask for. The
  capability surface grows; the output contract holds. *Precedent:* `2.2.0` added
  Mermaid input — "a feature release, not a patch."
- **PATCH** (`2.2.x`) — everything else: performance, generator/authoring-workflow
  internals, layout or aesthetic refinement, bug fixes, docs. Same inputs in, same
  kind of output out — just faster, better, or correct. *Precedent:* `2.2.1` rewired
  the generator so `layout.py` renders the finished file — a large internal change,
  but the user asks for nothing new and gets the same contract, so "a performance
  patch, not a feature."

The test, in one line: **could a user ask for something they couldn't before, or get
a materially different kind of artifact? → minor; otherwise → patch.**

## 2.2.3 — Leaner model output: omittable `shape`/`tier` + group-membership check

A **patch**, not a feature: same inputs, same self-contained-HTML output contract.
Two fields the model used to hand-write on every node are *derivable*, so the
authoring docs now tell it to omit them — less model output (the project's dominant
cost) for an identical diagram — and a new structural check closes a blind spot in
the verifier. Nothing new to ask for.

### Changed

- **Flow `shape` is omitted on steps.** `step` is exactly what the engine renders
  when `shape` is absent, so the authoring contract now says to write `shape` *only*
  for pills and decisions, never `"shape": "step"`. Identical render, less output —
  a live `m7-pr-cicd` generation trimmed ~170 B of node JSON (≈10% of the flow graph).
- **Architecture `tier` is omitted for ungrouped / single-group diagrams.** The
  engine already layers by longest-path when `tier` is absent; the docs now say to
  omit `tier` there (all-or-nothing) and keep it explicit only for **multi-group**
  diagrams, or when a cross-cutting sink must be pinned to a row. A live ungrouped-arch
  generation trimmed ~77 B (≈12% of its node array).
- The omission guidance is deliberately **imperative** ("do not write it; omit it"),
  not permissive: a live test showed an "optional" framing left the model writing
  every field anyway, realizing zero saving. The docs state the cost so the model acts.

### Added

- **`check_diagram` C9 — group membership.** A node sitting fully inside a group box
  it is *not* a member of is now reported. This is the silent corruption class the
  existing C1 cannot see — C1 exempts full containment (subnet-in-region is a
  legitimate box-contains-node case), so a group-blind layout could swallow a foreign
  node with a green check. To make membership judgeable from the HTML alone (no graph
  JSON needed at generation-time Step 6), the renderer now embeds `data-grp` (a node's
  resolved ancestor-group set) and `data-grp-id` (a box's group) on architecture
  rects. The attributes are invisible and the file stays self-contained.

### Verified

- `run_checks` 11/11, `check_diagram` 0 violations (including C9), `check_fidelity`
  PASS. Group-membership guard `check_c9.py`: authored fixtures 0 C9; tier-stripped
  multi-group fixtures correctly FAIL C9 (the previously-silent corruptions).
- Live medium-effort validation: flow (`m7`) omitted all 12 step shapes; an ungrouped
  architecture omitted all tiers (engine auto-layered cleanly, sinks at the bottom);
  bianque (35 nodes / 38 edges, multi-group) kept its tiers, generated in ~4 min
  (inside the 8-min perf gate), 0 violations including C9 — no false positive on a
  freshly generated multi-group diagram.

## 2.2.2 — Self-contained output; stricter label fidelity

A **patch**, not a feature: same inputs, same output contract — the rendered file
is now *fully* self-contained, and the fidelity check no longer hides a dropped
label separator. Nothing new to ask for.

### Changed

- **The output drops its Google Fonts dependency — now truly self-contained.** The
  rendered HTML no longer links `fonts.googleapis.com`; it falls back through a system
  monospace stack (`'JetBrains Mono', ui-monospace, 'SF Mono', 'Cascadia Code', Menlo,
  Consolas, monospace`), so JetBrains Mono still renders when installed locally, but the
  file now opens offline, issues no third-party request, and carries zero external
  assets. The output contract's "no external assets except Google Fonts" becomes just
  "no external assets."

### Fixed

- **`check_fidelity.py` now catches a genuinely dropped label separator.** It used to
  strip separator punctuation (`：:·•,，;；`) before matching, which also silently
  accepted a label whose separator was lost in rendering. It now matches the separator
  as an element boundary — the legitimate architecture label/sublabel split (`A：B` →
  two adjacent `<text>` elements) still passes, while a real collapse (`A：B` → "A B" in
  one element) is reported instead of hidden.

### Verified

- `run_checks` 11/11, `check_diagram` 0 violations, `check_fidelity` PASS (including the
  new boundary case). Local-test bianque (35 nodes / 38 edges) generated in ~3 min,
  inside the 8-min perf-gate. Model output and render latency unchanged — both changes
  live off the model's authoring path (deterministic Python + template), so generation
  cost is identical.

## 2.2.1 — Performance: layout.py renders the finished file

A **performance** patch, not a feature: same inputs, same self-contained-HTML
output contract — the generator just does more of the work, so diagrams come out
faster.

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
  on all 7 Mermaid cases + bianque. Confirmed end-to-end in local testing: a fresh
  medium-effort bianque (35 nodes / 38 edges) generated in ~3 min — well inside the
  8-min perf-gate, down from ~5 min — with structure + fidelity verified.

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
