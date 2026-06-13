# How dashmotion works

Implementation notes. For what dashmotion does and how to install it, see the [README](../README.md); for version history, [CHANGELOG.md](../CHANGELOG.md).

## The animation

**Flowing dashes** — animate `stroke-dashoffset` by exactly one dash period:

```css
.flow { stroke-dasharray: 5 5; animation: dashmove 0.75s linear infinite; }
@keyframes dashmove { to { stroke-dashoffset: -10; } }
```

**Traveling dots** — `<animateMotion>` reusing the connector's own path data. In architecture mode, dots chain via SMIL event timing (`begin="j1.end+0.3s"`) so one request visibly hops tier by tier:

```svg
<circle r="3.5" fill="#22d3ee">
  <animateMotion id="j2" dur="0.7s" begin="j1.end+0.3s" fill="freeze"
    path="M416 118 L464 118"/>
</circle>
```

## The layout engine

The layout arithmetic that makes generation reliable — branch-bar fan-out/fan-in, boundary nesting and padding, opaque masking under semi-transparent fills, legend placement, seamless-loop constraints, collision-free routing, and z-ordering so dots vanish *into* the node they arrive at — is computed by a bundled pure-stdlib engine, `scripts/layout.py`: the model describes the diagram as a semantic graph, the script returns the geometry, and the model transcribes it (a hand-computed fallback runs when `python3` is unavailable). Before delivering, two bundled checkers run and fix what they find — `scripts/check_diagram.py` for structure (overlapping boxes, connectors cutting through nodes, broken animation loops, out-of-viewBox coordinates) and, on Mermaid input, `scripts/check_fidelity.py` to confirm every label and edge survived verbatim. The *output* stays dependency-free either way: one HTML file, no libraries, no build step — the Python is generator-side only.

## Project layout

```
dashmotion/                               # repo root
├── skills/dashmotion/                    # the skill — this is what installs
│   ├── SKILL.md                          # Mode routing + animation contracts + shared tokens
│   ├── references/
│   │   ├── flow-mode.md                  # Flowchart layout arithmetic
│   │   ├── architecture-mode.md          # Semantic palette, boundaries, legend, request journeys
│   │   ├── mermaid-input.md              # Mermaid → dashmotion conversion rules + fidelity contract
│   │   └── layout-script.md              # layout.py input/output contract + transcription guide
│   ├── scripts/                          # pure-stdlib, generator-side (output stays dependency-free)
│   │   ├── layout.py                     # Deterministic layout engine — semantic graph → geometry
│   │   ├── check_diagram.py              # Structural checker (C1–C8)
│   │   └── check_fidelity.py             # Mermaid fidelity checker (labels/edges verbatim)
│   └── resources/
│       ├── template-flow.html            # Working flow example
│       └── template-architecture.html    # Working architecture example (AWS, animated request)
├── eval/                                 # structural-check harness + before/after evidence
├── examples/                             # demo GIFs
├── CHANGELOG.md                          # version history
└── README.md
```

`npx skills add` and the release zip ship only `skills/dashmotion/`; `eval/`, `examples/`, `docs/` and `CHANGELOG.md` stay in the repo. Both templates are complete working examples — open them in a browser right now.

## Exporting to GIF / MP4

Screen-record the open file (macOS ⌘⇧5). Animation durations divide 3s evenly, so a 3-second capture loops seamlessly. For any diagram with traveling dots this is the reliable path — see the note below.

Headless / scriptable:

```bash
npx timecut your-diagram.html --viewport=1200,900 --duration=3 --fps=30 --output=out.mp4
ffmpeg -i out.mp4 out.gif
```

> **`timecut` + traveling dots:** the `<animateMotion>` dots run on SVG's SMIL timeline, which `timecut`'s virtual clock doesn't advance — a delayed-start dot stays parked at the SVG origin and leaves a stray mark in the top-left corner of every frame. `timecut` is fine for the dashed-connector flow; for the dots, screen-record in real time or drive a real-time headless screencast (e.g. Chrome DevTools `Page.startScreencast`) instead.
