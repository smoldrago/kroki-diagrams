# kroki-diagrams

**A distributable agent skill for generating clean Kroki diagrams, interactive SVG viewers, and collection indexes.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

This repo packages the `kroki-diagrams` skill for:
- Claude Code plugin marketplace format
- OpenAI Codex skill installation
- Pi agent installation

The skill itself chooses the right diagram family and Kroki engine, generates readable source files, renders SVG output, can emit interactive HTML wrappers, and now auto-builds an `index.html` overview for diagram collections.

## Repo Layout

```text
.claude-plugin/
  plugin.json
  marketplace.json
plugins/
  kroki-diagrams/
    .claude-plugin/plugin.json
    SKILL.md
    agents/openai.yaml
    references/
    scripts/
install-pi.sh
```

## Install

### Claude Code

```bash
/plugin marketplace add smoldrago/kroki-diagrams
/plugin install kroki-diagrams@kroki-diagrams-marketplace
```

### OpenAI Codex

```bash
git clone --depth 1 https://github.com/smoldrago/kroki-diagrams.git /tmp/kroki-diagrams
cp -r /tmp/kroki-diagrams/plugins/kroki-diagrams ~/.agents/skills/kroki-diagrams
rm -rf /tmp/kroki-diagrams
```

Invoke with `$kroki-diagrams` or let Codex trigger it implicitly.

### Pi

```bash
curl -fsSL https://raw.githubusercontent.com/smoldrago/kroki-diagrams/main/install-pi.sh | bash
```

Or clone and run:

```bash
git clone --depth 1 https://github.com/smoldrago/kroki-diagrams.git
cd kroki-diagrams
./install-pi.sh
```

## What’s Included

- `plugins/kroki-diagrams/SKILL.md`
- `plugins/kroki-diagrams/references/*`
- `plugins/kroki-diagrams/scripts/render_kroki_diagram.py`
- `plugins/kroki-diagrams/scripts/build_interactive_kroki_html.py`
- `plugins/kroki-diagrams/scripts/build_diagram_index.py`

## Notes

- This repo does not add slash commands yet. It distributes the skill itself in the plugin-style wrapper format.
- The GitHub repository URL above assumes this repo is published as `smoldrago/kroki-diagrams`.

## License

MIT
