# Mermaid Input — Conversion Rules

When the request contains Mermaid source (a ```mermaid fenced block, a `.mmd` file, or pasted code), treat it as a pre-parsed Step 5.1 result: it already declares the nodes, edges, labels, and containment. Your job is a **faithful translation into dashmotion's existing modes** — not a visual imitation of mermaid's renderer. Everything else in SKILL.md and the mode references applies unchanged.

## Supported types & routing

| Mermaid header | Handling |
|---|---|
| `flowchart` / `graph` (any direction suffix) | Supported. Mode per SKILL.md Step 1: **Flow** by default; **Architecture** when subgraphs/nodes name system components, deployment zones, namespaces, VPCs, tiers |
| `stateDiagram-v2` / `stateDiagram` | Supported → Flow mode (it's a state machine) |
| anything else (`sequenceDiagram`, `classDiagram`, `erDiagram`, `gantt`, …) | **Not supported.** Say so plainly; offer to (a) re-express as a flowchart, or (b) work from a natural-language description. Never guess a lossy conversion silently |

Mermaid is syntax, not semantics — the Step 1 mode routing question ("what happens" vs "what the system is made of") still decides the mode.

## Direction: always re-layout

Mermaid layout direction (`TB`/`TD`/`BT`/`LR`/`RL`, including per-subgraph `direction`) is **ignored**. dashmotion always re-lays out top-down using the mode reference's arithmetic. Topology is preserved — geometry is not. If the source declared `LR`/`RL`/`BT`, tell the user once: "re-laid out top-down; structure and labels preserved." Edge arrows keep their source→target meaning regardless of layout direction.

## Node shape mapping (flowchart)

| Mermaid | dashmotion |
|---|---|
| `A[text]`, `A(text)`, `A[[text]]`, `A{{text}}`, `A[/text/]`, `A[\text\]`, `A>text]` | Step (Flow) / typed component (Architecture) |
| `A([text])`, `A((text))` | START/END pill **if** the node has in-degree 0 or out-degree 0; otherwise a plain step |
| `A{text}` | Decision (dashed border, branch labels beside outgoing connectors) — Flow mode |
| `A[(text)]` | Flow: plain step. Architecture: database-typed component (violet) |

**Never invent or drop nodes.** If a flowchart has no explicit start/end shape, do NOT add synthetic START/END pills — style the in-degree-0 node as the spine's entry (pill shape allowed, label verbatim from source).

In Architecture mode, type each component from its label like you would for a prose description (PostgreSQL → database, Kafka → message bus, NGINX → cloud infra, …).

## Edge mapping

Expand chains (`A --> B --> C`) and ampersands (`A --> B & C`) into individual edges first, then map:

| Mermaid | dashmotion |
|---|---|
| `-->` | Animated solid connector (`class="flow"`, marker-end) |
| `---` (no arrowhead) | Static line: no marker, no animation |
| `-.->` | Async edge: `stroke-dasharray="2 4"` **with its own keyframes** (offset delta a multiple of 6); orange dots in Architecture mode |
| `==>` | Main path: 1.5px stroke, and this edge gets dot priority |
| `-->|label|` or `-- label -->` | Connector label beside the line, 10px `#64748b`, in clear space |
| `<-->` | Single static line with `marker-start` + `marker-end`, NOT animated (flow direction is ambiguous) |

## stateDiagram-v2 mapping

- `[*] --> X` → START pill → X; `X --> [*]` → X → END pill.
- `X --> Y : label` → connector label beside the line.
- Self-loop `X --> X` → flow-mode loop rule: short side arc or `↻ label` sublabel — never a full-height return line.
- Composite states → group rect (see below); `<<choice>>` → decision node.

## subgraph mapping

- **Architecture mode**: subgraph → boundary. Outer/cloud/region-ish names → amber region (`8 4`); names containing subnet/private/security/zone → rose (`4 4`). Nesting max 2 levels (existing rule); if the source nests deeper, flatten the innermost level into component sublabels and tell the user.
- **Flow mode**: subgraph → a static group rect behind its nodes: stroke `#10b981` at opacity 0.35, `stroke-dasharray="8 4"`, `rx="12"`, transparent fill, label top-left inside in 10px `#64748b`, ≥20px padding. Groups never animate.

## Fidelity contract

- **Preserved exactly**: node set + label text verbatim (incl. unicode), edge set + directions + edge labels, containment, edge kind (sync/async/emphasis/no-arrow).
- **Recomputed**: all geometry (always top-down), sizes, and colors. Mermaid styling (`classDef`, `class`, `:::`, `style`, `linkStyle`, themes, icons) is **dropped** — dashmotion's palette takes over — with ONE exception: preserve a classDef's distinction ONLY when the source makes its semantics explicit — it pairs the classes with a legend, or the class names clearly encode lifecycle/version stages (`v1x`, `v2`, `beta`, `deprecated`, `planned`). Then render it as a stroke variant (color + dash pattern) on the affected components and add matching legend entries. A lone emphasis class without a legend (`hot`, `important`, a color name) is decoration — drop it. Either way, mention it once **in your chat reply, never inside the artifact** — the delivered HTML must not contain mermaid directive names or syntax. `click` handlers and `%%` comments are dropped silently.
- **Legend subgraphs**: a subgraph that is itself a hand-drawn legend (named 图例/Legend/Key, containing only swatch-explainer nodes) is NOT rendered as a boundary — merge its entries into dashmotion's own legend. The subgraph title may be omitted; every entry must appear **verbatim** — keep each entry's exact text, don't reword it or merge it with a boundary title (the Step 6 fidelity check compares them exactly).
- The only permitted edge-count reduction: a loop/self-loop edge rendered as a `↻` sublabel instead of a drawn path.

## Label & escaping hygiene

- Strip mermaid's quoting (`"…"`) and entity codes, then XML-escape for SVG: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`. A literal `<word>` in a label must arrive as `&lt;word&gt;`, never as a tag.
- **Never copy mermaid source into SVG/HTML comments** — edge syntax contains `--`, which terminates an XML comment early and corrupts the document.
- `<br/>` in a label → `<tspan>` line break. Labels longer than ~28 chars → wrap to two tspan lines (width formula uses the longest line); never truncate or paraphrase.

## Step 6 additions for mermaid input

During the structural self-check, also verify with written-out arithmetic:

1. **Node count**: list the source's node IDs; count of node rects/pills in the SVG must equal it (plus START/END pills only when the source had `[*]`).
2. **Edge count**: count of connector paths + `↻`-rendered loops must equal the source's edge count (after expanding chains and `&`).
3. **Labels verbatim**: every node and edge label string from the source appears in the SVG text (post-escaping).
