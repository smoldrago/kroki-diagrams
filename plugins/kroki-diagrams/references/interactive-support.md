# Interactive Support

This skill can now produce an `interactive.html` wrapper around Kroki-rendered SVG output.

The interactive wrapper supports:
- click the current node
- brighten the selected node border
- brighten directly connected nodes
- animate connected edges
- dim unrelated nodes and edges without hiding them
- reset when the user clicks non-interactive diagram space

## Interaction Modes

### Directed flow

Used when the SVG exposes a clear source and target for an edge.

Behavior:
- outgoing edges animate away from the selected node
- incoming edges animate toward the selected node

### Connected-only flow

Used when a connection is known but direction is not reliable or semantically appropriate.

Behavior:
- connected edges animate with a neutral electric-current effect
- connected nodes still highlight normally

## Support Tiers

### Full support

- `plantuml` sequence diagrams
- `plantuml` and `c4plantuml` entity-and-link diagrams
- `graphviz`

These emit stable enough SVG metadata to support node selection, directional edges, and dimming with good confidence.

### Best-effort support

- `mermaid`
- `erd`

These generally support the click-and-dim interaction, but edge mapping is more dependent on emitted SVG structure and naming conventions.

For Mermaid, prefer simple alphanumeric node ids if the interactive layer matters.

## Usage

Generate the normal SVG and the interactive HTML in one step:

```bash
python3 scripts/render_kroki_diagram.py \
  --engine plantuml \
  --input /path/to/source.puml \
  --output /path/to/rendered.svg \
  --interactive-output /path/to/interactive.html
```

You can also build the wrapper separately from an existing SVG:

```bash
python3 scripts/build_interactive_kroki_html.py \
  --engine graphviz \
  --input /path/to/rendered.svg \
  --output /path/to/interactive.html
```

## Limitations

- This is for inline SVG wrapped in HTML, not PNG or PDF.
- Static image embeds such as `<img src="rendered.svg">` cannot provide the interactive behavior.
- Engines outside the support tiers should be treated as non-interactive until tested.
