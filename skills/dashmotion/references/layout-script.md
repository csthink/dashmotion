# Layout Script — `scripts/layout.py`

`layout.py` (pure Python stdlib, zero deps) does the coordinate arithmetic the
mode references describe — row packing, branch gaps, boundary padding, orthogonal
rail/lane routing — so you stop hand-computing coordinates. **You decide the
semantics (types, tiers, grouping, journeys, emphasis); the script computes the
geometry.**

> **Treat `layout.py` as a black box — do NOT read its source.** This file is the
> complete contract: what JSON to feed it, what geometry it returns, and how to
> transcribe that geometry. Reading the 1000-line implementation is wasted time
> (it's exactly the pre-write thinking this script exists to remove). If something
> here is unclear, run it on a tiny graph and look at the output — don't open the source.

```
python3 <skill-dir>/scripts/layout.py graph.json                  # geometry JSON -> stdout
python3 <skill-dir>/scripts/layout.py graph.json --emit-svg r.html  # reference render (self-check)
```

## What the engine does for you (so you trust the output)

You never compute a coordinate, a width, or a path `d`. The script owns all of it:

- **Layering (vertical order).**
  - *Flow:* omit `tier`. Nodes are layered by longest-path on the forward-edge DAG.
    Back edges and self-loops are found by DFS and become a `↻ <label>` annotation
    beside the source (the references' loop-sublabel rule), returned as an edge with
    `"loop": true` — **not** a drawn path.
  - *Architecture:* you set `tier` on every node (`0` = top row, increasing
    downward). Each tier becomes one horizontal row.
- **Sizing & wrapping.** Width/height come from the label — **you never size a node.**
  Long labels wrap to two lines automatically; the output's `labelLines` is the
  wrapped result (render each entry as a `<tspan>`). Heights: flow step 44, pill 40,
  arch component 56 (+~16 if it wrapped), `bus` 36.
- **Within-row placement.** Row nodes are ordered group-contiguous then input order,
  centered on the spine. You never set `x`.
- **Boundaries.** A group box is its members' bounding box + 20px padding, computed
  innermost-first so nesting works; the engine also widens inter-tier gaps wherever a
  boundary opens/closes so nested padding never collides. Keep them clean by following
  the contract below.
- **Routing.** Every edge path is orthogonal and guaranteed not to cross a node box:
  adjacent layers → an L through the inter-layer gap; multi-layer / sideways / upward
  edges → straight down their own column when it's clear, else through a margin lane.
  **You never route or nudge anything** — copy the returned `d`.
- **Journeys.** Each hop returns the exact connector `d` of its edge, so the animated
  dot rides precisely on the line.

### Clean-boundary contract (architecture)

Boundaries come out as clean rectangles (checker passes) **iff** you author tiers so:

1. **Each tier belongs to one top-level group** (or is ungrouped). Don't place two
   different top-level groups on the same tier.
2. **A nested subgroup owns the tiers it sits on.** Never put a subgroup member and a
   loose (non-subgroup) sibling on the *same* tier — give them different tiers, or move
   the loose node into the subgroup. (E.g. a `PRIV` subnet of `API`+`WORK` plus a loose
   `Q` queue → put `Q` on its own tier, not API's.)
3. **A multi-tier group's tiers are consecutive** (no other group's tier interleaved),
   so its box is one clean span. **Nesting ≤ 2 levels** (region ⊃ subnet); flatten
   deeper nesting into sublabels.

## Input — the semantic graph JSON you author

```json
{
  "mode": "flow | architecture",
  "title": "short title for the header",
  "nodes": [
    {
      "id": "A", "label": "verbatim label", "sublabel": "arch 2nd line, optional",
      "shape": "pill | step | decision",            // FLOW only
      "type":  "frontend|backend|database|cloud|security|bus|external", // ARCH only
      "tier": 0,                                     // ARCH: the row, 0 = top (required in arch; omit in flow)
      "group": "GROUP_ID",                           // boundary membership, optional
      "semStroke": "#3b82f6", "semDash": "6 3"        // preserved classDef stroke variant, optional
    }
  ],
  "edges": [{ "from": "A", "to": "B", "kind": "sync|async|main|static", "label": "optional" }],
  "groups": [{ "id": "VPC", "label": "AWS VPC", "kind": "region|subnet", "parent": "OUTER_ID?" }],
  "journeys": [{ "color": "#22d3ee", "hops": [["A","B"], ["B","C"]] }],
  "legendExtra": [{ "label": "v2 点线橙框", "stroke": "#f59e0b", "dash": "2 2" }]
}
```

Authoring rules:

- **Flow:** omit `tier`; set `shape` per node; give entry/exit `[*]` nodes `shape: "pill"`.
  Loops/self-loops are handled for you (see above).
- **Architecture:** set `tier` on every node; obey the clean-boundary contract.
- **Edge kinds:** `sync` → animated solid; `async` (`-.->`) → `2 4` dotted, own
  keyframes, orange dots in arch; `main` (`==>`) → 1.5px emphasis + dot priority;
  `static` (`---`) → plain line, no marker, no animation.
- **classDef retention:** when the source pairs a class with a legend, or the class name
  encodes a lifecycle/version stage, set `semStroke`/`semDash` on the affected nodes and
  add matching `legendExtra` entries (see `mermaid-input.md`). **Copy `legendExtra` labels
  verbatim from the source's legend nodes — don't reword, merge two entries, or add
  parentheses;** the fidelity check (Step 6) compares them exactly. A lone emphasis class
  (`hot`, a color) is decoration — drop it.
- **Journeys:** 2–4 end-to-end paths whose `hops` are existing forward edges.

## Output — geometry JSON you transcribe

```json
{
  "mode","title","width","height",
  "nodes": { "A": { "x","y","w","h","shape","type","labelLines":["..."],"sublabel","loopNotes":[] } },
  "edges": [ { "from","to","kind","d","marker","label","labelPos":[x,y] },
             { "from","to","kind","label","loop": true } ],
  "groups": { "VPC": { "label","kind","parent","box":[x,y,w,h] } },
  "journeys": [ { "color", "hops": [ { "from","to","d" } ] } ],
  "notes": []
}
```

### Worked example (real output)

Input `{ "mode":"flow", "nodes":[{"id":"A","label":"Start","shape":"pill"},{"id":"B","label":"Do work","shape":"step"},{"id":"C","label":"Done","shape":"pill"}], "edges":[{"from":"A","to":"B"},{"from":"B","to":"C"}], "journeys":[{"hops":[["A","B"],["B","C"]]}] }`
gives `width 178, height 314`,
`nodes.A = {x:34, y:34, w:110, h:40, shape:"pill", labelLines:["Start"]}`,
`edges[0] = {from:"A", to:"B", kind:"sync", d:"M89 74 V126", marker:true}`,
`journeys[0].hops[0] = {from:"A", to:"B", d:"M89 74 V126"}`. You wrap A's rect at
those exact numbers, draw the connector with that exact `d`, and animate the dot
along the same `d` — no arithmetic of your own.

## Transcription

**Copy every `x/y/w/h` and every path `d` exactly as printed — do not recompute,
round, or re-derive a coordinate by hand;** that arithmetic is the cost the script
removes, and Step 6's checker (not your re-checking) is the authority. Your remaining
work is the *style* layer from the mode reference (fills/strokes by type, the
opaque-base + styled-rect masking pair, connector colors and the
`flow`/`flow-async`/`flow-auth` classes by `kind`, dot colors) plus the human-facing
copy (title, subtitle, summary cards, legend wording) and staggering journey dot
`begin`. Edges with `"loop": true` render as the `↻ label` annotation, not a path.
`--emit-svg` shows one valid rendering to diff against.
