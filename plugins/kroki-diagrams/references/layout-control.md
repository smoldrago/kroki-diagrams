# Layout Control

This file is about avoiding spaghetti. Use it after choosing the diagram type and engine, and before writing the source.

The root problem is usually not styling. It is lack of layout constraints.

## Global Rules

- Force one dominant flow direction for every diagram.
- Group before connecting: define clusters, boundaries, subgraphs, or packages before writing cross-group edges.
- Prefer one concern per diagram. If a diagram mixes control flow and data topology, split it.
- Prefer 7 nodes or fewer per visible layer. If a layer needs more, add a grouping layer or split the diagram.
- If the diagram would exceed 15 edges, strongly consider splitting it into two diagrams connected by one shared bridge node.
- Avoid bidirectional arrows on dense diagrams. Use two directed edges only when they are essential.
- If one node fans out to more than 4 peers, introduce an intermediate aggregator node or a grouped boundary.

## Engine Defaults

### PlantUML

Use:

- `left to right direction` for wide flows and runtime topology
- default top-down for hierarchies when it is genuinely clearer
- explicit directional arrows such as `-right->`, `-down->`, `-left->` when the auto-layout starts looping
- `together { ... }` to keep related nodes aligned
- `-[hidden]->` edges for layout nudging only when necessary

Only escalate to `!pragma layout smetana` or `!pragma layout elk` if the default layout is clearly failing.

### C4-PlantUML

Use:

- `LAYOUT_LEFT_RIGHT()` for most context and container diagrams
- `LAYOUT_TOP_DOWN()` for deeper hierarchies
- boundaries to group related systems or containers before connecting them

Prefer one or two external systems per side rather than spraying externals all around the canvas.

### Graphviz

Start dense structure diagrams with:

```dot
graph [
  rankdir=LR,
  splines=ortho,
  nodesep=0.8,
  ranksep=1.2,
  overlap=false,
  remincross=true
]
```

Use:

- `splines=ortho` first for right-angle routes
- `splines=polyline` if ortho becomes too rigid
- `rank=same` blocks to force peers onto one layer
- clusters for major subsystems before drawing cross-cluster edges

### Mermaid

Use:

- `flowchart LR` or `flowchart TD` consistently
- `subgraph` blocks for every logical section in a medium or large flowchart
- `direction LR` or `direction TD` inside subgraphs where needed

Connect subgraphs through one or two representative nodes rather than wiring many internals directly across sections.

### ERD

Prefer top-down or left-to-right relationship chains, not starbursts.

Keep:

- a limited set of entities in each diagram
- bridge tables in the middle
- leaf tables near the edges

If the schema is broad, split by bounded context rather than forcing the entire schema into one ERD.
