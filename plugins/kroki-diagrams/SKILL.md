---
name: kroki-diagrams
description: Create clean, readable diagrams using Kroki with a use-case-first selector. Use when Codex needs to visualize architecture, runtime topology, request flows, dependency graphs, schemas, planning structures, or tree-like repository layouts from code, docs, or natural-language descriptions. Prefer this skill when the user wants free, versionable, repository-local diagrams and wants the right diagram type, engine, or text-tree format chosen for the job.
---

# Kroki Diagrams

Create repository-friendly visual artifacts that stay readable under change. This skill uses Kroki as the renderer when a diagram is the right answer, but starts by choosing the right artifact family for the user’s intent before picking an engine.

## Workflow

1. Read the relevant code, docs, or user description.
2. Choose the use-case category and diagram type using `references/use-case-taxonomy.md`.
3. If the best artifact is a diagram, choose the engine using `references/diagram-selection.md` and `references/engine-matrix.md`.
4. Choose the output location and folder structure using `references/output-placement.md`.
5. Apply the readability rules in `references/style-guide.md`, the engine scaffold in `references/engine-style-templates.md`, and the layout constraints in `references/layout-control.md`.
6. Write the diagram source or structured text artifact.
7. Render it with `scripts/render_kroki_diagram.py` only if it is a Kroki-backed diagram.
8. Let the render step create or update the shared `index.html` in the artifact base unless there is a strong reason not to.
9. If click-based exploration would help, read `references/interactive-support.md` and emit an `interactive.html` wrapper.
10. Return the rendered output, any Kroki URL if generated, the source files used, and the artifact code.

## Choose The Right Diagram Family

Load `references/use-case-taxonomy.md` first.

Pick in this order:
1. intent category
2. diagram type
3. engine or text format

If the problem contains more than one distinct concern, split it into multiple diagrams instead of forcing everything into one.

Then:
- read `references/diagram-selection.md` for type-level guidance
- read `references/engine-matrix.md` for engine tradeoffs
- read `references/output-placement.md` for where the artifact should live

Examples:
- service interactions over time -> `Sequence` -> `plantuml`
- system boundaries -> `C4 Container` -> `c4plantuml`
- repo dependency graph -> `DAG` -> `graphviz`
- schema relationships -> `ER` -> `erd`
- feature decomposition -> `WBS` -> `plantuml`
- timeline planning -> `Gantt` -> `mermaid`
- repository layout with rules -> `Text tree` -> no Kroki engine

## Place Artifacts Well

Load `references/output-placement.md` before writing files.

Default placement order:
1. follow an existing `docs/diagrams/` convention if present
2. otherwise use `docs/diagrams/<artifact-name>/` if `docs/` exists
3. otherwise use another established docs-like location if clearly present
4. otherwise fall back to `diagrams/<artifact-name>/` at repo root

Use one folder per artifact:

```text
<artifact-name>/
  source.<ext>
  rendered.svg
  rendered.png
```

If the artifact is text-only, only write the source file.

## Keep It Clean

Load `references/style-guide.md` before drafting the diagram.
Load `references/engine-style-templates.md` when writing a Kroki-backed source file.
Load `references/layout-control.md` when the diagram has enough edges or groups that auto-layout might tangle it.

Non-negotiable rules:
- Optimize for clarity, not completeness.
- Prefer 7 to 9 nodes in an overview diagram.
- Collapse repeated infrastructure or shared-package relationships into one labeled box when possible.
- Use left-to-right layout for structure diagrams unless vertical flow is genuinely clearer.
- Avoid all-to-all support arrows.
- Use one diagram per concern: structure, runtime, or sequence.
- Use the engine's required style header and only add more styling if the base diagram renders cleanly.
- Follow the cross-engine palette and contrast rules unless the user asks for a different visual direction.
- Force a dominant layout direction and add grouping or rank hints before allowing a large flat graph.
- Split diagrams instead of forcing a single diagram past a readable edge count.

## Rendering

Use:

```bash
python3 scripts/render_kroki_diagram.py --engine plantuml --input /path/to/diagram.puml --output /path/to/diagram.svg
```

or:

```bash
python3 scripts/render_kroki_diagram.py --engine c4plantuml --input /path/to/diagram.puml --output /path/to/diagram.svg
```

Other supported engines:

```bash
python3 scripts/render_kroki_diagram.py --engine mermaid --input /path/to/diagram.mmd --output /path/to/diagram.svg
python3 scripts/render_kroki_diagram.py --engine graphviz --input /path/to/diagram.dot --output /path/to/diagram.svg
python3 scripts/render_kroki_diagram.py --engine erd --input /path/to/diagram.erd --output /path/to/diagram.svg
```

The script also prints a shareable Kroki URL for the generated source.
It also writes per-artifact metadata and refreshes the parent `index.html` collection page by default, so every normal artifact render updates the directory overview automatically unless `--skip-index` is passed.

To build the interactive wrapper at the same time:

```bash
python3 scripts/render_kroki_diagram.py --engine plantuml --input /path/to/diagram.puml --output /path/to/rendered.svg --interactive-output /path/to/interactive.html
```

The wrapper adds:
- click-to-select highlight on the current node
- connected-edge animation
- directional flow where the SVG exposes source and target
- neutral current animation where direction is not available
- contextual dimming for unrelated nodes and edges
- reset to the default state when the user clicks non-interactive diagram space

Read `references/interactive-support.md` before promising identical behavior across every engine.

## Output Format

When the user asks for a diagram or structure artifact, return:

1. A short note on which artifact type you chose.
2. A clickable file path to the rendered output if one was written locally.
3. A clickable file path to `interactive.html` if an interactive wrapper was written.
4. A clickable file path to the generated collection `index.html` if the render step updated it.
5. The Kroki URL if generated.
6. A short sources list describing which files or notes informed the diagram.
7. The diagram code or text artifact in a fenced block using the appropriate language label.

If the user only asked for the diagram, keep the surrounding explanation short.

## Safe Subset

Use the compatibility harness in `references/kroki-safe-subset.md` as the default baseline.

Prefer:
- `plantuml` and `c4plantuml` as the main architecture defaults
- `graphviz` for graph-heavy structure
- `mermaid` for simple flowcharts
- `erd` for schema diagrams
- plain text trees for repository layout and other hierarchy-first structure

If a render fails, simplify before trying exotic shapes or styling.

## Scope Discipline

Do not support every Kroki engine equally.

Use this tiering:
- Primary: `plantuml`, `c4plantuml`, `graphviz`, `mermaid`
- Secondary: `erd`
- Explicit request only: any other Kroki engine not covered in the references

Only choose a secondary or explicit-request engine when it is clearly better for the user’s question.

Treat `bpmn` as experimental until we have a stable passing smoke sample in this repo.

## Resources

- `scripts/render_kroki_diagram.py` renders curated Kroki engines and prints a shareable URL.
- `scripts/build_diagram_index.py` builds a lightweight `index.html` overview for a directory of diagram artifacts.
- `references/use-case-taxonomy.md` maps user intent to diagram families and types.
- `references/diagram-selection.md` explains which diagram family to choose.
- `references/engine-matrix.md` explains when one engine is better than another.
- `references/output-placement.md` explains where artifacts should live in the repo.
- `references/style-guide.md` explains how to keep diagrams readable.
- `references/engine-style-templates.md` provides engine-specific style headers and cross-engine visual defaults.
- `references/layout-control.md` explains how to force direction, grouping, spacing, and split points to avoid spaghetti layouts.
- `references/kroki-safe-subset.md` summarizes the tested compatibility baseline.
- `references/interactive-support.md` explains which engines support click-and-flow behavior and how to generate it.
