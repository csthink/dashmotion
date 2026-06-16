---
name: dashmotion
version: 2.2.4
description: 'Create dark-themed, animated technical diagrams as self-contained HTML+SVG files — flowcharts whose connectors visibly flow, and architecture diagrams where requests travel as light dots through the system (Diagrid/Temporal landing-page style). Use this skill whenever the user asks for a flowchart, workflow, pipeline, process diagram, state machine, system architecture, infrastructure, cloud, microservices, or network topology diagram — and especially when they mention "animated", "flowing", "dynamic", "alive", "GIF-like", or want a diagram for a landing page, README, docs, or product demo. Also use it to convert Mermaid source (a mermaid code block or .mmd file) into an animated diagram — "animate this mermaid", "make this flowchart move". Prefer this over static diagram output whenever the diagram represents anything that moves: requests, events, data, jobs, messages, or control flow.'
---

# Dashmotion

Create professional animated technical diagrams as single self-contained HTML files. The name is the implementation: `stroke-dash`offset animation + `animateMotion` — that's all there is. Output is vector, loops forever, weighs a few KB, and opens in any browser.

## Step 1 — Pick the mode

| User wants | Mode | Read |
|---|---|---|
| Steps, sequence, branching, parallel execution, state transitions ("what happens, in what order") | **Flow** | `references/flow-mode.md` + `resources/template-flow.html` |
| Components, services, infrastructure, containment, topology ("what the system is made of") | **Architecture** | `references/architecture-mode.md` + `resources/template-architecture.html` |

Mixed request ("show our microservices AND how an order flows through them") → Architecture mode; the animated request path *is* the flow. Only produce two separate files if the process has branching logic that the topology can't express.

**Mermaid input** — if the request contains Mermaid source (a ```mermaid block, a `.mmd` file, or pasted code), ALSO read `references/mermaid-input.md` before anything else. Supported: `flowchart`/`graph` and `stateDiagram-v2`; other diagram types are unsupported — say so and offer alternatives. The mode routing above still applies (mermaid is syntax, not semantics), and layout is always recomputed top-down regardless of the source's declared direction.

**Read the mode reference file before you start.** Its layout arithmetic is what `scripts/layout.py` implements (Step 5) — read it to author a clean semantic graph and to apply the color/shape/animation style layer to the script's geometry (and to hand-compute the fallback). It encodes what prevents the common failures: overlaps, arrows through boxes, broken loops.

## Step 2 — The two animation contracts (both modes)

### Flowing dashed connectors — `stroke-dashoffset`

```css
.flow { stroke-dasharray: 5 5; animation: dashmove 0.75s linear infinite; }
@keyframes dashmove { to { stroke-dashoffset: -10; } }
```

- The offset delta MUST equal one full `stroke-dasharray` period (here 5+5=10), or the loop visibly jumps.
- Negative offset flows in the path's drawing direction → **always author connector `d` from source to target.**
- 0.6–0.9s reads as "electric current"; slower than 1.5s reads as broken.

### Traveling dots — `<animateMotion>`

```svg
<circle r="3.5" class="dot" fill="#34d399">
  <animateMotion dur="2s" repeatCount="indefinite"
    path="M400 178 L400 204 L170 204 L170 222"/>
</circle>
```

- `path` reuses the connector's `d` verbatim; the dot rides exactly on the line.
- The circle has no `cx`/`cy` — `animateMotion` positions it.
- Stagger with `begin="0.7s"` etc. 3–6 dots total per diagram; put them where direction is informative (fan-outs, merges, the main request path), never on every edge.
- In Architecture mode a dot is semantically **a request/message in flight** — route dots along realistic end-to-end journeys.

## Step 3 — Shared design tokens

- Page: `#020617`, 40px grid pattern (`#0f1b33`, 0.5px lines), JetBrains Mono when locally installed, else a system monospace stack (`ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, Consolas, monospace`) — no web-font fetch, the file is fully self-contained.
- Text: labels `#e2e8f0` 13px/500, sublabels `#64748b` 10px, legend 11px.
- Node corner `rx="8"`; START/END pills `rx` = height/2.
- One shared arrowhead marker using `context-stroke` (inherits each line's color):

```svg
<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
  <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</marker>
```

- Connector endpoints stop **4px short** of node edges so arrowheads don't pierce borders.
- **Every connector `<path>` MUST have `fill="none"`** (or sit in a `<g fill="none">`) — SVG defaults to black fill and an L-shaped path renders as a giant black polygon without it.
- Z-order paint sequence: grid → connectors → dots → nodes. Nodes mask line ends; dots vanish "into" nodes instead of sliding over them.
- ViewBox: `0 0 W H` where H = lowest element bottom + 50. Never negative coordinates.

## Step 4 — Accessibility & motion (non-negotiable)

- Wrap ALL CSS animation in `@media (prefers-reduced-motion: no-preference)`.
- SMIL ignores that media query → keep the template's inline script that removes `.dot` elements under reduced motion and wires the visible ⏯ pause toggle (`animation-play-state: paused` + `svg.pauseAnimations()`).
- SVG gets `role="img"` + `<title>` + `<desc>`.

## Step 5 — Produce the file

dashmotion ships a deterministic layout engine, `scripts/layout.py` (pure stdlib). It does the coordinate arithmetic the mode references describe — row packing, branch gaps, boundary padding, orthogonal rail/lane routing — **and renders the finished HTML**: geometry + the mode style layer + your copy. So you do **not** hand-compute coordinates *or* hand-transcribe 35 rects and 38 path `d`s into a template (both are slow). You decide the *semantics and the copy*; the script writes the *file*. Full contract in `references/layout-script.md`.

**Script path — use it whenever `python3` is available:**

1. Parse the request — or the Mermaid source per `references/mermaid-input.md` — into the semantic graph JSON of `references/layout-script.md`. **This is your judgement layer**, and it carries everything the diagram needs:
   - structure: nodes (`type` + `tier` for architecture — **omit `tier` for ungrouped/single-group arch** (engine auto-layers), write it for multi-group, see `layout-script.md`; per-node `group` for boundary membership; flow `shape` **written only for pills & decisions — never `"shape": "step"`**, steps omit it), edges (`kind`), groups, journeys, any `legendExtra`, classDef retention;
   - **copy**: `title`, `subtitle`, and (architecture) a `summary` of exactly three cards (`accent` cyan/violet/rose, `title`, `items[]`) — the human-facing wording is yours to write, here, in the JSON.
2. Write it to a **temporary path, not the output folder** — e.g. `"$TMPDIR/dashmotion-graph.json"` (or any `mktemp` path) — then run `python3 <this-skill-directory>/scripts/layout.py "$TMPDIR/dashmotion-graph.json" --render <topic>-dashmotion.html`. The semantic JSON is a throwaway build intermediate; the delivered HTML does not depend on it, so **never write it beside the `.html`** — the user's folder should contain only the finished diagram. The script computes the geometry, applies the style layer (node fills/strokes by `type`, the opaque-base + styled-rect masking pair, `flow`/`flow-async`/`flow-auth` connector classes by edge `kind`, per-journey dot colors with staggered, chained `begin`), drops in your copy, and writes the **complete, self-contained, ready-to-ship file**. Edges flagged `"loop": true` are rendered as the `↻ label` annotation, not a path.
3. Run Step 6 against that file. The renderer is structurally sound by construction, but Step 6 is still the authority — run it.
4. You keep final say over everything visual: to adjust wording, emphasis, journeys, or types, **edit the JSON and re-render** (cheap and deterministic); to tweak a label or a colour by hand, edit the emitted file directly. What you no longer do is photocopy coordinates — the script owns geometry (plan A) and now the boilerplate around it.

Do not author the JSON, then *also* hand-write the HTML — that re-incurs the exact transcription cost this path removes. Render, check, deliver.

**Hand-computed fallback — only when `python3` is unavailable:** do the layout arithmetic from the mode reference explicitly before writing coordinates, copy the template, replace SVG content / title / header / legend / summary cards (keep CSS + pause toggle + reduced-motion script), pick 3–6 dot paths copying connector `d` values and staggering `begin`. This is the pre-2.2 path — slow, but it needs no Python.

Tell the user the file opens directly in any browser.

### GIF/MP4 export (only if asked)

Never render frames by hand. Screen-record the open file (macOS ⌘⇧5), or headless:
`npx timecut <file.html> --viewport=1200,900 --duration=3 --fps=30 --output=flow.mp4` then `ffmpeg -i flow.mp4 flow.gif`.
A 3s capture loops seamlessly when all durations divide 3s — prefer 0.75s / 1.5s / 3s when GIF export is the goal.

## Step 6 — Structural self-check (before delivering)

The file is not done when it's written — it's done when it passes this check. The `--render` output is structurally sound by construction, but the check is still mandatory (it's also your guard for the hand-computed fallback, whose coordinates fail in predictable ways — the connector layer far more often than the text layer). Verify; don't assume.

**Mechanized path (use it whenever `python3` is available):** run the bundled checker against the file you just wrote —

```bash
python3 <this-skill-directory>/scripts/check_diagram.py <your-file>.html
```

It deterministically detects the failure classes below (overlaps, connectors through boxes, dash-loop seams, out-of-bounds, dots off their line, black-fill, endpoint pierce, dangling begin refs, malformed XML). Fix every reported violation and re-run until it prints `0 violations`. Do NOT hand-walk the arithmetic when the script is available, do NOT write your own ad-hoc verification script, and **never verify by opening a browser or taking screenshots** — the script is the authority; items it can't see (label collisions, exact boundary padding, legend placement) you still check by reading the numbers.

**If the input was Mermaid**, also mechanize the fidelity recount (checklist item 6): save the source to a temp `.mmd` and run —

```bash
python3 <this-skill-directory>/scripts/check_fidelity.py <source>.mmd <your-file>.html
```

Fix until it prints `PASS`. It verifies every source node/edge/group label appears **verbatim** and the connector count matches the source's edge count. So keep labels and legend entries exactly as the source wrote them — do not reword, merge two source strings into one, or add parentheses (a legend entry `v2 点线橙框` must stay `v2 点线橙框`, never `v2 治理骨架（点线橙框）`). This is the same low-recall trap as the structural check: prose "I kept it verbatim" misses real drift; the script doesn't.

**Prose fallback (only if `python3` is unavailable):** verify each item below **with arithmetic on the actual numbers** (write the comparisons out), not by eyeballing the code. Fix every violation and re-check until the list is clean.

1. **Overlaps** — for every pair of same-row elements: `left.x + left.width + gap ≤ right.x` (gap ≥ 20 flow / 40 architecture). For every stacked pair: `top.y + top.height + gap ≤ bottom.y`. A boundary must fully contain its children with ≥ 20px padding on all four sides; partial overlap between any two boxes is always a bug.
2. **Connectors through boxes** — walk every path segment by segment: between its endpoints it must not enter any node rect. Check every horizontal rail's `y` against the rects it passes (`rect.y ≤ y ≤ rect.y + height` means a collision); same for vertical drops' `x`. Fix by re-routing with the rail pattern, not by nudging boxes until something else breaks.
3. **Animation loops** — for each animated class: `|stroke-dashoffset delta|` must be an exact multiple of the `stroke-dasharray` period sum (e.g. `5 5` → 10), **including connectors that override the dasharray inline** (an async `2 4` edge animated by a `-10` keyframe seams every cycle — give it its own keyframes). For each `animateMotion`, name the single connector whose `d` it traces — a dot path that spans two connectors sails straight through the component between them; split it into chained per-hop dots instead. Every `begin="X.end+…"` must reference an `id` that exists.
4. **ViewBox bounds** — no negative coordinates anywhere; every rect's `x+width`/`y+height` and every path coordinate stays inside `0 0 W H`; H ≥ lowest element bottom + 20; the legend sits below the lowest boundary (architecture).
5. **Connector & markup hygiene** — every connector `<path>` resolves to `fill="none"`; endpoints stop ~4px short of the target border and never reach inside a box; no `--` inside SVG comments (`<!-- A -- B -->` closes the comment early and leaks stray text into the document).
6. **Mermaid fidelity (mermaid input only)** — mechanized by `check_fidelity.py` above; run it and fix to `PASS`. It recounts against the source: node rects/pills == source node IDs (START/END pills added only for `[*]`); connector paths + `↻`-rendered loops == source edges after expanding chains and `&`; every node, edge, group, **and legend** label appears **verbatim** (legend entries merged from a 图例 subgraph included — keep their exact text). Without `python3`, recount by hand. Details in `references/mermaid-input.md`.

Deliver the file only after a pass where nothing needed fixing.

## Output contract

One self-contained `.html`: embedded CSS, inline SVG, no external assets, no JS dependencies — only the ~15-line inline pause/reduced-motion script. Renders correctly opened from the filesystem.