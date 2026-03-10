# Kroki Safe Subset

This skill is based on a practical compatibility baseline tested in the local repo.

## Tested As Working

PlantUML samples that rendered successfully through Kroki:
- component and package diagrams
- styled component diagrams with modest `skinparam`
- basic sequence diagrams
- advanced sequence diagrams with `loop`, `alt`, and activation
- class diagrams
- activity diagrams
- state diagrams
- deployment diagrams
- use case diagrams
- representative shape coverage

C4-PlantUML samples that rendered successfully through Kroki:
- system context
- container

Additional engines tested successfully through Kroki:
- Mermaid flowchart
- Graphviz directed graph
- ERD schema

Additional engine tried but not yet stable in this repo:
- BPMN process

## Practical Recommendation

Prefer this subset by default:
- `plantuml` for most software diagrams
- `c4plantuml` for context and container architecture
- `graphviz` for graph-heavy dependency or DAG views
- `mermaid` for simple flowcharts
- `erd` for schema diagrams

For interactive hover-and-flow wrappers:
- strongest support: `plantuml`, `c4plantuml`, `graphviz`
- best-effort support: `mermaid`, `erd`

Treat richer shapes or heavy styling as optional, not foundational.

## Failure Strategy

If a render fails:
1. remove exotic shapes
2. reduce styling
3. remove notes
4. simplify labels
5. reduce the number of edges
6. if needed, switch to a more suitable engine instead of forcing the current one
