#!/usr/bin/env python3
"""Fidelity checker for mermaid -> dashmotion conversion.

Verifies the fidelity contract of references/mermaid-input.md: the output
diagram must preserve the source's node set (labels verbatim), edge set,
edge labels, and containment labels. Layout/colors are intentionally NOT
compared (they are recomputed by design).

Checks:
  F1 node-labels    every source node label appears in the SVG text layer
  F2 edge-labels    every source edge label appears in the SVG text layer
  F3 group-labels   every subgraph/boundary label appears in the SVG text layer
  F4 edge-count     connector <path> count is within
                    [edges - backedges, edges]  (a back/self edge may legally
                    render as a "loop sublabel" instead of a drawn path)

Known limitations (documented, not checked): invented nodes that don't shadow
a source label; label collisions; geometric containment (check_diagram.py's
territory).

Supported mermaid subset: flowchart/graph + stateDiagram-v2 (the dashmotion
v2.2 feature scope). classDef/class/style/linkStyle/click/%% lines ignored.

Usage: python3 check_fidelity.py source.mmd output.html [--json]
Exit code: 0 if PASS, 1 if any check fails or inputs are unparseable.
"""

import html as html_mod
import json
import re
import sys
import xml.etree.ElementTree as ET

ARROWS = ["<-->", "-.->", "==>", "-->", "---"]
SHAPES = [  # (open, close) longest-first so cylinders beat rects, etc.
    ("[(", ")]"), ("([", "])"), ("((", "))"), ("{{", "}}"),
    ("[[", "]]"), ("[/", "/]"), ("[\\", "\\]"), ("[", "]"),
    ("(", ")"), ("{", "}"), (">", "]"),
]
SKIP_LINE = re.compile(r"^\s*(%%|classDef\b|class\b|style\b|linkStyle\b|click\b|direction\b)")


def clean_label(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        raw = raw[1:-1]
    return html_mod.unescape(raw).strip()


def parse_node_token(tok):
    """'A[Some label]' -> (id, label); bare 'A' -> ('A', None). Strips :::class."""
    tok = tok.strip()
    tok = re.sub(r":::\S+$", "", tok).strip()
    m = re.match(r"^([A-Za-z0-9_.-]+)(.*)$", tok, re.S)
    if not m:
        return None, None
    nid, rest = m.group(1), m.group(2).strip()
    if not rest:
        return nid, None
    for op, cl in SHAPES:
        if rest.startswith(op) and rest.endswith(cl):
            return nid, clean_label(rest[len(op):len(rest) - len(cl)])
    return nid, None


def parse_mermaid(text):
    """Returns dict: nodes {id: label}, edges [(src, dst, label)], groups [label],
    first_mention {id: index}, kind ('flowchart'|'state').

    stateDiagram [*] is split into __START__/__END__ pseudo-nodes so the
    cycle detector doesn't see entry->...->exit as a cycle."""
    lines = [l for l in text.splitlines() if l.strip()]
    header = lines[0].strip().lower() if lines else ""
    kind = "state" if header.startswith("statediagram") else "flowchart"
    nodes, edges, groups = {}, [], []
    first_mention, mention_i = {}, 0

    def touch(nid, label):
        # label=None means a bare reference: never overwrite a real label.
        nonlocal mention_i
        if nid not in first_mention:
            first_mention[nid] = mention_i
            mention_i += 1
        if nid not in nodes:
            nodes[nid] = label
        elif label is not None and nodes[nid] is None:
            nodes[nid] = label

    for line in lines[1:]:
        s = line.strip()
        if SKIP_LINE.match(s) or s == "end":
            continue
        m = re.match(r'^subgraph\s+(?:[A-Za-z0-9_.-]+\s*\[\s*"?(.*?)"?\s*\]|"?([^"\[\]]+)"?)\s*$', s)
        if m:
            groups.append(clean_label(m.group(1) or m.group(2)))
            continue

        if kind == "state":
            m = re.match(r"^(\[\*\]|[A-Za-z0-9_.-]+)\s*-->\s*(\[\*\]|[A-Za-z0-9_.-]+)\s*(?::\s*(.+))?$", s)
            if m:
                src, dst, lbl = m.group(1), m.group(2), m.group(3)
                src = "__START__" if src == "[*]" else src
                dst = "__END__" if dst == "[*]" else dst
                for nid in (src, dst):
                    if not nid.startswith("__"):
                        touch(nid, nid)
                edges.append((src, dst, clean_label(lbl) if lbl else None))
            continue

        # Mask quoted strings so `--` or arrows inside labels can't split the line
        qmap = []

        def _mask(mo):
            qmap.append(mo.group(0))
            return "\x00%d\x00" % (len(qmap) - 1)

        def _unmask(tok):
            return re.sub(r"\x00(\d+)\x00", lambda mo: qmap[int(mo.group(1))], tok)

        s = re.sub(r'"[^"]*"', _mask, s)

        # flowchart: split the line on arrows, keeping them. Labeled-arrow
        # forms (`-- x -->`, `-. x .->`, `== x ==>`) come first so they win
        # over their unlabeled prefixes.
        pat = ("(" + r"--\s*[^->]+?\s*-->|-\.\s*[^.]+?\s*\.->|==\s*[^=>]+?\s*==>|"
               + "|".join(re.escape(a) for a in ARROWS) + ")")
        parts = re.split(pat, s)
        if len(parts) == 1:
            nid, lbl = parse_node_token(_unmask(s))
            if nid:
                touch(nid, lbl)
            continue
        # walk: node (arrow node)*
        prev_ids = None
        i = 0
        while i < len(parts):
            seg = parts[i].strip()
            if i % 2 == 0:  # node segment, may carry |label| prefix from arrow
                edge_lbl = None
                lm = re.match(r"^\|\s*(.+?)\s*\|\s*(.*)$", seg, re.S)
                if lm:
                    edge_lbl = clean_label(_unmask(lm.group(1)))
                    seg = lm.group(2).strip()
                ids = []
                for tok in re.split(r"\s*&\s*", seg):
                    nid, lbl = parse_node_token(_unmask(tok))
                    if nid:
                        touch(nid, lbl)
                        ids.append(nid)
                if prev_ids is not None and ids:
                    arrow = _unmask(parts[i - 1].strip())
                    am = re.match(r"^(?:--\s*(.+?)\s*-->|-\.\s*(.+?)\s*\.->|==\s*(.+?)\s*==>)$", arrow)
                    if am:
                        edge_lbl = clean_label(am.group(1) or am.group(2) or am.group(3))
                    for a in prev_ids:
                        for b in ids:
                            edges.append((a, b, edge_lbl))
                prev_ids = ids if ids else prev_ids
            i += 1
    # a node only ever referenced bare gets its id as label
    for nid, lbl in nodes.items():
        if lbl is None:
            nodes[nid] = nid
    return {"kind": kind, "nodes": nodes, "edges": edges, "groups": groups,
            "first_mention": first_mention}


def count_back_edges(parsed):
    """Edges that close a cycle (incl. self-loops), via DFS in first-mention
    order — these may legally render as a loop sublabel instead of a path."""
    adj = {}
    for a, b, _ in parsed["edges"]:
        adj.setdefault(a, []).append(b)
    fm = parsed["first_mention"]
    every = sorted(set(adj) | {b for bs in adj.values() for b in bs},
                   key=lambda n: fm.get(n, -1))
    color, back = {}, 0
    sys.setrecursionlimit(10000)

    def dfs(u):
        nonlocal back
        color[u] = 1
        for v in adj.get(u, []):
            if color.get(v, 0) == 1:
                back += 1
            elif color.get(v, 0) == 0:
                dfs(v)
        color[u] = 2

    for n in every:
        if color.get(n, 0) == 0:
            dfs(n)
    return back


# ---------- output side ----------

def local(tag):
    return tag.split("}")[-1]


def extract_svg(html_text):
    m = re.search(r"<svg\b.*?</svg>", html_text, re.S)
    if not m:
        return None
    return m.group(0)


NUM = re.compile(r"-?\d*\.?\d+")


def path_endpoints(d):
    """First and last point of a path's `d` (absolute commands M/L/H/V/C/S/Q/T/A)."""
    toks = re.findall(r"[A-Za-z]|" + NUM.pattern, d)
    x = y = sx = sy = None
    first = None
    i = 0
    cmd = None
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            continue
        nums = []
        while i < len(toks) and not toks[i].isalpha():
            nums.append(float(toks[i]))
            i += 1
        c = (cmd or "L").upper()
        rel = cmd.islower()
        j = 0
        step = {"M": 2, "L": 2, "T": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "A": 7}.get(c, 2)
        while j + step <= len(nums):
            seg = nums[j:j + step]
            if c == "H":
                x = (x or 0) + seg[0] if rel else seg[0]
            elif c == "V":
                y = (y or 0) + seg[0] if rel else seg[0]
            else:
                nx, ny = seg[-2], seg[-1]
                x = (x or 0) + nx if rel else nx
                y = (y or 0) + ny if rel else ny
            if c == "M" and first is None:
                first = (x, y)
                sx, sy = x, y
            j += step
            if c == "M":
                c = "L"  # implicit lineto after moveto
        if first is None and x is not None and y is not None:
            first = (x, y)
    return first, (x, y)


def near_rect(pt, rects, tol=14.0):
    if pt is None or pt[0] is None or pt[1] is None:
        return False
    px, py = pt
    for (rx, ry, rw, rh) in rects:
        if rx - tol <= px <= rx + rw + tol and ry - tol <= py <= ry + rh + tol:
            return True
    return False


def svg_texts_and_paths(svg_src):
    """Returns (list of per-<text> joined strings, count of connector <path>).

    A path counts as a connector only if both endpoints land on/near a
    node-sized rect — this excludes legend swatch samples and other
    decorative strokes that aren't edges of the graph."""
    root = ET.fromstring(svg_src)
    texts, paths, rects = [], [], []

    def walk(el, in_defs):
        tag = local(el.tag)
        here_defs = in_defs or tag in ("defs", "marker", "pattern")
        if tag == "text":
            joined = " ".join(" ".join(el.itertext()).split())
            if joined:
                texts.append(joined)
            return
        if tag == "rect" and not here_defs:
            try:
                r = tuple(float(el.get(k, "0")) for k in ("x", "y", "width", "height"))
                if r[2] >= 60 and r[3] >= 30:  # node-sized; skips legend swatches
                    rects.append(r)
            except ValueError:
                pass
        if tag == "path" and not here_defs and el.get("d"):
            paths.append(el.get("d"))
        for ch in el:
            walk(ch, here_defs)

    walk(root, False)
    path_count = 0
    for d in paths:
        a, b = path_endpoints(d)
        if near_rect(a, rects) and near_rect(b, rects):
            path_count += 1
    return texts, path_count


def norm(s):
    return " ".join(html_mod.unescape(s).split()).lower()


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv
    if len(args) != 2:
        print(__doc__)
        sys.exit(1)
    src_path, out_path = args
    src = parse_mermaid(open(src_path, encoding="utf-8").read())
    html_text = open(out_path, encoding="utf-8").read()
    svg_src = extract_svg(html_text)
    if svg_src is None:
        print(f"FAIL  {out_path}  (no <svg> found)")
        sys.exit(1)
    try:
        texts, path_count = svg_texts_and_paths(svg_src)
    except ET.ParseError as e:
        print(f"FAIL  {out_path}  (svg not well-formed: {e})")
        sys.exit(1)
    blob = norm(" | ".join(texts))
    # Architecture mode legally splits a long source label into a 13px label
    # + 10px sublabel (two adjacent <text> elements) — match across elements
    # as a fallback before declaring a label missing.
    blob_loose = norm(" ".join(texts))

    # Third fallback tier: the label/sublabel split may absorb the separator
    # punctuation (`A：B` -> label "A" + sublabel "B"); compare with separator
    # chars stripped. Limitation: also hides a genuinely dropped separator.
    SEP = re.compile(r"[：:·•,，;；]")

    def desep(s):
        return " ".join(SEP.sub(" ", s).split())

    def present(lbl):
        n = norm(lbl)
        if n in blob or n in blob_loose:
            return True
        return desep(n) in desep(blob_loose)

    failures = []
    # F1 node labels
    for nid, lbl in src["nodes"].items():
        if lbl and not present(lbl):
            failures.append(f"F1 node label missing: {lbl!r}")
    # F2 edge labels
    for _, _, lbl in src["edges"]:
        if lbl and not present(lbl):
            failures.append(f"F2 edge label missing: {lbl!r}")
    # F3 group labels. Legend-like subgraphs may legally merge into
    # dashmotion's own legend with their title omitted (contract exception,
    # 2026-06-12) — exempt them; their entries are still covered by F1.
    LEGEND_NAME = re.compile(r"图例|legend|key", re.I)
    for g in src["groups"]:
        if g and not present(g) and not LEGEND_NAME.search(g):
            failures.append(f"F3 group label missing: {g!r}")
    # F4 edge count vs connector paths
    back = count_back_edges(src)
    n_edges = len(src["edges"])
    lo, hi = n_edges - back, n_edges
    if not (lo <= path_count <= hi):
        failures.append(
            f"F4 connector path count {path_count} outside [{lo}, {hi}] "
            f"(edges={n_edges}, back/self={back})")

    report = {
        "source": src_path, "output": out_path, "kind": src["kind"],
        "nodes": len(src["nodes"]), "edges": n_edges, "back_edges": back,
        "connector_paths": path_count, "failures": failures,
    }
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if not failures else "FAIL"
        print(f"{status}  {out_path}  (nodes={report['nodes']} edges={n_edges} "
              f"paths={path_count} back={back})")
        for f in failures:
            print(f"  - {f}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
