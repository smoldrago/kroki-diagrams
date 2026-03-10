# Diagram Selection

Choose the smallest diagram type that answers the user's question.

Read `use-case-taxonomy.md` first to identify the intent category.
Then use this file to narrow the diagram type.
For broader engine guidance, read `engine-matrix.md`.

If `use-case-taxonomy.md` points to a text tree, stop here and produce structured text instead of a diagram.

## Software Architecture

- Use `c4plantuml` for system context and container diagrams.
- Use `plantuml` for package, component, deployment, and runtime topology views.

Preferred C4 levels for this repo:
- Context: when showing users and external systems
- Container: when showing web, API, worker, database, cache, and supporting services

Avoid C4 when the user really needs temporal flow or detailed package structure.

## Temporal Flow

- Use `plantuml` sequence diagrams for API interactions, request flow, user journeys over time, and validation paths.
- Use `plantuml` activity diagrams for procedural control flow.
- Use `bpmn` only on explicit request or when process semantics clearly matter more than software structure.

## Graph-Heavy Structure

- Use `graphviz` for DAGs, dependency graphs, and layouts with many edges.
- Use `mermaid` for simple flowcharts, quick journeys, or lightweight browser-friendly diagrams.

## Data Modeling

- Use `erd` for schema and relational diagrams.
- Use `plantuml` class diagrams only when the user is really asking for software type relationships rather than table structure.

## Planning And Decomposition

- Use `plantuml` WBS when the user is decomposing work or scope.
- Use `mermaid` Gantt when the user is asking for timeline-oriented planning.
- Use `plantuml` mindmap when the user is clustering concepts or brainstorming.

## Split Instead Of Overloading

If the answer needs more than one of these:
- architecture
- runtime topology
- step-by-step flow
- schema
- planning/timeline

create multiple diagrams instead of forcing one giant diagram.
