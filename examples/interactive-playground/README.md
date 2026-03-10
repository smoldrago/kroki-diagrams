# Kroki Interactive Playground

This folder is a repo-local testbed for the interactive Kroki SVG wrapper.

Open `index.html` in a browser to compare engines and interaction tiers.
The committed files are meant to act as a working reference set for the distributed skill.

## Included diagrams

- `ai-request-sequence`: PlantUML sequence with branching and recompute flow
- `trading-platform-container`: C4 container architecture with internal and external dependencies
- `signal-orchestration-dag`: Graphviz DAG with queues, feedback, and human-review branch
- `market-ops-control-loop`: Mermaid flowchart with loops and operational branches
- `trading-domain-erd`: ERD schema with relational connections

## Re-render

Run:

```bash
./render_all.sh
```

The script uses the packaged renderer from `plugins/kroki-diagrams/scripts/render_kroki_diagram.py`,
so it works from a normal clone of this repo instead of depending on a machine-local path.
