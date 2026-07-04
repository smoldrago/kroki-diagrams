#!/usr/bin/env python3
"""Build an index.html for a directory of diagram artifacts.

Redesigned "Console" gallery: refined dark (with a light theme toggle), a left
engine-filter rail with counts, live search, grid/list views, per-engine accents,
tier badges, and an empty state.
"""
import argparse
import html
import json
import pathlib


META_FILENAME = ".diagram-meta.json"

# Per-engine accent palette: rgb triplet, hex, default interactive tier.
ENGINE_COLORS: dict[str, tuple[str, str, str]] = {
    "plantuml":   ("168, 85, 247",  "#a855f7", "full"),
    "c4plantuml": ("99, 102, 241",  "#6366f1", "full"),
    "graphviz":   ("251, 191, 36",  "#fbbf24", "full"),
    "mermaid":    ("45, 212, 191",  "#2dd4bf", "best-effort"),
    "erd":        ("251, 113, 133", "#fb7185", "best-effort"),
}
DEFAULT_COLOR = ("99, 102, 241", "#6366f1", "full")
ENGINE_ORDER = ["plantuml", "c4plantuml", "graphviz", "mermaid", "erd"]


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
        "kroki_url": meta.get("kroki_url", ""),
        "interactive_href": f"./{artifact_dir.name}/interactive.html",
        "interactive_exists": str((artifact_dir / 'interactive.html').exists()).lower(),
        "svg_href": f"./{artifact_dir.name}/rendered.svg",
    }


INDEX_STYLE = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }

#app {
  --bg: #0d0f13; --bg2: #0f1116; --bg3: #0b0d11; --panel: #12141a; --panel2: #161922;
  --canvas: #08090c; --border: rgba(255,255,255,.08); --border2: rgba(255,255,255,.06);
  --text: #eceef2; --text2: #a9adb6; --muted: #6b7280; --faint: #565b65;
  --accent: #8b8ff5; --accent-soft: rgba(139,143,245,.14);
  --dot: rgba(255,255,255,.05); --input: #0a0b0e;
  min-height: 100vh; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
}
#app[data-theme="light"] {
  --bg: #eceef2; --bg2: #ffffff; --bg3: #f6f7f9; --panel: #ffffff; --panel2: #eef0f4;
  --canvas: #fafbfc; --border: rgba(15,20,35,.11); --border2: rgba(15,20,35,.07);
  --text: #161a22; --text2: #454b57; --muted: #727884; --faint: #9aa0ac;
  --accent: #4f46e5; --accent-soft: rgba(79,70,229,.1);
  --dot: rgba(15,20,35,.06); --input: #f2f3f6;
}
#app[data-theme="dark"] .kc-prev-img { filter: invert(1) hue-rotate(180deg); }
a { color: inherit; text-decoration: none; }
.mono { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace; }

/* topbar */
.kc-top {
  position: sticky; top: 0; z-index: 20; display: flex; align-items: center; gap: 14px;
  padding: 0 20px; height: 56px; border-bottom: 1px solid var(--border); background: var(--bg2);
}
.kc-logo { display: flex; align-items: center; gap: 9px; }
.kc-logo-mark {
  width: 28px; height: 28px; border-radius: 7px; background: var(--panel2);
  border: 1px solid var(--border); display: flex; align-items: center; justify-content: center;
}
.kc-logo-mark svg { width: 16px; height: 16px; fill: none; stroke: var(--accent); stroke-width: 2; stroke-linecap: round; }
.kc-logo b { font: 600 14px system-ui; color: var(--text); letter-spacing: -.01em; }
.kc-logo span { font: 500 14px system-ui; color: var(--muted); }
.kc-searchbar {
  flex: 1; display: flex; align-items: center; gap: 9px; max-width: 380px; margin-left: 10px;
  padding: 0 12px; height: 34px; background: var(--input); border: 1px solid var(--border); border-radius: 9px;
}
.kc-searchbar svg { width: 14px; height: 14px; fill: none; stroke: var(--faint); stroke-width: 2; flex: none; }
.kc-searchbar input { flex: 1; background: transparent; border: 0; outline: 0; color: var(--text); font: 400 12.5px system-ui; }
.kc-searchbar input::placeholder { color: var(--faint); }
.kc-top-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.kc-viewtoggle { display: flex; background: var(--input); border: 1px solid var(--border); border-radius: 9px; padding: 3px; }
.kc-viewtoggle button {
  width: 30px; height: 26px; border-radius: 6px; background: transparent; border: 0; color: var(--muted);
  display: flex; align-items: center; justify-content: center; cursor: pointer; transition: background .13s, color .13s;
}
.kc-viewtoggle button svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; }
.kc-viewtoggle button.active { background: var(--panel2); color: var(--text); }
.kc-icon {
  width: 34px; height: 32px; border-radius: 9px; background: var(--input); border: 1px solid var(--border);
  color: var(--accent); display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.kc-icon svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

/* layout */
.kc-shell { display: flex; align-items: flex-start; }
.kc-rail {
  width: 212px; flex: none; align-self: stretch; border-right: 1px solid var(--border);
  padding: 20px 16px; background: var(--bg3); min-height: calc(100vh - 56px); position: sticky; top: 56px;
}
.kc-rail-h { font: 600 10px/1 'JetBrains Mono', monospace; letter-spacing: .11em; color: var(--faint); text-transform: uppercase; margin-bottom: 12px; }
.kc-eng { display: flex; align-items: center; gap: 9px; padding: 7px 10px; border-radius: 8px; cursor: pointer; transition: background .13s; }
.kc-eng:hover { background: var(--accent-soft); }
.kc-eng .sw { width: 8px; height: 8px; border-radius: 2px; flex: none; }
.kc-eng .lb { font: 500 12.5px system-ui; flex: 1; color: var(--text2); }
.kc-eng .ct { font: 500 11px/1 'JetBrains Mono', monospace; color: var(--faint); }
.kc-eng.active { background: var(--panel2); }
.kc-eng.active .lb { color: var(--text); }
.kc-rail-sep { height: 1px; background: var(--border); margin: 16px 0; }
.kc-support { display: flex; flex-direction: column; gap: 9px; }
.kc-support div { display: flex; align-items: center; gap: 9px; font: 500 12px system-ui; color: var(--text2); }
.kc-support .full-dot { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; }
.kc-support .best-dot { width: 7px; height: 7px; border-radius: 50%; border: 1px dashed var(--muted); }

.kc-content { flex: 1; padding: 26px 28px; min-width: 0; }
.kc-content-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 18px; gap: 12px; }
.kc-content-head h1 { font: 700 20px system-ui; color: var(--text); letter-spacing: -.02em; }
.kc-content-head .sub { font: 400 12.5px system-ui; color: var(--muted); margin-top: 3px; }
.kc-content-head .sort { font: 500 11px/1 'JetBrains Mono', monospace; color: var(--faint); white-space: nowrap; }

/* gallery */
.kc-gallery.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 15px; }
.kc-gallery.list { display: flex; flex-direction: column; gap: 9px; }

.kc-card {
  position: relative; background: var(--panel); border: 1px solid var(--border2);
  border-left: 2px solid var(--accent); border-radius: 12px; overflow: hidden;
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.kc-card:hover { transform: translateY(-3px); box-shadow: 0 18px 40px -16px rgba(0,0,0,.5); }
.kc-card-link { position: absolute; inset: 0; z-index: 0; border-radius: inherit; }
.kc-card > *:not(.kc-card-link) { position: relative; z-index: 1; pointer-events: none; }
.kc-card a, .kc-card button { pointer-events: auto; }
.kc-card-prev { height: 140px; background: var(--canvas); overflow: hidden; border-bottom: 1px solid var(--border2); }
.kc-prev-img { width: 100%; height: 100%; background-size: contain; background-repeat: no-repeat; background-position: center; padding: 13px; }
.kc-card-main { padding: 14px 15px; }
.kc-card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 7px; }
.kc-card-top h2 { font: 600 13.5px system-ui; color: var(--text); }
.kc-card-sum { font: 400 12px/1.5 system-ui; color: var(--muted); }
.kc-card-foot { display: flex; align-items: center; gap: 9px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border2); }
.kc-card-foot .sp { flex: 1; }

.kc-pill { display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px; border-radius: 999px; font: 600 10px/1 'JetBrains Mono', monospace; white-space: nowrap; }
.kc-pill .d { width: 5px; height: 5px; border-radius: 50%; }
.kc-badge { font: 600 10px/1 'JetBrains Mono', monospace; border-radius: 5px; padding: 3px 8px; }
.kc-badge.full { color: var(--text2); background: var(--panel2); }
.kc-badge.best { color: var(--muted); background: transparent; border: 1px dashed var(--border); }
.kc-svglink { font: 500 11px/1 'JetBrains Mono', monospace; color: var(--faint); }
.kc-svglink:hover { color: var(--text2); }
.kc-copy { display: inline-flex; align-items: center; background: transparent; border: 0; color: var(--faint); cursor: pointer; padding: 2px; }
.kc-copy:hover { color: var(--accent); }
.kc-copy svg { width: 13px; height: 13px; fill: none; stroke: currentColor; stroke-width: 2; }
.kc-open { font: 500 11px/1 'JetBrains Mono', monospace; color: var(--text2); }
.kc-card:hover .kc-open { color: var(--accent); }

/* list overrides */
.kc-gallery.list .kc-card { display: flex; align-items: center; gap: 16px; border-left-width: 4px; padding: 11px 16px 11px 12px; }
.kc-gallery.list .kc-card:hover { transform: translateX(3px); }
.kc-gallery.list .kc-card-prev { width: 104px; height: 62px; flex: none; border: 1px solid var(--border2); border-bottom: 1px solid var(--border2); border-radius: 7px; }
.kc-gallery.list .kc-prev-img { padding: 6px; }
.kc-gallery.list .kc-card-main { flex: 1; min-width: 0; padding: 0; display: flex; align-items: center; gap: 14px; }
.kc-gallery.list .kc-card-top { margin: 0; flex: 1; min-width: 0; }
.kc-gallery.list .kc-card-top h2 { flex: none; }
.kc-gallery.list .kc-card-sum { display: none; }
.kc-gallery.list .kc-card-foot { margin: 0; padding: 0; border: 0; flex: none; }
.kc-gallery.list .kc-card-foot .sp, .kc-gallery.list .kc-open, .kc-gallery.list .kc-svglink { display: none; }

/* empty state */
.kc-empty {
  display: none; flex-direction: column; align-items: center; justify-content: center; text-align: center;
  padding: 70px 20px; border: 1px dashed var(--border); border-radius: 16px; background: var(--panel);
}
.kc-empty.show { display: flex; }
.kc-empty-mark { width: 52px; height: 52px; border-radius: 14px; background: var(--panel2); border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; margin-bottom: 16px; }
.kc-empty-mark svg { width: 24px; height: 24px; fill: none; stroke: var(--muted); stroke-width: 1.7; stroke-linecap: round; }
.kc-empty h3 { font: 600 15px system-ui; color: var(--text); }
.kc-empty p { font: 400 12.5px/1.6 system-ui; color: var(--muted); max-width: 320px; margin-top: 6px; }
.kc-empty button { margin-top: 18px; font: 600 12px system-ui; color: #fff; background: var(--accent); border: 0; border-radius: 9px; padding: 9px 18px; cursor: pointer; }

/* toast */
.kc-toast {
  position: fixed; left: 50%; bottom: 26px; transform: translateX(-50%) translateY(12px); z-index: 60;
  display: flex; align-items: center; gap: 9px; padding: 11px 17px; background: var(--panel);
  border: 1px solid var(--border); border-radius: 11px; box-shadow: 0 14px 40px rgba(0,0,0,.4);
  font: 600 12.5px system-ui; color: var(--text); opacity: 0; pointer-events: none; transition: opacity .2s, transform .2s;
}
.kc-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.kc-toast .d { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; }

@media (max-width: 720px) {
  .kc-rail { display: none; }
  .kc-searchbar { max-width: none; }
  .kc-gallery.grid { grid-template-columns: 1fr; }
}
"""


INDEX_SCRIPT = """
(function () {
  const app = document.getElementById("app");
  const THEME_KEY = "kroki-diagrams-theme";
  const VIEW_KEY = "kroki-diagrams-index-view";

  // theme
  try { const s = localStorage.getItem(THEME_KEY); if (s === "light" || s === "dark") app.setAttribute("data-theme", s); } catch (e) {}
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const next = app.getAttribute("data-theme") === "light" ? "dark" : "light";
    app.setAttribute("data-theme", next);
    try { localStorage.setItem(THEME_KEY, next); } catch (e) {}
  });

  // view (grid / list)
  const gallery = document.getElementById("gallery");
  const btnGrid = document.getElementById("view-grid");
  const btnList = document.getElementById("view-list");
  function applyView(v) {
    const grid = v === "grid";
    gallery.classList.toggle("grid", grid);
    gallery.classList.toggle("list", !grid);
    btnGrid.classList.toggle("active", grid);
    btnList.classList.toggle("active", !grid);
    try { localStorage.setItem(VIEW_KEY, v); } catch (e) {}
  }
  let initView = "grid";
  try { const s = localStorage.getItem(VIEW_KEY); if (s === "grid" || s === "list") initView = s; } catch (e) {}
  applyView(initView);
  btnGrid.addEventListener("click", () => applyView("grid"));
  btnList.addEventListener("click", () => applyView("list"));

  // search + engine filter
  const cards = Array.from(document.querySelectorAll(".kc-card"));
  const searchEl = document.getElementById("search");
  const railItems = Array.from(document.querySelectorAll(".kc-eng"));
  const empty = document.getElementById("empty");
  const emptyText = document.getElementById("empty-text");
  const countEl = document.getElementById("shown-count");
  let activeEngine = "all";

  function refresh() {
    const q = searchEl.value.trim().toLowerCase();
    let shown = 0;
    cards.forEach((c) => {
      const okE = activeEngine === "all" || c.dataset.engine === activeEngine;
      const hay = (c.dataset.title + " " + c.dataset.engine + " " + c.dataset.summary + " " + c.dataset.folder).toLowerCase();
      const okQ = !q || hay.includes(q);
      const show = okE && okQ;
      c.style.display = show ? "" : "none";
      if (show) shown++;
    });
    countEl.textContent = shown + (shown === 1 ? " shown" : " shown");
    empty.classList.toggle("show", shown === 0);
    if (shown === 0) {
      const bits = [];
      if (q) bits.push('\u201c' + q + '\u201d');
      if (activeEngine !== "all") bits.push("in " + activeEngine);
      emptyText.textContent = "Nothing matches " + (bits.join(" ") || "the current filters") + ".";
    }
  }
  searchEl.addEventListener("input", refresh);
  railItems.forEach((it) => it.addEventListener("click", () => {
    activeEngine = it.dataset.engine;
    railItems.forEach((r) => r.classList.toggle("active", r === it));
    refresh();
  }));
  document.getElementById("reset-filters").addEventListener("click", () => {
    searchEl.value = ""; activeEngine = "all";
    railItems.forEach((r) => r.classList.toggle("active", r.dataset.engine === "all"));
    refresh();
  });

  // copy kroki url
  const toast = document.getElementById("toast");
  document.querySelectorAll(".kc-copy").forEach((b) => b.addEventListener("click", (e) => {
    e.preventDefault(); e.stopPropagation();
    const url = b.dataset.url;
    if (url && navigator.clipboard) navigator.clipboard.writeText(url).catch(() => {});
    toast.classList.add("show");
    clearTimeout(window.__kcToast);
    window.__kcToast = setTimeout(() => toast.classList.remove("show"), 1900);
  }));

  refresh();
})();
"""


def build_index_html(entries: list[dict[str, str]], title: str) -> str:
    # per-engine counts (only engines that appear)
    counts: dict[str, int] = {}
    full_n = 0
    for e in entries:
        counts[e["engine"]] = counts.get(e["engine"], 0) + 1
        if e["tier"] == "full":
            full_n += 1
    best_n = len(entries) - full_n

    # engine rail
    rail_rows = ['<div class="kc-eng active" data-engine="all"><span class="sw" style="background:var(--text2)"></span><span class="lb">All</span><span class="ct">%d</span></div>' % len(entries)]
    ordered = [k for k in ENGINE_ORDER if k in counts] + [k for k in counts if k not in ENGINE_ORDER]
    for eng in ordered:
        rgb, hexc, _ = ENGINE_COLORS.get(eng, DEFAULT_COLOR)
        rail_rows.append(
            '<div class="kc-eng" data-engine="%s"><span class="sw" style="background:%s"></span>'
            '<span class="lb">%s</span><span class="ct">%d</span></div>'
            % (html.escape(eng), hexc, html.escape(eng), counts[eng])
        )
    rail_html = "\n        ".join(rail_rows)

    # cards
    cards = []
    for entry in entries:
        title_html = html.escape(entry["title"])
        summary_html = html.escape(entry["summary"])
        engine_html = html.escape(entry["engine"])
        tier = entry["tier"]
        rgb, hexc, _ = ENGINE_COLORS.get(entry["engine"], DEFAULT_COLOR)

        interactive_href = html.escape(entry["interactive_href"]) if entry["interactive_exists"] == "true" else ""
        svg_href = html.escape(entry["svg_href"])
        primary_href = interactive_href or svg_href

        badge = ('<span class="kc-badge full">Full</span>' if tier == "full"
                 else '<span class="kc-badge best">Best effort</span>')

        copy_btn = ""
        if entry.get("kroki_url"):
            copy_btn = (
                '<button class="kc-copy" type="button" title="Copy Kroki URL" data-url="%s">'
                '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="2"/>'
                '<path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg></button>'
                % html.escape(entry["kroki_url"])
            )

        cards.append(
            '      <article class="kc-card" data-title="%s" data-engine="%s" data-summary="%s" data-folder="%s" style="border-left-color:%s">\n'
            '        <a class="kc-card-link" href="%s" target="_blank" rel="noopener noreferrer" aria-label="Open %s"></a>\n'
            '        <div class="kc-card-prev"><div class="kc-prev-img" style="background-image:url(%s)"></div></div>\n'
            '        <div class="kc-card-main">\n'
            '          <div class="kc-card-top"><h2>%s</h2><span class="kc-pill" style="background:rgba(%s,.13);border:1px solid rgba(%s,.3);color:%s"><span class="d" style="background:%s"></span>%s</span></div>\n'
            '          <p class="kc-card-sum">%s</p>\n'
            '          <div class="kc-card-foot">%s<span class="sp"></span>%s<a class="kc-svglink" href="%s" target="_blank" rel="noopener noreferrer">svg</a><span class="kc-open">open &rarr;</span></div>\n'
            '        </div>\n'
            '      </article>'
            % (
                title_html, engine_html, summary_html, html.escape(entry["folder"]), hexc,
                primary_href, title_html,
                svg_href,
                title_html, rgb, rgb, hexc, hexc, engine_html,
                summary_html,
                badge, copy_btn, svg_href,
            )
        )
    cards_html = "\n".join(cards)
    n = len(entries)

    shell = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>__STYLE__</style>
</head>
<body>
  <div id="app" data-theme="dark">
    <div class="kc-top">
      <a class="kc-logo" href=".">
        <span class="kc-logo-mark"><svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7 11.3 17 6.7M7 12.7 17 17.3"/></svg></span>
        <b>kroki</b><span>diagrams</span>
      </a>
      <label class="kc-searchbar">
        <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
        <input id="search" placeholder="Search diagrams\u2026" autocomplete="off">
      </label>
      <div class="kc-top-right">
        <div class="kc-viewtoggle">
          <button id="view-grid" class="active" type="button" aria-label="Grid view"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg></button>
          <button id="view-list" type="button" aria-label="List view"><svg viewBox="0 0 24 24"><path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/></svg></button>
        </div>
        <button class="kc-icon" id="theme-toggle" type="button" aria-label="Toggle theme"><svg viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg></button>
      </div>
    </div>
    <div class="kc-shell">
      <aside class="kc-rail">
        <div class="kc-rail-h">Engines</div>
        __RAIL__
        <div class="kc-rail-sep"></div>
        <div class="kc-rail-h">Support</div>
        <div class="kc-support">
          <div><span class="full-dot"></span>Full &middot; __FULL_N__</div>
          <div><span class="best-dot"></span>Best effort &middot; __BEST_N__</div>
        </div>
      </aside>
      <main class="kc-content">
        <div class="kc-content-head">
          <div><h1>Diagram collection</h1><div class="sub">docs/diagrams &middot; <span id="shown-count">__N__ shown</span></div></div>
          <div class="sort">sorted: recent</div>
        </div>
        <div class="kc-empty" id="empty">
          <div class="kc-empty-mark"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></div>
          <h3>No diagrams match</h3>
          <p id="empty-text"></p>
          <button id="reset-filters" type="button">Reset filters</button>
        </div>
        <div class="kc-gallery grid" id="gallery">
__CARDS__
        </div>
      </main>
    </div>
    <div class="kc-toast" id="toast"><span class="d"></span>Kroki URL copied to clipboard</div>
  </div>
  <script>__SCRIPT__</script>
</body>
</html>
"""

    out = shell
    for token, value in {
        "__STYLE__": INDEX_STYLE,
        "__SCRIPT__": INDEX_SCRIPT,
        "__RAIL__": rail_html,
        "__CARDS__": cards_html,
        "__FULL_N__": str(full_n),
        "__BEST_N__": str(best_n),
        "__N__": str(n),
    }.items():
        out = out.replace(token, value)
    out = out.replace("__TITLE__", html.escape(title))
    return out


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
