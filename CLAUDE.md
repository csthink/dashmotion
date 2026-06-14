# CLAUDE.md — dashmotion

Operational notes for AI agents (and humans) editing this repo. What dashmotion
does and how the generation works live in the [README](README.md) and
[docs/how-it-works.md](docs/how-it-works.md) — this file does not repeat them.

Mars's cross-project working philosophy (verification discipline, authorization
boundaries, how to sink learnings) lives in the global `~/.claude/CLAUDE.md` and is
not duplicated here. Instructions there and in chat override this file. This file is
a prose layer — it points at the real mechanisms; it does not enforce anything. When
a convention changes, change the mechanism first, then the pointer here.

## Mechanisms — follow the mechanism, don't paraphrase its details

- **Release gate.** Before tagging any version, both must hold: `test/run_checks.py`
  green over the **b1–b4 + m1–m7** fixtures (structure + per-case asserts + Mermaid
  fidelity), and a fresh **medium-effort** bianque-class diagram (30+ nodes)
  generating **≤ 8 min** end-to-end. `test/` is gitignored — runner and fixtures are
  local-only.
- **Verification authority.** A generated diagram is judged by the skill's bundled
  `skills/dashmotion/scripts/check_diagram.py` (structure: overlaps, connectors
  through boxes, broken loops, out-of-viewBox) and `check_fidelity.py` (Mermaid
  labels, verbatim) — this is SKILL.md Step 6. **Never** verify by eyeballing or a
  browser screenshot: label paraphrase is invisible to the eye and silently shipped
  reworded labels before `check_fidelity.py` was mechanized. `eval/` holds the
  committed eval harness.
- **Timing.** Always benchmark at **medium / default** effort, never xhigh — the
  effort setting alone moves latency ~3.4× and will corrupt any perf conclusion.
  ≤8 min is an absolute, model-agnostic UX target.

## Repo conventions — non-obvious, has bitten

- **What ships ≠ the repo.** `npx skills add` and the release zip ship **only**
  `skills/dashmotion/`. README, CHANGELOG, `docs/`, `eval/` stay in the repo and
  never reach an installed user — so doc-only changes need **no release**.
- **Gitignored by design:** `research/` (decision maps — write strategy/decision
  docs here, *not* committed) and `test/` (fixtures + runner). Don't try to commit
  them.
- **Two remotes:** `origin` = GitHub (csthink/dashmotion), `gitee` = Gitee. Tags,
  releases and the zip go to **both**. Don't merge to `main` or tag a release
  without Mars's explicit go-ahead.
- **Versioning rubric** is in the [CHANGELOG](CHANGELOG.md) header: the dividing line
  is the user-facing capability surface (new input / output mode / refinement =
  **minor**) vs. generator internals (perf, workflow, layout, fixes = **patch**).
- **Distribution & updates:** users install/upgrade via `npx skills` (`-g` for
  global) or the release zip; no client auto-notifies updates. Decision detail in the
  gitignored `research/distribution-and-updates.md`.
