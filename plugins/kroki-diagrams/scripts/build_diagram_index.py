#!/usr/bin/env python3
import argparse
import html
import json
import pathlib


META_FILENAME = ".diagram-meta.json"


def prettify_name(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()


def infer_engine_from_source(artifact_dir: pathlib.Path) -> str:
    for source in artifact_dir.glob("source.*"):
        suffix = source.suffix.lower()
        if suffix == ".puml":
            return "plantuml"
        if suffix == ".mmd":
            return "mermaid"
        if suffix == ".dot":
            return "graphviz"
        if suffix == ".erd":
            return "erd"
    return "diagram"


def load_artifact_entry(artifact_dir: pathlib.Path) -> dict[str, str] | None:
    rendered_svg = artifact_dir / "rendered.svg"
    if not rendered_svg.exists():
        return None

    meta_path = artifact_dir / META_FILENAME
    meta: dict[str, str] = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    title = meta.get("title") or prettify_name(artifact_dir.name)
    engine = meta.get("engine") or infer_engine_from_source(artifact_dir)
    tier = meta.get("interactive_tier") or ("full" if (artifact_dir / "interactive.html").exists() else "static")
    summary = meta.get("summary") or f"Rendered with {engine}."

    return {
        "folder": artifact_dir.name,
        "title": title,
        "engine": engine,
        "tier": tier,
        "summary": summary,
        "interactive_href": f"./{artifact_dir.name}/interactive.html",
        "interactive_exists": str((artifact_dir / 'interactive.html').exists()).lower(),
        "svg_href": f"./{artifact_dir.name}/rendered.svg",
    }


def build_index_html(entries: list[dict[str, str]], title: str) -> str:
    list_rows = []
    cards = []
    for entry in entries:
        title_html = html.escape(entry["title"])
        summary_html = html.escape(entry["summary"])
        engine_html = html.escape(entry["engine"])
        tier_html = html.escape(entry["tier"].replace("-", " ").title())
        primary_href = html.escape(
            entry["interactive_href"] if entry["interactive_exists"] == "true" else entry["svg_href"]
        )
        interactive_link = (
            f'<a href="{html.escape(entry["interactive_href"])}" target="_blank" rel="noopener noreferrer">Open interactive</a>'
            if entry["interactive_exists"] == "true"
            else '<span class="link-muted">No interactive view</span>'
        )
        svg_link = (
            f'<a href="{html.escape(entry["svg_href"])}" target="_blank" rel="noopener noreferrer">Open SVG</a>'
        )

        list_rows.append(
            f"""      <article class="list-row">
        <a class="list-main" href="{primary_href}" target="_blank" rel="noopener noreferrer">
          <h2>{title_html}</h2>
          <p>{summary_html}</p>
        </a>
        <div class="list-meta">
          <span class="pill">{engine_html}</span>
          <span class="pill">{tier_html}</span>
        </div>
        <div class="list-links">
          {interactive_link}
          {svg_link}
        </div>
      </article>"""
        )

        cards.append(
            f"""      <article class="card">
        <div class="row">
          <span class="pill">{engine_html}</span>
          <span class="pill">{tier_html}</span>
        </div>
        <h2>{title_html}</h2>
        <p>{summary_html}</p>
        <div class="row">
          {interactive_link}
          {svg_link}
        </div>
        <a class="preview-link" href="{primary_href}" target="_blank" rel="noopener noreferrer" aria-label="Open preview for {title_html}">
          <div class="preview-frame">
            <img class="preview-image" src="{html.escape(entry["svg_href"])}" alt="Preview of {title_html}">
          </div>
        </a>
      </article>"""
        )

    list_rows_html = "\n".join(list_rows)
    cards_html = "\n".join(cards)
    page_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

    :root {{
      --bg: #e7edf4;
      --bg-deep: #d9e2ec;
      --panel: rgba(247, 250, 252, 0.9);
      --panel-strong: rgba(244, 248, 251, 0.94);
      --border: rgba(69, 89, 115, 0.18);
      --text: #142033;
      --muted: #607087;
      --accent: #2f6fed;
      --accent-soft: rgba(47, 111, 237, 0.1);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(57, 135, 255, 0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(18, 35, 58, 0.08), transparent 30%),
        linear-gradient(180deg, var(--bg) 0%, var(--bg-deep) 100%);
    }}

    main {{
      max-width: 1540px;
      margin: 0 auto;
      padding: 20px 18px 34px;
    }}

    .hero {{
      margin-bottom: 20px;
      padding: 24px 24px 22px;
      border-radius: 22px;
      background: linear-gradient(180deg, var(--panel-strong), var(--panel));
      border: 1px solid var(--border);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.72),
        0 18px 42px rgba(31, 45, 61, 0.08);
    }}

    h1 {{
      margin: 0 0 10px;
      font-size: clamp(1.7rem, 2.8vw, 2.6rem);
      line-height: 1.04;
      letter-spacing: -0.03em;
    }}

    .hero p {{
      margin: 0;
      max-width: 980px;
      color: var(--muted);
      font-size: 1.02rem;
      line-height: 1.55;
    }}

    .hero-top {{
      display: flex;
      gap: 16px;
      align-items: flex-start;
      justify-content: space-between;
    }}

    .view-switch {{
      display: inline-flex;
      gap: 6px;
      padding: 6px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.56);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
      flex-shrink: 0;
    }}

    .view-switch button {{
      border: 0;
      border-radius: 10px;
      padding: 10px 14px;
      background: transparent;
      color: var(--muted);
      font-family: "IBM Plex Mono", "SFMono-Regular", "Menlo", monospace;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 120ms ease, color 120ms ease, box-shadow 120ms ease;
    }}

    .view-switch button[aria-pressed="true"] {{
      background: rgba(47, 111, 237, 0.12);
      color: var(--accent);
      box-shadow: inset 0 0 0 1px rgba(47, 111, 237, 0.12);
    }}

    .catalog-list,
    .grid {{
      gap: 20px;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    }}

    .card {{
      display: grid;
      gap: 16px;
      padding: 18px;
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(250, 252, 254, 0.9), rgba(244, 248, 251, 0.88));
      border: 1px solid var(--border);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.72),
        0 14px 30px rgba(31, 45, 61, 0.08);
    }}

    .row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}

    .pill {{
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      border: 1px solid rgba(47, 111, 237, 0.14);
      color: var(--accent);
      font-family: "IBM Plex Mono", "SFMono-Regular", "Menlo", monospace;
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.01em;
    }}

    .catalog-list {{
      display: flex;
      flex-direction: column;
    }}

    .list-row {{
      display: grid;
      grid-template-columns: minmax(0, 1.8fr) auto auto;
      gap: 18px;
      align-items: center;
      padding: 18px 20px;
      border-radius: 20px;
      background: linear-gradient(180deg, rgba(250, 252, 254, 0.9), rgba(244, 248, 251, 0.88));
      border: 1px solid var(--border);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.72),
        0 10px 22px rgba(31, 45, 61, 0.06);
    }}

    .list-main {{
      min-width: 0;
      color: inherit;
      text-decoration: none;
    }}

    .list-main:hover h2 {{
      color: #1f5edb;
    }}

    .list-main p {{
      margin: 6px 0 0;
      color: var(--muted);
      line-height: 1.45;
    }}

    .list-meta,
    .list-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: flex-end;
    }}

    h2 {{
      margin: 0;
      font-size: 1.14rem;
      line-height: 1.2;
    }}

    .card p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
    }}

    a {{
      color: #1f5edb;
      text-decoration: none;
      font-weight: 600;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .link-muted {{
      color: var(--muted);
      font-weight: 500;
    }}

    .preview-link {{
      display: block;
      text-decoration: none;
      color: inherit;
    }}

    .preview-frame {{
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 360px;
      overflow: hidden;
      border: 1px solid rgba(69, 89, 115, 0.14);
      border-radius: 18px;
      background:
        radial-gradient(circle at top left, rgba(255, 255, 255, 0.78), transparent 25%),
        linear-gradient(180deg, #f5f8fb 0%, #edf3f8 100%);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.76),
        0 8px 20px rgba(31, 45, 61, 0.05);
      transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
    }}

    .preview-link:hover .preview-frame {{
      transform: translateY(-1px);
      border-color: rgba(47, 111, 237, 0.22);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.78),
        0 12px 24px rgba(31, 45, 61, 0.08);
    }}

    .preview-image {{
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
      object-position: center center;
      padding: 14px;
    }}

    body[data-view="list"] .grid {{
      display: none;
    }}

    body[data-view="cards"] .catalog-list {{
      display: none;
    }}

    @media (max-width: 720px) {{
      main {{
        padding: 10px 10px 22px;
      }}

      .hero,
      .list-row,
      .card {{
        border-radius: 18px;
      }}

      .hero-top {{
        flex-direction: column;
      }}

      .view-switch {{
        width: 100%;
      }}

      .view-switch button {{
        flex: 1 1 0;
      }}

      .list-row {{
        grid-template-columns: 1fr;
        gap: 14px;
      }}

      .list-meta,
      .list-links {{
        justify-content: flex-start;
      }}

      .card {{
        padding: 16px;
      }}
    }}
  </style>
</head>
<body data-view="list">
  <main>
    <section class="hero">
      <div class="hero-top">
        <div>
          <h1>{page_title}</h1>
          <p>Browse the diagram collection in a compact list or switch to cards when you want visual previews.</p>
        </div>
        <div class="view-switch" aria-label="Diagram index view selector">
          <button type="button" data-view="list" aria-pressed="true">List</button>
          <button type="button" data-view="cards" aria-pressed="false">Cards</button>
        </div>
      </div>
    </section>
    <section class="catalog-list">
{list_rows_html}
    </section>
    <section class="grid">
{cards_html}
    </section>
  </main>
  <script>
    (function () {{
      const storageKey = "kroki-diagrams-index-view";
      const body = document.body;
      const buttons = Array.from(document.querySelectorAll(".view-switch button"));

      function applyView(view) {{
        const nextView = view === "cards" ? "cards" : "list";
        body.dataset.view = nextView;
        buttons.forEach((button) => {{
          button.setAttribute("aria-pressed", String(button.dataset.view === nextView));
        }});
        try {{
          localStorage.setItem(storageKey, nextView);
        }} catch (error) {{
          void error;
        }}
      }}

      let initialView = "list";
      try {{
        const savedView = localStorage.getItem(storageKey);
        if (savedView === "list" || savedView === "cards") {{
          initialView = savedView;
        }}
      }} catch (error) {{
        void error;
      }}

      applyView(initialView);
      buttons.forEach((button) => {{
        button.addEventListener("click", () => applyView(button.dataset.view || "list"));
      }});
    }})();
  </script>
</body>
</html>
"""


def build_diagram_index(root: pathlib.Path, title: str | None = None) -> pathlib.Path:
    entries = []
    for child in sorted(root.iterdir()):
        if child.is_dir():
            entry = load_artifact_entry(child)
            if entry:
                entries.append(entry)

    output_path = root / "index.html"
    page_title = title or "Kroki Interactive Diagrams"
    output_path.write_text(build_index_html(entries, page_title), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an index.html for a directory of diagram artifacts.")
    parser.add_argument("--root", required=True, help="Directory containing one artifact folder per diagram.")
    parser.add_argument("--title", help="Optional page title.")
    args = parser.parse_args()

    root = pathlib.Path(args.root)
    output_path = build_diagram_index(root=root, title=args.title)
    print(f"Index HTML: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
