#!/usr/bin/env python3
"""layout.py — deterministic geometry for dashmotion diagrams (pure stdlib).

The model produces a *semantic* graph JSON (nodes/types/edges/groups/journeys +
tier hints); this script does the mechanical placement arithmetic that the mode
references spell out (row packing, branch gaps, boundary padding, orthogonal
rail/lane routing) and emits geometry — so the model stops hand-computing 35
components' coordinates in one long pre-write thinking stretch (the ~90% cost
sink that plan A targets). Aesthetic judgement (which nodes are emphasized, tier
assignment, journey choice) stays in the model and arrives as JSON hints.

  python3 layout.py graph.json                     # geometry JSON -> stdout
  python3 layout.py graph.json --emit-svg out.html # debug HTML (check_diagram)

The --emit-svg path renders the geometry to a full self-contained HTML so the
bundled check_diagram.py can verify it (C1-C8). In production the model consumes
the geometry JSON and transcribes it into the mode template, keeping final say
over labels/colors/copy.

Design decisions (frozen by the plan-A handoff, not re-invented here):
  * Shared layered engine. Both modes lay out top-down by layer. Flow computes
    layers by longest-path on the forward DAG (back edges found by DFS); arch
    uses the model-supplied `tier`.
  * C2-safe routing. Adjacent-layer edges use orthogonal L routes whose
    horizontal rail sits in the inter-layer gap (no box there). Edges that span
    >1 layer, or run sideways/upward, route through a vertical lane placed
    OUTSIDE every box (margins) — the lane can never cross a node. check_diagram
    excludes containers (boundaries) from its box set, so lanes/rails crossing a
    boundary rect is fine.
  * Loops. Flow back/self edges render as a `↻ <label>` annotation beside the
    source (the references' sublabel option; also the only edge-count reduction
    check_fidelity permits) — never a drawn return path. The label is emitted as
    its own <text> so it survives verbatim.
  * Boundaries. check_diagram only penalises PARTIAL rect overlap (C1); full
    containment is legal. Boundary boxes are computed bottom-up (innermost
    first) as member bbox + padding, and each subgroup owns its own tiers, so
    every boundary either fully contains or is disjoint from every rect.
  * Positivity. Layout runs in arbitrary coordinates, then a single translate
    pass shifts everything to >=0 and sets viewBox 0 0 W H (C4). Edges are kept
    as orthogonal point lists and serialized to M/V/H/L after translation.

Known limitations (documented, NOT worked around by loosening the checker):
  * Within-layer ordering is group-contiguous + input order, not crossing-
    minimized (no barycenter sweep). Wide fan structures may cross visually;
    never through a box.
  * Layers are centered, not barycenter-aligned to parents.
  * A subgroup is assumed to own its tiers (no loose sibling sharing a tier);
    the graph JSON is authored that way. Mixed tiers fall back to side-by-side
    bands and can look sparse.
  * Message-bus components render as a 36px-tall typed component (fidelity needs
    node-sized rects), not the references' 22px in-gap strip.
  * Curves are not produced; all routing is orthogonal.
"""

import json
import sys

# ----------------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------------

CENTER = 520.0          # provisional spine x; normalized away at the end
MARGIN = 34.0           # outer padding after translate
BOTTOM_PAD = 44.0       # extra below lowest element (SKILL: H = lowest + ~50)

# flow
STEP_H = 44.0
PILL_H = 40.0
FLOW_VGAP = 56.0        # node bottom -> next node top
FLOW_HGAP = 30.0
FLOW_MAXW = 190.0
FLOW_NODE_FILL = "rgba(16,185,129,0.04)"
FLOW_NODE_STROKE = "#10b981"
FLOW_PILL_FILL = "rgba(52,211,153,0.06)"
FLOW_PILL_STROKE = "#34d399"
FLOW_CONN = "#10b981"
FLOW_DOT = "#34d399"

# arch
COMP_H = 56.0
BUS_H = 36.0
ARCH_VGAP = 56.0
ARCH_HGAP = 40.0
ARCH_MAXW = 200.0
BOUND_PAD = 20.0
ARCH_CONN = "#64748b"
ARCH_ASYNC = "#fb923c"
ARCH_AUTH = "#fb7185"
ARCH_DOT = "#22d3ee"

TYPE_STYLE = {  # type -> (fill, stroke, legend label)
    "frontend": ("rgba(8,51,68,0.45)", "#22d3ee", "frontend"),
    "backend":  ("rgba(6,78,59,0.45)", "#34d399", "service"),
    "database": ("rgba(76,29,149,0.45)", "#a78bfa", "data"),
    "cloud":    ("rgba(120,53,15,0.35)", "#fbbf24", "cloud infra"),
    "security": ("rgba(136,19,55,0.45)", "#fb7185", "security"),
    "bus":      ("rgba(154,52,18,0.35)", "#fb923c", "message bus"),
    "external": ("rgba(30,41,59,0.5)", "#94a3b8", "external"),
}

# lanes
LANE_GAP = 30.0         # first lane this far outside content
LANE_STEP = 16.0        # spacing between stacked lanes
RAIL_IN = 24.0          # rail offset into the inter-layer gap

EDGE_SHORT = 4.0        # connector stops this far short of the target border


# ----------------------------------------------------------------------------
# text
# ----------------------------------------------------------------------------

def char_w(c):
    o = ord(c)
    if o >= 0x2E80:            # CJK / wide
        return 14.0
    if c in "iljt.,:;'|! ":
        return 5.0
    if c in "mwMW":
        return 11.0
    return 8.0


def text_w(s):
    return sum(char_w(c) for c in s)


def wrap(label, maxw):
    """Wrap to at most two lines; width keyed off the longest line."""
    if text_w(label) <= maxw:
        return [label]
    words = label.split(" ")
    if len(words) > 1:
        best, line1 = None, ""
        for i in range(1, len(words)):
            a = " ".join(words[:i])
            b = " ".join(words[i:])
            score = max(text_w(a), text_w(b))
            if best is None or score < best:
                best, line1, line2 = score, a, b
        return [line1, line2]
    # single long token (e.g. CJK run): split near the middle
    n = len(label)
    cut = n // 2
    return [label[:cut], label[cut:]]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ----------------------------------------------------------------------------
# model
# ----------------------------------------------------------------------------

class Node:
    def __init__(self, d):
        self.id = d["id"]
        self.label = d.get("label", d["id"])
        self.sublabel = d.get("sublabel")
        self.shape = d.get("shape")          # flow: pill|step|decision
        self.type = d.get("type")            # arch: frontend|...
        self.tier = d.get("tier")
        self.group = d.get("group")
        self.sem_stroke = d.get("semStroke")  # semantic classDef retention
        self.sem_dash = d.get("semDash")
        self.loop_notes = []                 # ↻ annotations attached here
        self.layer = 0
        self.x = self.y = 0.0
        self.w = self.h = 0.0
        self.lines = [self.label]

    @property
    def cx(self):
        return self.x + self.w / 2.0

    @property
    def cy(self):
        return self.y + self.h / 2.0

    @property
    def x2(self):
        return self.x + self.w

    @property
    def y2(self):
        return self.y + self.h


class Edge:
    def __init__(self, d):
        self.src = d["from"]
        self.dst = d["to"]
        self.kind = d.get("kind", "sync")
        self.label = d.get("label")
        self.pts = []                        # orthogonal polyline
        self.is_loop = False
        self.label_pos = None


class Group:
    def __init__(self, d):
        self.id = d["id"]
        self.label = d.get("label", d["id"])
        self.kind = d.get("kind", "region")  # region|subnet
        self.parent = d.get("parent")
        self.box = None                      # (x, y, w, h)


# ----------------------------------------------------------------------------
# layering
# ----------------------------------------------------------------------------

def find_back_edges(node_ids, edges):
    adj = {n: [] for n in node_ids}
    for i, e in enumerate(edges):
        if e.src in adj:
            adj[e.src].append((e.dst, i))
    color = {}
    back = set()
    sys.setrecursionlimit(10000)

    def dfs(u):
        color[u] = 1
        for v, i in adj[u]:
            if v == u:
                back.add(i)
                continue
            c = color.get(v, 0)
            if c == 1:
                back.add(i)
            elif c == 0:
                dfs(v)
        color[u] = 2

    for n in node_ids:
        if color.get(n, 0) == 0:
            dfs(n)
    return back


def longest_path_layers(node_ids, fwd):
    succ = {n: [] for n in node_ids}
    indeg = {n: 0 for n in node_ids}
    for e in fwd:
        succ[e.src].append(e.dst)
        indeg[e.dst] += 1
    level = {n: 0 for n in node_ids}
    queue = [n for n in node_ids if indeg[n] == 0]
    qi = 0
    while qi < len(queue):
        u = queue[qi]
        qi += 1
        for v in succ[u]:
            if level[u] + 1 > level[v]:
                level[v] = level[u] + 1
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return level


# ----------------------------------------------------------------------------
# layout
# ----------------------------------------------------------------------------

class Layout:
    def __init__(self, graph):
        self.mode = graph.get("mode", "flow")
        self.title = graph.get("title", "diagram")
        self.nodes = [Node(n) for n in graph["nodes"]]
        self.by_id = {n.id: n for n in self.nodes}
        self.edges = [Edge(e) for e in graph.get("edges", [])]
        self.groups = [Group(g) for g in graph.get("groups", [])]
        self.group_by_id = {g.id: g for g in self.groups}
        self.journeys = graph.get("journeys", [])
        self.legend_extra = graph.get("legendExtra", [])
        self.input_index = {n.id: i for i, n in enumerate(self.nodes)}
        self.notes = []
        self.lanes_r = 0
        self.lanes_l = 0
        self.lane_base_r = 0.0
        self.lane_base_l = 0.0

    # -- sizing --
    def size_nodes(self):
        maxw = FLOW_MAXW if self.mode == "flow" else ARCH_MAXW
        for n in self.nodes:
            n.lines = wrap(n.label, maxw)
            lw = max(text_w(l) for l in n.lines)
            if self.mode == "flow":
                if n.shape == "pill":
                    n.w = min(max(text_w(n.label) + 40, 110), 150)
                    n.h = PILL_H
                else:
                    n.w = max(lw + 32, 110)
                    n.h = STEP_H if len(n.lines) == 1 else STEP_H + 14
            else:
                base = max(lw + 36, 130)
                if n.sublabel:
                    base = max(base, text_w(n.sublabel) + 36)
                n.w = base
                if n.type == "bus":
                    n.h = BUS_H
                else:
                    n.h = COMP_H if len(n.lines) == 1 else COMP_H + 16

    # -- layers --
    def assign_layers(self):
        ids = [n.id for n in self.nodes]
        if all(n.tier is not None for n in self.nodes):
            for n in self.nodes:
                n.layer = int(n.tier)
            self.back = set()
        else:
            back = find_back_edges(ids, self.edges)
            fwd = [e for i, e in enumerate(self.edges) if i not in back]
            level = longest_path_layers(ids, fwd)
            for n in self.nodes:
                n.layer = level[n.id]
            self.back = back
        # mark loop edges (flow back/self) and attach annotations
        for i, e in enumerate(self.edges):
            if self.mode == "flow" and (i in self.back):
                e.is_loop = True
                self.by_id[e.src].loop_notes.append(e.label or "")

    def _group_chain(self, n):
        chain = []
        g = self.group_by_id.get(n.group) if n.group else None
        while g is not None:
            chain.append(self.input_index.get(g.id, 0))
            chain.append(g.id)
            g = self.group_by_id.get(g.parent) if g.parent else None
        chain.reverse()
        return tuple(chain)

    def _group_set(self, n):
        s = set()
        g = self.group_by_id.get(n.group) if n.group else None
        while g is not None:
            s.add(g.id)
            g = self.group_by_id.get(g.parent) if g.parent else None
        return s

    # -- placement --
    def place(self):
        layers = {}
        for n in self.nodes:
            layers.setdefault(n.layer, []).append(n)
        vgap = FLOW_VGAP if self.mode == "flow" else ARCH_VGAP
        hgap = FLOW_HGAP if self.mode == "flow" else ARCH_HGAP
        order = sorted(layers)
        active = {}
        for L in order:
            s = set()
            for n in layers[L]:
                s |= self._group_set(n)
            active[L] = s

        y = 0.0
        for idx, L in enumerate(order):
            row = layers[L]
            row.sort(key=lambda n: (self._group_chain(n), self.input_index[n.id]))
            h = max(n.h for n in row)
            total = sum(n.w for n in row) + hgap * (len(row) - 1)
            x = CENTER - total / 2.0
            for n in row:
                n.x = x
                n.y = y + (h - n.h) / 2.0
                x += n.w + hgap
            # gap to next layer: widen where boundaries open/close so nested
            # boundary padding never makes two boundary rects overlap (C1)
            gap = vgap
            if idx + 1 < len(order):
                nxt = active[order[idx + 1]]
                closing = active[L] - nxt
                opening = nxt - active[L]
                gap = max(vgap, BOUND_PAD * (len(closing) + len(opening)) + 8)
            y += h + gap

    # -- group boxes (bottom-up) --
    def build_groups(self):
        def depth(g):
            d = 0
            while g.parent and g.parent in self.group_by_id:
                g = self.group_by_id[g.parent]
                d += 1
            return d
        for g in sorted(self.groups, key=depth, reverse=True):
            members = [n for n in self.nodes if n.group == g.id]
            child_boxes = [c.box for c in self.groups
                           if c.parent == g.id and c.box]
            xs, ys, xs2, ys2 = [], [], [], []
            for n in members:
                xs.append(n.x); ys.append(n.y); xs2.append(n.x2); ys2.append(n.y2)
            for (bx, by, bw, bh) in child_boxes:
                xs.append(bx); ys.append(by); xs2.append(bx + bw); ys2.append(by + bh)
            if not xs:
                continue
            x = min(xs) - BOUND_PAD
            yy = min(ys) - BOUND_PAD
            w = max(xs2) + BOUND_PAD - x
            hh = max(ys2) + BOUND_PAD - yy
            g.box = (x, yy, w, hh)

    # -- routing --
    def _content_bounds(self):
        xs, xs2 = [], []
        for n in self.nodes:
            xs.append(n.x); xs2.append(n.x2)
        for g in self.groups:
            if g.box:
                xs.append(g.box[0]); xs2.append(g.box[0] + g.box[2])
        return min(xs), max(xs2)

    def route(self):
        lo, hi = self._content_bounds()
        self.lane_base_r = hi + LANE_GAP
        self.lane_base_l = lo - LANE_GAP
        for e in self.edges:
            if e.is_loop:
                continue
            self._route_edge(e)

    def _layer_gap_y(self, upper_layer_bottom, target_top):
        return (upper_layer_bottom + target_top) / 2.0

    def _column_clear(self, x, y0, y1, exclude):
        """No node box straddles the vertical x within (y0, y1)."""
        lo, hi = (y0, y1) if y0 <= y1 else (y1, y0)
        for n in self.nodes:
            if n.id in exclude:
                continue
            if n.x - 3 < x < n.x2 + 3 and not (n.y2 <= lo or n.y >= hi):
                return False
        return True

    def _route_edge(self, e):
        u = self.by_id[e.src]
        v = self.by_id[e.dst]
        ux, uy = u.cx, u.y2
        vx, vtop = v.cx, v.y - EDGE_SHORT
        # exit from source bottom; if target is above (upward) start from top
        upward = v.layer < u.layer
        same = v.layer == u.layer
        if upward:
            ux, uy = u.cx, u.y
            vx, vtop = v.cx, v.y2 + EDGE_SHORT
        if (not upward) and (not same) and v.layer - u.layer == 1:
            if abs(ux - vx) < 0.6:
                e.pts = [(ux, uy), (vx, vtop)]
            else:
                midy = self._layer_gap_y(u.y2, v.y)
                e.pts = [(ux, uy), (ux, midy), (vx, midy), (vx, vtop)]
            self._set_label_pos(e, u, v)
            return
        # multi-layer downward: prefer a straight column drop (source's own
        # column, then jog above the target) when that column is clear of boxes
        # — avoids the boxy far-lane detour. Fall back to a lane only if blocked.
        if (not upward) and (not same):
            rail_b = v.y - RAIL_IN
            if self._column_clear(ux, u.y2, rail_b, {u.id, v.id}):
                e.pts = [(ux, uy), (ux, rail_b), (vx, rail_b), (vx, vtop)]
                self._set_label_pos(e, u, v)
                return
            rail_a = u.y2 + RAIL_IN
            if self._column_clear(vx, rail_a, vtop, {u.id, v.id}):
                e.pts = [(ux, uy), (ux, rail_a), (vx, rail_a), (vx, vtop)]
                self._set_label_pos(e, u, v)
                return
        if same:
            # dip just below the row and come back up into the target's bottom
            ya = max(u.y2, v.y2) + RAIL_IN
            e.pts = [(u.cx, u.y2), (u.cx, ya), (v.cx, ya),
                     (v.cx, v.y2 + EDGE_SHORT)]
            self._set_label_pos(e, u, v)
            return
        # sideways / upward / blocked -> vertical lane outside all boxes
        right = u.cx >= CENTER
        if right:
            self.lanes_r += 1
            lane = self.lane_base_r + (self.lanes_r - 1) * LANE_STEP
        else:
            self.lanes_l += 1
            lane = self.lane_base_l - (self.lanes_l - 1) * LANE_STEP
        rail_a = uy + (RAIL_IN if not upward else -RAIL_IN)
        rail_b = vtop + (-RAIL_IN if not upward else RAIL_IN)
        e.pts = [(ux, uy), (ux, rail_a), (lane, rail_a),
                 (lane, rail_b), (vx, rail_b), (vx, vtop)]
        self._set_label_pos(e, u, v)

    def _set_label_pos(self, e, u, v):
        if not e.label or len(e.pts) < 2:
            return
        # midpoint of the edge's own polyline (by arc length), nudged aside so
        # fan-out branch labels never collide at the shared source point
        total = _poly_len(e.pts)
        half = total / 2.0
        acc = 0.0
        for (ax, ay), (bx, by) in zip(e.pts, e.pts[1:]):
            seg = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            if acc + seg >= half and seg > 0:
                t = (half - acc) / seg
                e.label_pos = (ax + (bx - ax) * t + 8, ay + (by - ay) * t - 3)
                return
            acc += seg
        e.label_pos = (e.pts[0][0] + 8, e.pts[0][1])

    # -- translate to positive & viewbox --
    def normalize(self):
        xs, ys = [], []

        def acc(x, y):
            xs.append(x); ys.append(y)

        for n in self.nodes:
            acc(n.x, n.y); acc(n.x2, n.y2)
            if n.loop_notes:  # ↻ glyph + label sits to the node's right
                wid = max((text_w(s) for s in n.loop_notes), default=0.0)
                acc(n.x2 + 8 + 14 + wid + 8, n.cy)
                acc(n.x2, n.cy + 15 * len(n.loop_notes))
        for g in self.groups:
            if g.box:
                acc(g.box[0], g.box[1])
                acc(g.box[0] + g.box[2], g.box[1] + g.box[3])
        for e in self.edges:
            for (x, y) in e.pts:
                acc(x, y)
        minx, miny = min(xs), min(ys)
        dx, dy = -minx + MARGIN, -miny + MARGIN
        for n in self.nodes:
            n.x += dx; n.y += dy
        for g in self.groups:
            if g.box:
                g.box = (g.box[0] + dx, g.box[1] + dy, g.box[2], g.box[3])
        for e in self.edges:
            e.pts = [(x + dx, y + dy) for (x, y) in e.pts]
            if e.label_pos:
                e.label_pos = (e.label_pos[0] + dx, e.label_pos[1] + dy)
        # legend / cards live below; computed in render. provisional bounds:
        self.maxx = max(x + dx for x in xs)
        self.maxy = max(y + dy for y in ys)

    def run(self):
        self.size_nodes()
        self.assign_layers()
        self.place()
        self.build_groups()
        self.route()
        self.normalize()


# ----------------------------------------------------------------------------
# path serialization
# ----------------------------------------------------------------------------

def fmt(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def to_d(pts):
    if not pts:
        return ""
    out = [f"M{fmt(pts[0][0])} {fmt(pts[0][1])}"]
    px, py = pts[0]
    for (x, y) in pts[1:]:
        if abs(x - px) < 0.05:
            out.append(f"V{fmt(y)}")
        elif abs(y - py) < 0.05:
            out.append(f"H{fmt(x)}")
        else:
            out.append(f"L{fmt(x)} {fmt(y)}")
        px, py = x, y
    return " ".join(out)


# ----------------------------------------------------------------------------
# geometry dict (the contract the model consumes)
# ----------------------------------------------------------------------------

def geometry(lo):
    nodes = {}
    for n in lo.nodes:
        nodes[n.id] = {
            "x": round(n.x, 1), "y": round(n.y, 1),
            "w": round(n.w, 1), "h": round(n.h, 1),
            "shape": n.shape, "type": n.type,
            "labelLines": n.lines, "sublabel": n.sublabel,
            "loopNotes": n.loop_notes,
        }
    edges = []
    edge_d = {}
    for e in lo.edges:
        if e.is_loop:
            edges.append({"from": e.src, "to": e.dst, "kind": e.kind,
                          "label": e.label, "loop": True})
            continue
        d = to_d(e.pts)
        edge_d[(e.src, e.dst)] = d
        edges.append({"from": e.src, "to": e.dst, "kind": e.kind,
                      "d": d, "marker": e.kind != "static",
                      "label": e.label,
                      "labelPos": [round(e.label_pos[0], 1),
                                   round(e.label_pos[1], 1)] if e.label_pos else None})
    groups = {}
    for g in lo.groups:
        if g.box:
            groups[g.id] = {"label": g.label, "kind": g.kind,
                            "parent": g.parent,
                            "box": [round(v, 1) for v in g.box]}
    journeys = []
    for j in lo.journeys:
        hops = []
        for (a, b) in j.get("hops", []):
            d = edge_d.get((a, b))
            if d:
                hops.append({"from": a, "to": b, "d": d})
        if hops:
            journeys.append({"color": j.get("color"), "hops": hops})
    return {
        "mode": lo.mode,
        "title": lo.title,
        "nodes": nodes,
        "edges": edges,
        "groups": groups,
        "journeys": journeys,
        "notes": lo.notes,
        "width": round(lo.maxx + MARGIN, 1),
        "height": round(lo.maxy + BOTTOM_PAD, 1),
    }


# ----------------------------------------------------------------------------
# debug SVG renderer (geometry -> full HTML for check_diagram)
# ----------------------------------------------------------------------------

CSS_COMMON = """
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'JetBrains Mono', monospace; background: #020617;
         min-height: 100vh; padding: 2rem; color: #e2e8f0; }
  .container { max-width: %dpx; margin: 0 auto; }
  .header { display: flex; align-items: center; gap: 12px; margin-bottom: 0.4rem; }
  .pulse-dot { width: 10px; height: 10px; border-radius: 50%%; background: %s; }
  h1 { font-size: 1.25rem; font-weight: 600; letter-spacing: -0.02em; }
  .subtitle { color: #64748b; font-size: 0.8rem; margin-bottom: 1.5rem; }
  .diagram-card { border: 1px solid #1e293b; border-radius: 12px; position: relative;
    background: repeating-linear-gradient(0deg, #0f1b33 0 0.5px, transparent 0.5px 40px),
      repeating-linear-gradient(90deg, #0f1b33 0 0.5px, transparent 0.5px 40px), #030a1c;
    padding: 1.25rem 1rem; }
  .pause-btn { position: absolute; top: 12px; right: 12px; z-index: 2; background: transparent;
    border: 1px solid #1e293b; color: #64748b; border-radius: 6px; padding: 4px 10px;
    font: inherit; font-size: 11px; cursor: pointer; }
  .pause-btn:hover { color: #e2e8f0; border-color: #334155; }
  .footer { color: #475569; font-size: 0.7rem; margin-top: 1rem; }
  .flow { stroke-dasharray: 5 5; }
  .flow-async { stroke-dasharray: 2 4; }
  .flow-auth { stroke-dasharray: 4 4; }
  @media (prefers-reduced-motion: no-preference) {
    .flow { animation: dashmove 0.75s linear infinite; }
    .flow-async { animation: dashasync 0.9s linear infinite; }
    .flow-auth { animation: dashauth 1.2s linear infinite; }
    .pulse-dot { animation: pulse 2s ease-in-out infinite; }
  }
  @keyframes dashmove { to { stroke-dashoffset: -10; } }
  @keyframes dashasync { to { stroke-dashoffset: -12; } }
  @keyframes dashauth { to { stroke-dashoffset: -8; } }
  @keyframes pulse { 0%%, 100%% { opacity: 1; } 50%% { opacity: 0.4; } }
  body.paused .flow, body.paused .flow-async, body.paused .flow-auth,
  body.paused .pulse-dot { animation-play-state: paused; }
"""

CSS_CARDS = """
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1rem; margin-top: 1.25rem; }
  .card { border: 1px solid #1e293b; border-radius: 10px; background: #060d20; padding: 1rem 1.1rem; }
  .card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 0.6rem; }
  .card-dot { width: 8px; height: 8px; border-radius: 50%; }
  .card-dot.cyan { background: #22d3ee; } .card-dot.violet { background: #a78bfa; }
  .card-dot.rose { background: #fb7185; }
  .card h3 { font-size: 0.8rem; font-weight: 600; }
  .card ul { list-style: none; } .card li { font-size: 0.72rem; color: #94a3b8; line-height: 1.7; }
"""

SCRIPT = """
<script>
(function () {
  var svg = document.getElementById('flowsvg');
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('.dot').forEach(function (d) { d.remove(); });
    var b = document.getElementById('pauseBtn'); if (b) b.remove(); return;
  }
  var btn = document.getElementById('pauseBtn'); var paused = false;
  btn.addEventListener('click', function () {
    paused = !paused; document.body.classList.toggle('paused', paused);
    paused ? svg.pauseAnimations() : svg.unpauseAnimations();
    btn.textContent = paused ? '▶ play' : '⏸ pause';
    btn.setAttribute('aria-pressed', String(paused));
  });
})();
</script>
"""

MARKER = ('<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
          'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
          '<path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" '
          'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>')


def _node_text_svg(n):
    parts = []
    cx = n.cx
    if n.sublabel:  # arch component: label + sublabel
        ly = n.y + (n.h - 18) / 2 + 4
        if len(n.lines) == 1:
            parts.append(f'<text x="{fmt(cx)}" y="{fmt(ly)}" fill="#e2e8f0" '
                         f'font-size="13" font-weight="500">{esc(n.lines[0])}</text>')
        else:
            parts.append(f'<text x="{fmt(cx)}" y="{fmt(ly-7)}" fill="#e2e8f0" '
                         f'font-size="13" font-weight="500">'
                         f'<tspan x="{fmt(cx)}">{esc(n.lines[0])}</tspan>'
                         f'<tspan x="{fmt(cx)}" dy="15">{esc(n.lines[1])}</tspan></text>')
        parts.append(f'<text x="{fmt(cx)}" y="{fmt(n.y2-10)}" fill="#64748b" '
                     f'font-size="10">{esc(n.sublabel)}</text>')
    else:
        weight = "600" if n.shape == "pill" else "500"
        if len(n.lines) == 1:
            ty = n.cy + 4
            parts.append(f'<text x="{fmt(cx)}" y="{fmt(ty)}" fill="#e2e8f0" '
                         f'font-size="13" font-weight="{weight}">{esc(n.lines[0])}</text>')
        else:
            ty = n.cy - 3
            parts.append(f'<text x="{fmt(cx)}" y="{fmt(ty)}" fill="#e2e8f0" '
                         f'font-size="13" font-weight="{weight}">'
                         f'<tspan x="{fmt(cx)}">{esc(n.lines[0])}</tspan>'
                         f'<tspan x="{fmt(cx)}" dy="15">{esc(n.lines[1])}</tspan></text>')
    return "".join(parts)


def render(lo, geom):
    mode = lo.mode
    parts = []
    W = geom["width"]
    H = geom["height"]

    # boundaries (arch) first — static containers
    bound_svg = []
    legend_entries = []   # (fill, stroke, label) for swatches; None fill => dot
    used_types = []
    if mode != "flow":
        for g in lo.groups:
            if not g.box:
                continue
            x, y, w, h = g.box
            if g.kind == "subnet":
                stroke, dash, fs = "#fb7185", "4 4", 10
                rx = 8
            else:
                stroke, dash, fs = "#fbbf24", "8 4", 11
                rx = 12
            bound_svg.append(
                f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                f'rx="{rx}" fill="none" stroke="{stroke}" stroke-width="1" '
                f'stroke-dasharray="{dash}" opacity="0.6"/>')
            bound_svg.append(
                f'<text x="{fmt(x+14)}" y="{fmt(y+18)}" fill="{stroke}" '
                f'font-size="{fs}" opacity="0.9">{esc(g.label)}</text>')

    # connectors
    conn = ['<g fill="none">']
    label_svg = []
    for e in lo.edges:
        if e.is_loop:
            continue
        d = to_d(e.pts)
        if mode == "flow":
            stroke = FLOW_CONN
            width = "1.5" if e.kind == "main" else "1"
            opacity = "0.85"
        else:
            stroke = (ARCH_ASYNC if e.kind == "async"
                      else ARCH_AUTH if e.kind == "auth" else ARCH_CONN)
            width = "1.5" if e.kind == "main" else "1"
            opacity = "1"
        cls = ("flow-async" if e.kind == "async"
               else "flow-auth" if e.kind == "auth"
               else "" if e.kind == "static" else "flow")
        marker = "" if e.kind == "static" else ' marker-end="url(#arrow)"'
        clsattr = f' class="{cls}"' if cls else ""
        conn.append(f'<path{clsattr} d="{d}" stroke="{stroke}" '
                    f'stroke-width="{width}" opacity="{opacity}"{marker}/>')
        if e.label and e.label_pos:
            lx, ly = e.label_pos
            label_svg.append(f'<text x="{fmt(lx)}" y="{fmt(ly)}" fill="#64748b" '
                             f'font-size="10">{esc(e.label)}</text>')
    conn.append('</g>')

    # loop annotations
    for n in lo.nodes:
        off = 0
        for note in n.loop_notes:
            lx = n.x2 + 8
            ly = n.cy + 4 + off
            label_svg.append(f'<text x="{fmt(lx)}" y="{fmt(ly)}" fill="#64748b" '
                             f'font-size="11">↻</text>')
            if note:
                label_svg.append(f'<text x="{fmt(lx+14)}" y="{fmt(ly)}" '
                                 f'fill="#64748b" font-size="10">{esc(note)}</text>')
            off += 15

    # journeys / dots
    dot_svg = []
    dot_default = FLOW_DOT if mode == "flow" else ARCH_DOT
    edge_d = {(e.src, e.dst): to_d(e.pts) for e in lo.edges if not e.is_loop}
    edge_pts = {(e.src, e.dst): e.pts for e in lo.edges if not e.is_loop}
    for ji, j in enumerate(lo.journeys):
        color = j.get("color") or dot_default
        hops = [h for h in j.get("hops", []) if (h[0], h[1]) in edge_d]
        if not hops:
            continue
        prev_id = None
        last_id = f"j{ji}_{len(hops)-1}"
        for hi, (a, b) in enumerate(hops):
            d = edge_d[(a, b)]
            mid = f"j{ji}_{hi}"
            if hi == 0:
                begin = f"0s;{last_id}.end+0.6s"
            else:
                begin = f"{prev_id}.end+0.3s"
            dur = max(0.6, _poly_len(edge_pts[(a, b)]) / 150.0)
            dot_svg.append(
                f'<circle r="3.5" class="dot" fill="{color}">'
                f'<animateMotion id="{mid}" dur="{dur:.1f}s" begin="{begin}" '
                f'fill="freeze" path="{d}"/></circle>')
            prev_id = mid

    # nodes
    node_svg = []
    for n in lo.nodes:
        if mode == "flow":
            if n.shape == "pill":
                node_svg.append(
                    f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                    f'height="{fmt(n.h)}" rx="20" fill="{FLOW_PILL_FILL}" '
                    f'stroke="{FLOW_PILL_STROKE}" stroke-width="1.5"/>')
            elif n.shape == "decision":
                node_svg.append(
                    f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                    f'height="{fmt(n.h)}" rx="8" fill="{FLOW_NODE_FILL}" '
                    f'stroke="{FLOW_NODE_STROKE}" stroke-dasharray="4 3"/>')
            else:
                node_svg.append(
                    f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                    f'height="{fmt(n.h)}" rx="8" fill="{FLOW_NODE_FILL}" '
                    f'stroke="{FLOW_NODE_STROKE}"/>')
            node_svg.append(_node_text_svg(n))
        else:
            fill, stroke, leg = TYPE_STYLE.get(n.type or "external",
                                               TYPE_STYLE["external"])
            if leg not in [u[2] for u in used_types]:
                used_types.append((fill, stroke, leg))
            st = n.sem_stroke or stroke
            dash = f' stroke-dasharray="{n.sem_dash}"' if n.sem_dash else ""
            node_svg.append(
                f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                f'height="{fmt(n.h)}" rx="8" fill="#0b1226"/>')
            node_svg.append(
                f'<rect x="{fmt(n.x)}" y="{fmt(n.y)}" width="{fmt(n.w)}" '
                f'height="{fmt(n.h)}" rx="8" fill="{fill}" stroke="{st}" '
                f'stroke-width="1.5"{dash}/>')
            node_svg.append(_node_text_svg(n))

    # legend (arch): below everything
    legend_svg = []
    extra_h = 0
    if mode != "flow":
        ly = H - BOTTOM_PAD + 6
        lx = MARGIN
        for (fill, stroke, leg) in used_types:
            legend_svg.append(
                f'<rect x="{fmt(lx)}" y="{fmt(ly)}" width="12" height="12" rx="3" '
                f'fill="{fill}" stroke="{stroke}"/>')
            legend_svg.append(
                f'<text x="{fmt(lx+18)}" y="{fmt(ly+10)}" fill="#94a3b8" '
                f'font-size="11">{esc(leg)}</text>')
            lx += 22 + text_w(leg) + 28
        legend_svg.append(
            f'<circle cx="{fmt(lx+6)}" cy="{fmt(ly+6)}" r="3.5" fill="{ARCH_DOT}"/>')
        legend_svg.append(
            f'<text x="{fmt(lx+16)}" y="{fmt(ly+10)}" fill="#94a3b8" '
            f'font-size="11">request in flight</text>')
        lx += 16 + text_w("request in flight") + 28
        # semantic classDef legend entries (preserved stroke variants)
        if lo.legend_extra:
            ly2 = ly + 22
            lx = MARGIN
            for ex in lo.legend_extra:
                exd = f' stroke-dasharray="{ex["dash"]}"' if ex.get("dash") else ""
                legend_svg.append(
                    f'<rect x="{fmt(lx)}" y="{fmt(ly2)}" width="12" height="12" '
                    f'rx="3" fill="none" stroke="{ex.get("stroke", "#94a3b8")}"{exd}/>')
                legend_svg.append(
                    f'<text x="{fmt(lx+18)}" y="{fmt(ly2+10)}" fill="#94a3b8" '
                    f'font-size="11">{esc(ex["label"])}</text>')
                lx += 22 + text_w(ex["label"]) + 28
            H = H + 24
            W = max(W, lx + 10)
        W = max(W, lx + 10)
        H = H + 12

    svg = []
    svg.append(f'<svg id="flowsvg" width="100%" viewBox="0 0 {fmt(W)} {fmt(H)}" '
               f'role="img">')
    svg.append(f'<title>{esc(lo.title)} animated diagram</title>')
    svg.append(f'<desc>Top-down {mode} diagram; dashed connectors animate in the '
               f'direction of flow and dots ride the main paths.</desc>')
    svg.append(f'<defs>{MARKER}</defs>')
    svg.extend(bound_svg)
    svg.extend(conn)
    svg.extend(label_svg)
    svg.append('<g>')
    svg.extend(dot_svg)
    svg.append('</g>')
    svg.append('<g font-family="JetBrains Mono, monospace" text-anchor="middle">')
    svg.extend(node_svg)
    svg.append('</g>')
    if legend_svg:
        svg.append('<g font-family="JetBrains Mono, monospace" font-size="11">')
        svg.extend(legend_svg)
        svg.append('</g>')
    svg.append('</svg>')

    pulse = FLOW_DOT if mode == "flow" else ARCH_DOT
    maxw = 960 if mode == "flow" else 1100
    css = CSS_COMMON % (maxw, pulse)
    if mode != "flow":
        css += CSS_CARDS
    cards = ""
    if mode != "flow":
        cards = (
            '<div class="cards">'
            '<div class="card"><div class="card-header"><div class="card-dot cyan">'
            '</div><h3>Request path</h3></div><ul><li>• animated dot rides the '
            'main journey</li><li>• tier by tier</li></ul></div>'
            '<div class="card"><div class="card-header"><div class="card-dot violet">'
            '</div><h3>Data layer</h3></div><ul><li>• stores and caches</li>'
            '<li>• violet components</li></ul></div>'
            '<div class="card"><div class="card-header"><div class="card-dot rose">'
            '</div><h3>Boundaries</h3></div><ul><li>• regions and subnets</li>'
            '<li>• dashed containment</li></ul></div></div>')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(lo.title)} — dashmotion</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<div class="container">
  <div class="header"><div class="pulse-dot"></div><h1>{esc(lo.title)}</h1></div>
  <p class="subtitle">Generated by dashmotion layout.py ({mode} mode)</p>
  <div class="diagram-card">
    <button class="pause-btn" id="pauseBtn" aria-pressed="false">⏸ pause</button>
    {''.join(svg)}
  </div>
  {cards}
  <p class="footer">dashmotion · {mode} mode · deterministic layout</p>
</div>
{SCRIPT}
</body>
</html>"""
    return html


def _poly_len(pts):
    total = 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        total += ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
    return total


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    emit_svg = None
    if "--emit-svg" in sys.argv:
        i = sys.argv.index("--emit-svg")
        emit_svg = sys.argv[i + 1]
        args = [a for a in args if a != emit_svg]
    if not args:
        print(__doc__)
        sys.exit(1)
    graph = json.load(open(args[0], encoding="utf-8"))
    lo = Layout(graph)
    lo.run()
    geom = geometry(lo)
    if emit_svg:
        html = render(lo, geom)
        open(emit_svg, "w", encoding="utf-8").write(html)
        print(f"wrote {emit_svg}")
    else:
        print(json.dumps(geom, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
