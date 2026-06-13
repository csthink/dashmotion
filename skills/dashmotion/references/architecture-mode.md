# Architecture Mode — Layout Rules

For system/infrastructure/cloud/network diagrams: components, containment boundaries, and **animated request paths** — a dot in this mode is a request/message traveling through the system.

> The arithmetic below is implemented by `scripts/layout.py` (SKILL.md Step 5) — you author a semantic graph JSON (typed components, `tier`, groups, journeys) and transcribe the geometry it returns, rather than computing these numbers by hand. Read this for the color/type style layer, to author clean input (see `layout-script.md` for tier/grouping rules), and as the recipe for the no-`python3` fallback.

## Semantic color palette

Every component gets a type. Fills are semi-transparent so the grid glows through:

| Component type | Fill (rgba) | Stroke | Use for |
|---|---|---|---|
| Frontend | `rgba(8, 51, 68, 0.45)` | `#22d3ee` (cyan) | clients, UI, edge devices |
| Backend | `rgba(6, 78, 59, 0.45)` | `#34d399` (emerald) | servers, APIs, services |
| Database | `rgba(76, 29, 149, 0.45)` | `#a78bfa` (violet) | DBs, storage, AI/ML |
| Cloud infra | `rgba(120, 53, 15, 0.35)` | `#fbbf24` (amber) | cloud services, CDN, gateways |
| Security | `rgba(136, 19, 55, 0.45)` | `#fb7185` (rose) | auth, IAM, encryption |
| Message bus | `rgba(154, 52, 18, 0.35)` | `#fb923c` (orange) | Kafka, queues, event buses |
| External | `rgba(30, 41, 59, 0.5)` | `#94a3b8` (slate) | third parties, generic |

## The masking rule (critical)

Fills are semi-transparent, so connectors drawn behind a component would show through it. Under EVERY component, draw an opaque base rect first, then the styled rect:

```svg
<rect x="X" y="Y" width="W" height="H" rx="8" fill="#0b1226"/>
<rect x="X" y="Y" width="W" height="H" rx="8" fill="rgba(76,29,149,0.45)" stroke="#a78bfa" stroke-width="1.5"/>
```

Paint order: grid → boundaries → connectors → dots → component pairs (base + styled) → labels. With this order, traveling dots disappear cleanly "into" the component they arrive at.

## Boundaries (containment)

- **Region / cloud boundary**: dashed amber, `stroke-dasharray="8 4"`, `rx="12"`, transparent fill, label top-left inside in 11px amber. Containment edges are STATIC — never animate a boundary border; only request paths flow.
- **Security group / subnet**: dashed rose, `stroke-dasharray="4 4"`, `rx="8"`, label top-left inside in 10px rose.
- **Which kind?** Top-level / logical containment — cloud regions, VPCs, cloud accounts, **Kubernetes namespaces**, availability zones, environments — is a *region* (amber `8 4`). Network / security subdivisions — subnets, security groups, private/internal zones — are *subnets* (rose `4 4`). A namespace/region/VPC is a region, not a subnet; whenever the system has one, at least one boundary is amber. (In the JSON: `"kind": "region"` vs `"kind": "subnet"`.)
- 20px minimum padding between a boundary edge and anything inside it. Boundaries may nest (region ⊃ subnet) but max 2 levels at 1000px width.

## Connectors

- **Request/data paths** (the ones that animate): slate `#64748b` or the source component's stroke color, 1px, `class="flow"`, `marker-end`.
- **Auth/security flows**: rose `#fb7185`, dashed, animated at a SLOWER cycle (1.2s) so they read as a different kind of traffic. Rose dots, smaller (r=3).
- **Sync vs async**: async edges (through a message bus) get `stroke-dasharray="2 4"` dotted styling and orange dots.
- Label protocols/ports beside the line in 9px `#64748b` (`HTTPS`, `:5432`, `gRPC`) — placed in clear space, never on the line.

## Message bus pattern

A thin connector element placed IN the gap between service tiers, never overlapping:

```svg
<rect x="X" y="Y" width="200" height="22" rx="4" fill="rgba(154,52,18,0.35)" stroke="#fb923c" stroke-width="1"/>
<text x="CX" y="Y+15" fill="#fb923c" font-size="9" text-anchor="middle">Kafka</text>
```

Tier A bottom → 44px gap → bus (22px tall, centered in gap) → tier B top. Verify: bus.y ≥ tierA.bottom + 11 and bus.y + 22 ≤ tierB.top − 11.

## Spacing arithmetic

- Component height: 56px standard (label 13px + sublabel 10px), 80–120px for emphasized components.
- Vertical gap between tiers: 44px minimum (90px when a bus or animated fan-out sits in the gap).
- Horizontal gap between same-tier components: 40px minimum.
- ViewBox typically `0 0 1000 H`.

## Legend (required)

Place OUTSIDE and BELOW all boundaries: compute the lowest boundary bottom, legend starts ≥ 20px below it, extend viewBox H accordingly. One swatch per component type actually used, plus one entry: animated dot = "request in flight". Never put the legend inside a boundary.

## Dot journeys (the differentiator)

Design 2–4 **end-to-end journeys**, not per-edge dots. Example: `client → CDN → API gateway → service → database` as a sequence of dots with `begin` values chained so the request visibly "hops" tier by tier (dot 2 begins roughly when dot 1 arrives). An auth journey in rose runs on its own slower rhythm. This is what makes the diagram explain *behavior*, not just structure — prioritize the system's most important request path.

## HTML page structure (below the SVG)

1. Header: pulsing dot + title + one-line subtitle
2. Diagram card (grid background, pause toggle)
3. **Summary cards**: grid of 3 — typical trio: "Request path" (the animated journey in words), "Data layer", "Security". Each: colored dot + h3 + 3–4 bullet items.
4. Footer metadata line

Card markup pattern:

```html
<div class="card">
  <div class="card-header"><div class="card-dot cyan"></div><h3>Request path</h3></div>
  <ul><li>• Client → CDN → API</li><li>• p95 ~120ms</li></ul>
</div>
```