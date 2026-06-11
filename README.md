# Dashmotion

**Diagrams that move.** A Claude AI skill that generates animated technical diagrams as self-contained HTML/SVG files — dashed connectors stream in the direction of execution, and light dots travel through the system like requests in flight. The style you see on modern infra landing pages (Diagrid, Temporal, Inngest), generated from a plain-English description.

The name is the implementation: **`stroke-dash`** offset animation + **`animateMotion`** paths. That's the whole trick — no libraries, no GIF rendering, no design tools.

<!-- TODO: record demo GIFs of both modes — these two images sell the entire project -->
| Flow mode | Architecture mode |
|---|---|
| ![flow demo](examples/images/flow-demo.gif) | ![architecture demo](examples/images/architecture-demo.gif) |

## Two modes

**Flow mode** — workflows, pipelines, state machines. *What happens, in what order.* Monochrome circuitry aesthetic: a dark canvas where execution visibly flows from START to END through branches and merges.

**Architecture mode** — systems, infrastructure, topology. *What the system is made of — and how requests move through it.* Semantic component colors (frontend/service/data/cloud/security), region and security-group boundaries, a legend, summary cards — plus the differentiator: animated request journeys. A cyan dot leaves the client, hops through the CDN and gateway, lands in a service, reaches the database, and a new request begins. Your architecture diagram explains *behavior*, not just structure.

## Why not just a GIF?

| | GIF | Dashmotion (SVG/CSS) |
|---|---|---|
| File size | MBs | KBs |
| Sharpness | fixed resolution | vector, infinite zoom |
| Editable | re-render everything | ask Claude to change one box |
| Loop | frame-perfect work | free |
| Convert to GIF later | — | one command (`timecut`) or screen-record |

## Quick start

> Requires Claude Pro, Max, Team, or Enterprise.

1. Download `dashmotion.zip` from [Releases](../../releases)
2. claude.ai → **Settings** → **Capabilities** → **Skills** → **+ Add** → upload → toggle on
3. Ask:

```
Use dashmotion to visualize this workflow:
- User submits an order
- Validate payment and check inventory in parallel
- Wait for fraud-review timer
- Ship, then send confirmation email and update analytics in parallel
```

or:

```
Use dashmotion to draw our architecture and animate the main request path:
- React frontend behind CloudFront
- API Gateway → Auth Service (Go) and Order Service (Node) in a private subnet
- PostgreSQL and Redis
- Cognito for auth
```

Claude returns a single `.html` file. Open it — it's already moving.

### Claude Code

```bash
unzip dashmotion.zip -d ~/.claude/skills/      # global
unzip dashmotion.zip -d ./.claude/skills/      # or project-local
```

## How the animation works

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

The skill encodes the layout arithmetic that makes generation reliable: branch-bar fan-out/fan-in, boundary nesting and padding rules, opaque masking under semi-transparent fills, legend placement, seamless-loop constraints, and z-ordering so dots vanish *into* the node they arrive at.

## Project layout

```
dashmotion/
├── SKILL.md                          # Mode routing + animation contracts + shared tokens
├── references/
│   ├── flow-mode.md                  # Flowchart layout arithmetic
│   └── architecture-mode.md          # Semantic palette, boundaries, legend, request journeys
└── resources/
    ├── template-flow.html            # Working flow example
    └── template-architecture.html    # Working architecture example (AWS, animated request)
```

Both templates are complete working examples — open them in a browser right now.

## Exporting to GIF / MP4

```bash
npx timecut your-diagram.html --viewport=1200,900 --duration=3 --fps=30 --output=out.mp4
ffmpeg -i out.mp4 out.gif
```

Or screen-record (macOS ⌘⇧5). Animation durations divide 3s evenly, so a 3-second capture loops seamlessly.

## Accessibility

All CSS animation is gated behind `@media (prefers-reduced-motion: no-preference)`; SMIL dots are removed by script under reduced motion; every diagram ships a visible pause/play toggle and `role="img"` + `<title>`/`<desc>`.

## Credits

Skill packaging pattern and the static architecture design system build on [Cocoon-AI/architecture-diagram-generator](https://github.com/Cocoon-AI/architecture-diagram-generator) (MIT). Visual style inspired by the workflow animations on [diagrid.io](https://www.diagrid.io/catalyst).

## License

MIT