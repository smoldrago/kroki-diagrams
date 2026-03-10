#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$ROOT/../.." && pwd)"
RENDERER="$REPO_ROOT/plugins/kroki-diagrams/scripts/render_kroki_diagram.py"

render_diagram() {
  local engine="$1"
  local folder="$2"
  local source="$3"
  local title="$4"

  python3 "$RENDERER" \
    --engine "$engine" \
    --input "$ROOT/$folder/$source" \
    --output "$ROOT/$folder/rendered.svg" \
    --interactive-output "$ROOT/$folder/interactive.html" \
    --interactive-title "$title"
}

render_diagram plantuml ai-request-sequence source.puml "AI Request Sequence"
render_diagram c4plantuml trading-platform-container source.puml "Trading Platform Container"
render_diagram graphviz signal-orchestration-dag source.dot "Signal Orchestration DAG"
render_diagram mermaid market-ops-control-loop source.mmd "Market Ops Control Loop"
render_diagram erd trading-domain-erd source.erd "Trading Domain ERD"

echo "Playground rendered at $ROOT"
