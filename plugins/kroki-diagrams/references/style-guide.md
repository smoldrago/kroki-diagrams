# Style Guide

The goal is legibility first.

## Default Rules

- Prefer one concern per diagram.
- Prefer 7 to 9 nodes in an overview.
- Use left-to-right direction for structure and topology diagrams.
- Use sequence diagrams for behavior over time.
- Group related nodes using packages or boundaries.
- Force a dominant layout direction before adding detailed edges.
- Use short labels.
- Keep box text to 1 or 2 short lines whenever possible.
- Prefer terse subtitles over paragraph-like descriptions inside nodes.
- Prefer one shared node over repeating the same support relationship three times.
- Start unstyled or lightly styled.

## Avoid Spaghetti

- Do not show every dependency if it does not help the user's reasoning.
- Do not draw all helper-package arrows when one summarized relationship communicates the idea better.
- Do not create all-to-all relationships.
- Do not leave medium or large graphs as one flat list of nodes without groups or rank hints.
- Do not mix structure and sequence in the same diagram.
- Do not encode every implementation detail in an overview.
- Do not attach quality or support layers to every box unless the user explicitly wants that level of completeness.
- Do not let long curved support arrows dominate the visual composition.
- Do not force more than roughly 15 edges into one diagram if two diagrams would explain it more clearly.

## Good Defaults

- For repo structure: show apps, shared packages, and key rules.
- For runtime topology: show harness, services, backing services, and quality layer.
- For sequence: show only the participants that actually exchange messages in the flow.

## Styling Guidance

- Use plain shapes before exotic shapes.
- Start from the engine's mandatory style scaffold in `engine-style-templates.md` before adding custom styling.
- Use modest colors only after the base diagram is stable.
- Keep notes sparse.
- Use a restrained palette with clear fills and readable contrast.
- On light backgrounds, keep arrows, borders, and text dark enough to read at a glance.
- Make the main path visually dominant and supporting concerns secondary.
- If styling causes render instability, remove it.

## Visual Defaults

- Use `#FAFAFA` as the canvas background instead of pure white.
- Use Arial or Helvetica at 13px or larger.
- Use at most 4 distinct fill colors in one diagram.
- Use `#08427B` for people and user roles.
- Use `#1168BD` for services and application containers.
- Use `#FFF3E0` for databases and persistent stores.
- Use white text on dark fills and `#1A1A2E` on light fills.
- Prefer a darker neutral for arrows and relationship text than the node fill colors.

## Engine Notes

- For `plantuml`, prefer the modern `<style>` block over legacy `skinparam`.
- For `c4plantuml`, prefer `UpdateElementStyle()` and `UpdateRelStyle()` as the stable default. If you use `!theme`, place it before `!include`.
- For `graphviz`, always define `graph`, `node`, and `edge` defaults before any nodes.
- For `mermaid`, put the `%%{init}%%` theme block on the very first line and define semantic `classDef` groups.
- For this skill's `erd` engine, favor naming cleanliness and field discipline over heavy theming, because the renderer exposes limited style controls.
