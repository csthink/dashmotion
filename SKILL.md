---
name: dashmotion
description: Create dark-themed, animated technical diagrams as self-contained HTML+SVG files — flowcharts whose connectors visibly flow, and architecture diagrams where requests travel as light dots through the system (Diagrid/Temporal landing-page style). Use this skill whenever the user asks for a flowchart, workflow, pipeline, process diagram, state machine, system architecture, infrastructure, cloud, microservices, or network topology diagram — and especially when they mention "animated", "flowing", "dynamic", "alive", "GIF-like", or want a diagram for a landing page, README, docs, or product demo. Prefer this over static diagram output whenever the diagram represents anything that moves: requests, events, data, jobs, messages, or control flow.
---

# Dashmotion

Create professional animated technical diagrams as single self-contained HTML files. The name is the implementation: `stroke-dash`offset animation + `animateMotion` — that's all there is. Output is vector, loops forever, weighs a few KB, and opens in any browser.

## Step 1 — Pick the mode

| User wants | Mode | Read |
|---|---|---|
| Steps, sequence, branching, parallel execution, state transitions ("what happens, in what order") | **Flow** | `references/flow-mode.md` + `resources/template-flow.html` |
| Components, services, infrastructure, containment, topology ("what the system is made of") | **Architecture** | `references/architecture-mode.md` + `resources/template-architecture.html` |

Mixed request ("show our microservices AND how an order flows through them") → Architecture mode; the animated request path *is* the flow. Only produce two separate files if the process has branching logic that the topology can't express.

**Read the mode reference file before writing any coordinates.** Each contains the layout arithmetic that prevents the common failures (overlaps, arrows through boxes, broken loops).

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

- Page: `#020617`, 40px grid pattern (`#0f1b33`, 0.5px lines), JetBrains Mono via Google Fonts.
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

1. Parse the description into nodes (typed), edges (directed), groups/boundaries.
2. Do the layout arithmetic from the mode reference explicitly before writing coordinates.
3. Copy the mode's template; replace SVG content, title, header, legend, summary cards. Keep CSS, pause toggle, and reduced-motion script intact.
4. Pick 3–6 dot paths, copy connector `d` values, stagger `begin`.
5. Save as `<topic>-dashmotion.html`. Tell the user it opens directly in any browser.

### GIF/MP4 export (only if asked)

Never render frames by hand. Screen-record the open file (macOS ⌘⇧5), or headless:
`npx timecut <file.html> --viewport=1200,900 --duration=3 --fps=30 --output=flow.mp4` then `ffmpeg -i flow.mp4 flow.gif`.
A 3s capture loops seamlessly when all durations divide 3s — prefer 0.75s / 1.5s / 3s when GIF export is the goal.

## Output contract

One self-contained `.html`: embedded CSS, inline SVG, no external assets except Google Fonts, no JS dependencies — only the ~15-line inline pause/reduced-motion script. Renders correctly opened from the filesystem.