# Dashmotion

English | [简体中文](https://github.com/csthink/dashmotion/blob/main/README.zh-CN.md)

[![version](https://img.shields.io/badge/version-2.2.4-10b981?style=flat&labelColor=0b1226)](https://github.com/csthink/dashmotion/releases)
[![license: MIT](https://img.shields.io/badge/license-MIT-64748b?style=flat&labelColor=0b1226)](https://github.com/csthink/dashmotion/blob/main/LICENSE)
[![live demo](https://img.shields.io/badge/▶%20live%20demo-22d3ee?style=flat&labelColor=0b1226)](https://csthink.github.io/dashmotion/)

**Diagrams that move.**

A Claude skill for animated technical diagrams — from plain English or Mermaid, as one self-contained HTML/SVG file.

Turn a plain-English description — or a Mermaid source — into an animated diagram: one HTML/SVG file, no dependencies, where dashed connectors stream in the direction of execution and light dots travel through the system like requests in flight. The style you see on modern infra landing pages (Diagrid, Temporal, Inngest).

[![Dashmotion animating a checkout request through a Kubernetes architecture — ingress → cart → payments → Postgres, plus a Kafka async event to a worker](https://github.com/csthink/dashmotion/raw/main/examples/images/k8s-hero.gif)](https://csthink.github.io/dashmotion/)

**[▶ Watch real diagrams run live →](https://csthink.github.io/dashmotion/)** — unedited skill output, not a video.

> ⭐ If dashmotion saved you from hand-drawing a diagram, [a star](https://github.com/csthink/dashmotion) helps others find it.

## Two modes

| Flow mode | Architecture mode |
| --- | --- |
| [![flow demo](https://github.com/csthink/dashmotion/raw/main/examples/images/flow-demo.gif)](https://github.com/csthink/dashmotion/blob/main/examples/images/flow-demo.gif) | [![architecture demo](https://github.com/csthink/dashmotion/raw/main/examples/images/architecture-demo.gif)](https://github.com/csthink/dashmotion/blob/main/examples/images/architecture-demo.gif) |

## What it does

The name is the implementation: `stroke-dashoffset` offset animation + `animateMotion` paths — no libraries, no GIF rendering, no design tools.

- **Inputs (today):** a natural-language description, or a Mermaid `flowchart` / `graph` / `stateDiagram-v2` source — the same animated result either way.
- **Output styles (today):** **Flow** — workflows, pipelines and state machines, where execution visibly streams from START to END through branches and merges; and **Architecture** — systems and topology, with semantic component colors, region/security boundaries, a legend, and the differentiator: animated request journeys, a dot hopping client → gateway → service → database and back.
- **Refine in plain language:** *"make the auth path stand out"*, *"put Redis next to Postgres"*, *"split the workers into a second diagram."*
- **The output is dependency-free:** one HTML file — vector, loops forever, a few KB, opens in any browser.

## Quick start

Then just ask — one sentence is enough to see it work:

```
Use dashmotion to draw a simple 3-step login flow.
```

The two longer prompts below generated the demos at the top — paste either to reproduce it:

**Flow** — the left demo:

```
Use dashmotion to visualize our CI/CD pipeline: a commit runs lint, unit tests and integration tests in parallel; all three merge into building a Docker image; then a security scan; then a deploy to staging; then a manual approval gate — approved deploys to production and posts a Slack notification, rejected notifies the author and ends.
```

**Architecture** — the hero above:

```
Use dashmotion to draw our Kubernetes microservices platform and animate the main request path: an NGINX ingress in front; users, catalog, cart and payments services in the 'shop' namespace; a Kafka bus between the services and two async workers (email worker, analytics worker); PostgreSQL for orders and MongoDB for the catalog; Prometheus and Grafana in an observability namespace. Animate a checkout request from ingress through cart and payments to PostgreSQL, plus an async event from payments through Kafka to the email worker.
```

**A few things worth knowing:**

- Each generation lays things out a little differently — yours won't be pixel-identical to the demo, but it's the same diagram.
- You don't have to spell everything out: point it at a design doc (*"use dashmotion to draw the architecture in `docs/design.md`"*) or just ask for a flowchart / architecture diagram of what you're building.
- Already have the diagram as Mermaid? Paste it — see [Mermaid input](#mermaid-input) below.
- Don't like the result? Say so in plain language and it refines from there.

## Install

Needs a Claude plan that includes skills (Pro, Max, Team, or Enterprise).

**Claude Code** — one command:

```bash
npx skills add csthink/dashmotion -a claude-code -g
```

**claude.ai** — download `dashmotion.zip` from [Releases](https://github.com/csthink/dashmotion/releases) → Settings → Capabilities → Skills → + Add → upload → toggle on.

<details>
<summary>Why <code>-a claude-code</code>, and global vs. project?</summary>

- **`-a claude-code`** writes a plain *copy* (into `~/.claude/skills/` with `-g`, or `./.claude/skills/` without). The bare `npx skills add csthink/dashmotion` makes a *symlink* instead, and Claude Code's symlink handling is rough — the link may not get created, a symlinked skill doesn't appear in `/skills` ([claude-code#14836](https://github.com/anthropics/claude-code/issues/14836)), and `npx skills update` won't refresh it. A copy lists in `/skills` and updates cleanly. If the CLI ever prompts copy-vs-symlink, choose **copy** (or pass `--copy`). Other agents (Cursor, Codex, …) read `~/.agents/skills/` directly and work fine with the bare command.
- **Global (`-g`)** lives in `~/.claude/skills/`, available everywhere. **Project-local** (no `-g`) lives in `./.claude/skills/` — scoped to that one directory, and handy to commit alongside a repo so your team gets the skill.

Prefer the zip on Claude Code? `rm -rf ~/.claude/skills/dashmotion && unzip dashmotion.zip -d ~/.claude/skills/` — clear the folder first when upgrading so old files don't linger.
</details>

<details>
<summary>Upgrading, auto-update &amp; uninstall</summary>

No Claude client tells you when a skill has a new version — you pull updates yourself. On **Claude Code**, one command refreshes it in place:

```bash
npx skills update dashmotion -g -y
```

Name the skill: a bare `npx skills update -g -y` updates **every** globally-installed skill, not just dashmotion — which may pull updates into others you didn't mean to touch. Drop `-g` for a project-local install; re-running the install command works too. On **claude.ai** there's no in-place update — delete the old skill and upload the new `dashmotion.zip`.

**Check which version you're on** — it lives in the skill's `SKILL.md`; compare it against the latest [release](https://github.com/csthink/dashmotion/releases) (`npx skills list` shows the path, not the version):

```bash
grep '^version:' ~/.claude/skills/dashmotion/SKILL.md     # project-local: ./.claude/skills/dashmotion/SKILL.md
```

**Hands-off: auto-update on every session (Claude Code)** — add a `SessionStart` hook so Claude Code refreshes the skill each time it starts. In `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup", "hooks": [
        { "type": "command", "command": "npx skills update dashmotion -g -y >/dev/null 2>&1 || true" }
      ] }
    ]
  }
}
```

It costs a short network call at startup and silently keeps you on the latest tag. Widen the command to `npx skills update -g -y` to auto-update *all* your global skills.

**Uninstall:**

```bash
npx skills remove dashmotion -g         # installed via the skills CLI (drop -g if project-local)
rm -rf ~/.claude/skills/dashmotion      # installed by unzipping (use ./.claude/... for project-local)
```
</details>

## Mermaid input

Already have the diagram as Mermaid? Paste it — dashmotion turns a static `flowchart`/`graph` or `stateDiagram-v2` source into the same **moving** diagram, no redrawing. Topology and labels are kept exactly; only the layout and colors are recomputed.

````
Use dashmotion to animate this mermaid diagram:

```mermaid
flowchart TB
    A[Receive ticket] --> B{Severity?}
    B -->|P1| C[Page on-call]
    B -->|P2| D[Create incident]
    C --> E[Mitigate]
    D --> E
```
````

…becomes a moving flowchart — dashed connectors stream from `Receive ticket` through the `Severity?` decision, fan out, and merge into `Mitigate`, with a dot riding the path:

![A Mermaid flowchart converted into an animated dashmotion diagram](https://github.com/csthink/dashmotion/raw/main/examples/images/mermaid-demo.gif)

What to expect:

- **Preserved exactly**: every node and label, every edge and edge label, subgraph containment, and edge kinds — `-->` animates, `-.->` becomes a dotted async edge, `==>` marks the main path and gets the traveling dot.
- **Recomputed by design**: layout (always top-down — `LR` sources are re-laid out; structure is preserved, geometry is not) and colors (`classDef`/`style`/`linkStyle` are replaced by dashmotion's semantic palette).
- Subgraphs that name system components (namespaces, VPCs, tiers) route to architecture mode with boundaries and request journeys; plain process subgraphs stay in flow mode.
- Other mermaid types (sequence, class, ER, gantt) aren't supported — dashmotion says so instead of guessing a lossy conversion.

## Why not just a GIF?

| | GIF | Dashmotion (SVG/CSS) |
|---|---|---|
| File size | MBs | KBs |
| Sharpness | fixed resolution | vector, infinite zoom |
| Editable | re-render everything | ask Claude to change one box |
| Loop | frame-perfect work | free |
| Convert to GIF later | — | one command (`timecut`) or screen-record |

## Accessibility

All CSS animation is gated behind `@media (prefers-reduced-motion: no-preference)`; SMIL dots are removed by script under reduced motion; every diagram ships a visible pause/play toggle and `role="img"` + `<title>`/`<desc>`.

## FAQ

**Can I install this alongside [architecture-diagram-generator](https://github.com/Cocoon-AI/architecture-diagram-generator)?**
Yes — tested side by side. Animation intent ("make the request path move") routes to dashmotion; plain static architecture requests stay with Cocoon's skill. No file conflicts.

## How it works, and more

The animation technique, the deterministic layout engine, the repo layout, and exporting to GIF/MP4 are in **[docs/how-it-works.md](https://github.com/csthink/dashmotion/blob/main/docs/how-it-works.md)**. Version history is in **[CHANGELOG.md](https://github.com/csthink/dashmotion/blob/main/CHANGELOG.md)**.

## Credits

Skill packaging pattern and the static architecture design system build on [Cocoon-AI/architecture-diagram-generator](https://github.com/Cocoon-AI/architecture-diagram-generator) (MIT). Visual style inspired by the workflow animations on [diagrid.io](https://www.diagrid.io/catalyst).

## License

MIT
