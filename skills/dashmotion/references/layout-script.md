# Layout Script — `scripts/layout.py`

`layout.py` (pure Python stdlib, zero deps) does the coordinate arithmetic the
mode references describe — row packing, branch gaps, boundary padding, orthogonal
rail/lane routing — **and renders the finished HTML** (geometry + style layer +
your copy). So you stop hand-computing coordinates *and* stop hand-transcribing
them into a template. **You decide the semantics and the copy (types, tiers,
grouping, journeys, emphasis, title/subtitle/summary); the script writes the
file.**

> **Treat `layout.py` as a black box — do NOT read its source.** This file is the
> complete contract: what JSON to feed it, what geometry it returns, and how to
> transcribe that geometry. Reading the 1000-line implementation is wasted time
> (it's exactly the pre-write thinking this script exists to remove). If something
> here is unclear, run it on a tiny graph and look at the output — don't open the source.

```
python3 <skill-dir>/scripts/layout.py graph.json --render out.html  # finished, ready-to-ship HTML
python3 <skill-dir>/scripts/layout.py graph.json                    # geometry JSON -> stdout (fallback/inspection)
```

`--render` is the path you use: it writes the complete deliverable. (`--emit-svg`
is a legacy alias for the same thing. The bare geometry-JSON form is for the
hand-transcribe fallback when there is no Python, and for poking at the numbers.)

Write the input `graph.json` to a **temp path** (`"$TMPDIR/…"` or `mktemp`), not
the output folder: it is a throwaway intermediate, the rendered HTML does not
depend on it, and the user's folder should end up holding only the `.html`.

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
  "subtitle": "one-line description under the title (optional)",
  "summary": [                                     // ARCH: exactly 3 cards (optional; a neutral stub renders if omitted)
    {"accent": "cyan|violet|rose", "title": "card title", "items": ["bullet", "bullet"]}
  ],
  "footer": "footer line (optional)",
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
  Group `kind`: namespaces / VPCs / regions → `region` (amber `8 4`); subnets /
  inner zones → `subnet` (rose `4 4`). Details in `architecture-mode.md`.
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
- **Copy:** write `title`/`subtitle` always; in architecture write a `summary` of
  exactly three cards (this is the model's voice — describe the request path, the
  data layer, the boundaries, in the diagram's own terms). Omit it and a neutral
  three-card stub renders instead. Legend wording for preserved classDef variants
  goes in `legendExtra` (verbatim from the source — Step 6 checks it).

## Output — the finished file (`--render`)

With `--render out.html` the script writes the complete, self-contained deliverable
and there is nothing to transcribe. It applies, from your JSON, all of:

- geometry — every `x/y/w/h`, every orthogonal path `d`, every group box, viewBox;
- the style layer — node fills/strokes by `type`, the opaque-base + styled-rect
  masking pair (architecture), `flow`/`flow-async`/`flow-auth` connector classes by
  edge `kind`, per-journey dot colours with staggered chained `begin`;
- your copy — `title`, `subtitle`, the three `summary` cards, the legend (type
  swatches + `request in flight` + any `legendExtra`);
- the boilerplate — CSS, the ⏯ pause toggle, the reduced-motion script, `role`/
  `<title>`/`<desc>`.

Edges with `"loop": true` come out as the `↻ label` annotation, not a path. Run
Step 6 on the file; to change anything, edit the JSON and re-render, or hand-edit
the emitted HTML for a one-off tweak.

### Geometry JSON (fallback / inspection only)

Run without `--render` to print geometry instead of writing a file — the shape the
hand-transcribe fallback consumes when there is no Python, and a way to inspect the
numbers:

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

In the fallback you wrap each node's rect at those exact numbers, draw each
connector with that exact `d`, animate dots along the same `d` — **copy every
coordinate verbatim, never recompute or round** — and apply the style + copy layers
by hand. That transcription is the cost `--render` removes; only do it when Python
is unavailable.
