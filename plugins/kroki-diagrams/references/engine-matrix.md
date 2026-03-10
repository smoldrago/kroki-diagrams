# Engine Matrix

Choose the smallest engine that fits the chosen diagram type well.

This file assumes you already identified the use-case category and diagram type from `use-case-taxonomy.md`.

## Primary Engines

### `c4plantuml`

Use for:
- system context
- container diagrams
- high-level architecture boundaries

Best when:
- the user is asking how systems, services, users, and databases relate
- you want an architecture diagram that feels structured and intentional

Avoid when:
- the user needs detailed timing or call flow
- the user needs schema detail

### `plantuml`

Use for:
- sequence
- activity
- state
- class
- use case
- deployment
- component or package views
- runtime topology
- WBS
- mindmap

Best when:
- the request is software-centric
- you need strong control over layout and styling
- the diagram should look polished and coherent
- you may need arrow-level layout hints or hidden nudges to keep the diagram readable

Avoid when:
- a true graph layout is more important than UML-style structure

### `graphviz`

Use for:
- DAGs
- dependency graphs
- pipelines
- graph-heavy topology

Best when:
- there are many edges
- layout clarity depends on graph ranking and routing
- the user wants a strict graph rather than a UML diagram
- the user may want node-hover interactivity after SVG render
- you need explicit control over spacing, ranks, and orthogonal routing

Avoid when:
- the request is really a temporal flow or C4 architecture view

### `mermaid`

Use for:
- simple flowcharts
- user journeys
- lightweight gantt
- git graphs

Best when:
- the user wants simple, easy-to-edit syntax
- a browser-friendly or GitHub-friendly format matters
- the user is okay with best-effort interactive SVG enhancement rather than guaranteed stable DOM hooks
- the flow can be decomposed into subgraphs with a strong direction

Avoid when:
- the diagram needs heavy styling control
- the diagram is already dense or layout-sensitive

## Secondary Engines

### `bpmn`

Use for:
- business process diagrams
- swimlanes
- gateway-heavy workflows

Best when:
- the request is operational or workflow-oriented rather than software-structural

Current status:
- treat as experimental in this repo until Kroki smoke coverage is stable

### `erd`

Use for:
- relational schema views
- tables, fields, and relationships

Best when:
- the user is asking about entities and cardinality, not service architecture

## Heuristics

- If the chosen type is `C4 context` or `C4 container`, use `c4plantuml`.
- If the chosen type is `Sequence`, `Activity`, `Use case`, `WBS`, or `Mindmap`, use `plantuml`.
- If the chosen type is `DAG` or dependency graph, use `graphviz`.
- If the chosen type is `Flowchart`, `Gantt`, or `Git graph`, use `mermaid`.
- If the chosen type is `ER`, use `erd`.
- If the chosen type is `BPMN`, treat `bpmn` as experimental.
- If the user explicitly wants hover-driven SVG interactivity, prefer `plantuml`, `c4plantuml`, or `graphviz` before `mermaid`.

If more than one concern is present, split into multiple diagrams instead of overloading one engine.
