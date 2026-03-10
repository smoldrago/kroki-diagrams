# Use-Case Taxonomy

Choose in this order:
1. user intent category
2. diagram type
3. engine or text format

The engine is the last decision, not the first.
Sometimes the best answer is not a diagram at all.

## Structured Text

Use when hierarchy matters more than visual topology.

- Text tree
  Best for: repository layout, folder structure, nested ownership, simple hierarchy with attached rules
  Default format: fenced `text` block with tree connectors like `├──`, `└──`, and `│`
  Avoid diagrams when: the user mainly needs to scan hierarchy, not relationships over time or across many systems

## Common Graphs

Use when the user is reasoning about structure, dependencies, or clusters rather than time.

- Block diagram
  Best for: high-level system pieces, simple boxes and arrows
  Default engine: `plantuml` or `mermaid`
- DAG / dependency graph
  Best for: pipelines, package dependencies, graph-heavy layouts
  Default engine: `graphviz`
- Mindmap
  Best for: brainstorming, feature grouping, concept exploration
  Default engine: `plantuml`

## UML / C4

Use when the user is reasoning about software architecture or behavior.

- Sequence
  Best for: interactions over time, API/request flow, validation paths
  Default engine: `plantuml`
- Activity
  Best for: control flow, branching logic, procedural workflows
  Default engine: `plantuml`
- Use case
  Best for: actor-to-capability views
  Default engine: `plantuml`
- Class
  Best for: type relationships in software design
  Default engine: `plantuml`
- C4 context
  Best for: system boundaries and external actors
  Default engine: `c4plantuml`
- C4 container
  Best for: service/container-level architecture
  Default engine: `c4plantuml`
- Component / package / runtime topology
  Best for: internal software structure and runtime wiring
  Default engine: `plantuml`

## Project Management

Use when the user is planning, sequencing, or decomposing work.

- WBS
  Best for: work breakdown and scope decomposition
  Default engine: `plantuml`
- Gantt
  Best for: timeline-oriented planning
  Default engine: `mermaid`
- BPMN
  Best for: operational or business processes with gateways or swimlanes
  Default engine: `bpmn`
  Current status: experimental in this repo

## Data Modeling

Use when the user is reasoning about entities, tables, or schema structure.

- ER diagram
  Best for: relational schema, cardinality, tables
  Default engine: `erd`
- Class diagram
  Best for: software domain types rather than database schema
  Default engine: `plantuml`

## Freestyle / Lightweight

Use when the user wants something fast, simple, and easy to edit.

- Flowchart
  Best for: user journeys, simple process flow, decision paths
  Default engine: `mermaid`
- Git graph
  Best for: branching/merge visualization
  Default engine: `mermaid`

## Decision Heuristics

- If the user asks "what does the repo/folder structure look like?", start with `Text tree`.
- If the user asks "how do these parts fit together?", think architecture.
- If the user asks "what happens step by step?", think sequence or activity.
- If the user asks "what depends on what?", think DAG or dependency graph.
- If the user asks "what are the tables/entities?", think ER.
- If the user asks "how do we plan or break down the work?", think WBS or Gantt.
- If the user asks "I just need a simple visual flow", think flowchart.

If more than one category is present, split the answer into multiple diagrams instead of forcing one.
