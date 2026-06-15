# Flow Mode — Layout Rules

For flowcharts, workflows, pipelines, state machines: directed top-down flow on a central spine.

> The arithmetic below is implemented by `scripts/layout.py` (SKILL.md Step 5) — you author a semantic graph JSON and transcribe the geometry it returns, rather than computing these numbers by hand. Read this for the color/shape style layer, to author clean input, and as the recipe for the no-`python3` fallback.

## Color system (monochrome circuitry)

| Element | Value |
|---|---|
| Node fill | `rgba(16, 185, 129, 0.04)` |
| Node stroke | `#10b981` 1px; START/END pills `#34d399` 1.5px |
| Connector stroke | `#10b981` 1px, opacity 0.85 |
| Traveling dot | `#34d399` |

Monochrome green is the default. If the user wants semantics, allow at most ONE secondary hue: amber `#fbbf24` for timers/waits, or violet `#a78bfa` for external events. More than two hues kills the circuitry aesthetic.

## Node shapes

In the graph JSON, write `shape` **only** for pills and decisions. **Do NOT write `"shape": "step"` — leave `shape` off every step node.** `step` is exactly what the engine renders when `shape` is absent, so writing it changes nothing and only wastes output tokens. Pill and decision are *not* inferable from edge structure (a node with no incoming or outgoing edge is *not* assumed to be a pill — many flows open and close on a step), so those two must be explicit.

- **START / END**: pill, width 110–130, height 40, uppercase label. **Write `shape: "pill"`.**
- **Step / Activity**: rounded rect `rx="8"`, height 44, width = `max(label_chars × 8.5 + 32, 110)`. **Omit `shape` entirely — never write `"shape": "step"`.**
- **Decision**: same rect, dashed border (`stroke-dasharray="4 3"`, the node border itself is NOT animated), yes/no labels placed beside the outgoing connectors in 10px `#64748b`. **Set `shape: "decision"` explicitly — a branch node with `shape` omitted silently renders as a plain step, losing its yes/no semantics.**
- **Wait / Timer / External**: rect in the secondary hue if semantic coloring is on.

## Layout arithmetic

**Vertical rhythm.** Main spine stacks top-down on one center x. Gap from node bottom to next node top: **56px minimum** (connector + arrowhead + 10px air).

**Fan-out (parallel branches) — the branch bar pattern.** One horizontal rail, then vertical drops:

```
Source bottom: (cx, y0)
Rail:          y_rail = y0 + 28
Branch tops:   y1 = y_rail + 24
Per branch i:  d="M cx y0 V y_rail H bx_i V (y1 - 4)"   ← marker-end on each
```

Each branch is a **separate** `<path>` sharing the first segment — this makes the dash animation flow outward from the source into every branch simultaneously.

**Fan-in (merge)** is the mirror: each source gets its own path down to a shared rail then into the target. `marker-end` on only ONE of the merging paths — they share the final segment and stacked arrowheads smudge.

**Horizontal packing.** N branches of width w with 30px gaps: total = N·w + (N−1)·30. If total > viewBox_width − 80, shrink boxes or wrap to two rows. Boxes never overlap; verify left.x + left.w + 20 ≤ right.x for every same-row pair.

**Loops/retries.** Don't route a long return arrow up the whole diagram. Use a short curved path exiting the node's side and re-entering above it, or a `↻ retries` sublabel. Return paths are dashed but NOT dot-carrying.

## Dot placement priorities

1. The first connector out of START (establishes direction immediately)
2. Fan-out branches (staggered `begin` so they leave the rail at different times)
3. The merge into END

Skip dots on plain mid-spine hops — the dash animation already covers them.