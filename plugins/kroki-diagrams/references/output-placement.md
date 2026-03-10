# Output Placement

Choose the output location after choosing the artifact type.

## Preferred Structure

When the repo already has a diagram convention, follow it.

Preferred artifact layout:

```text
<base>/<artifact-name>/
  source.<ext>
  rendered.svg
  rendered.png

<base>/index.html
```

Use:
- `source.puml` for PlantUML or C4-PlantUML
- `source.mmd` for Mermaid
- `source.dot` for Graphviz
- `source.erd` for ERD
- `source.md` for text-tree or structured text artifacts

## Placement Order

Pick the first suitable option:

1. Existing diagram home
   Example: `docs/diagrams/<artifact-name>/`

2. Existing docs home
   Example: `docs/diagrams/<artifact-name>/` if `docs/` exists but `docs/diagrams/` does not yet

3. Existing architecture or design docs area
   Example: `architecture/diagrams/<artifact-name>/`, `design/diagrams/<artifact-name>/`, or a similar established documentation area

4. Root-level fallback
   Example: `diagrams/<artifact-name>/`

If none of the above is clearly present, use the root-level fallback.

## Naming

- Use short kebab-case artifact names.
- Name the folder after the artifact, not the engine.
- Keep rendered filenames generic: `rendered.svg`, `rendered.png`.
- Keep the source filename generic: `source.<ext>`.
- Keep one generated collection index at the shared base as `index.html`.

## When To Reuse Existing Files

- If the artifact already exists, update it in place.
- If the repo already groups one artifact per folder, keep that convention.
- Do not introduce a new parallel layout without a strong reason.
