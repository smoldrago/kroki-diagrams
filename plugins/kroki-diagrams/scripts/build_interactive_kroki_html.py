#!/usr/bin/env python3
"""Wrap a Kroki SVG in an interactive HTML viewer.

Redesigned "Console" viewer: refined dark (with a light theme toggle), calm
monochrome node highlighting, a live node list, minimap, pan/zoom, and a
Copy-Kroki-URL action. All SVG annotation logic is unchanged.
"""
import argparse
import html
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
NS = {"svg": SVG_NS}

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)


def clean_svg_text(svg_text: str) -> str:
    svg_text = re.sub(r"<\?xml[^>]*\?>", "", svg_text, flags=re.IGNORECASE)
    svg_text = re.sub(r"<!DOCTYPE[^>]*>", "", svg_text, flags=re.IGNORECASE)
    svg_text = re.sub(r"<\?.*?\?>", "", svg_text, flags=re.DOTALL)
    return svg_text.strip()


def append_class(element: ET.Element, class_name: str) -> None:
    classes = set(filter(None, (element.get("class") or "").split()))
    classes.add(class_name)
    element.set("class", " ".join(sorted(classes)))


def soften_svg_background(root: ET.Element) -> None:
    style = root.get("style")
    if style:
        cleaned = re.sub(r"background\s*:\s*[^;]+;?", "", style, flags=re.IGNORECASE).strip()
        root.set("style", cleaned)

    view_box = root.get("viewBox")
    if not view_box:
        return

    try:
        _, _, width, height = [float(part) for part in view_box.replace(",", " ").split()]
    except ValueError:
        return

    parent_map = {child: parent for parent in root.iter() for child in parent}

    rects = root.findall(".//svg:rect", NS)
    for rect in rects:
        try:
            rect_width = float(rect.get("width", "0"))
            rect_height = float(rect.get("height", "0"))
            rect_x = float(rect.get("x", "0"))
            rect_y = float(rect.get("y", "0"))
        except ValueError:
            continue

        style_value = rect.get("style", "")
        fill = rect.get("fill", "").lower()
        has_no_stroke = "stroke:none" in style_value.replace(" ", "").lower()
        fills_background = (
            rect_x == 0
            and rect_y == 0
            and abs(rect_width - width) <= max(2.0, width * 0.02)
            and abs(rect_height - height) <= max(2.0, height * 0.02)
        )

        if fills_background and (fill or has_no_stroke):
            parent = parent_map.get(rect)
            if parent is not None:
                parent.remove(rect)
            break

    polygons = root.findall(".//svg:polygon", NS)
    for polygon in polygons:
        points_value = polygon.get("points", "").strip()
        if not points_value:
            continue

        coords: list[tuple[float, float]] = []
        try:
            for pair in points_value.split():
                x_text, y_text = pair.split(",")
                coords.append((float(x_text), float(y_text)))
        except ValueError:
            continue

        if len(coords) < 4:
            continue

        xs = [x for x, _ in coords]
        ys = [y for _, y in coords]
        poly_width = max(xs) - min(xs)
        poly_height = max(ys) - min(ys)
        fill = polygon.get("fill", "").lower()
        style_value = polygon.get("style", "")
        has_no_stroke = "stroke:none" in style_value.replace(" ", "").lower()
        fills_background = (
            abs(poly_width - width) <= max(6.0, width * 0.03)
            and abs(poly_height - height) <= max(6.0, height * 0.03)
        )

        if fills_background and (fill or has_no_stroke):
            parent = parent_map.get(polygon)
            if parent is not None:
                parent.remove(polygon)
            break


def annotate_graphviz_like(root: ET.Element) -> tuple[int, int]:
    node_count = 0
    edge_count = 0

    for group in root.findall(".//svg:g", NS):
        classes = set((group.get("class") or "").split())
        title = group.find("svg:title", NS)
        title_text = (title.text or "").strip() if title is not None else ""

        if "node" in classes and title_text:
            group.set("data-node-id", title_text)
            append_class(group, "interactive-node")
            node_count += 1
            continue

        if "edge" not in classes or not title_text:
            continue

        match = re.match(r"^(.*?)\s*(-+>|--)\s*(.*?)$", title_text)
        if not match:
            continue

        source, operator, target = match.groups()
        group.set("data-edge-source", source.strip())
        group.set("data-edge-target", target.strip())
        group.set("data-edge-kind", "directed" if ">" in operator else "undirected")
        append_class(group, "interactive-edge")
        edge_count += 1

    return node_count, edge_count


def annotate_mermaid(root: ET.Element) -> tuple[int, int]:
    node_count = 0
    edge_count = 0

    for group in root.findall(".//svg:g", NS):
        classes = set((group.get("class") or "").split())
        group_id = group.get("id") or ""
        if "node" not in classes:
            continue

        match = re.match(r"^flowchart-(.+)-\d+$", group_id)
        if not match:
            continue

        group.set("data-node-id", match.group(1))
        append_class(group, "interactive-node")
        node_count += 1

    edge_candidates = list(root.findall(".//svg:path", NS)) + list(root.findall(".//svg:g", NS))
    for element in edge_candidates:
        classes = set((element.get("class") or "").split())
        if "flowchart-link" not in classes:
            continue

        edge_id = element.get("id") or ""
        match = re.match(r"^L_([^_]+)_([^_]+)_\d+$", edge_id)
        if not match:
            continue

        source, target = match.groups()
        directed = "marker-end" in element.attrib or "marker-start" in element.attrib
        element.set("data-edge-source", source)
        element.set("data-edge-target", target)
        element.set("data-edge-kind", "directed" if directed else "undirected")
        append_class(element, "interactive-edge")
        edge_count += 1

    return node_count, edge_count


def annotate_sequence(root: ET.Element) -> tuple[int, int]:
    node_ids: set[str] = set()
    edge_count = 0

    for group in root.findall(".//svg:g", NS):
        classes = set((group.get("class") or "").split())

        if "participant-head" in classes or "participant-lifeline" in classes:
            node_id = group.get("data-entity-uid")
            if not node_id:
                continue
            group.set("data-node-id", node_id)
            append_class(group, "interactive-node")
            node_ids.add(node_id)
            continue

        if "message" not in classes:
            continue

        source = group.get("data-entity-1")
        target = group.get("data-entity-2")
        if not source or not target:
            continue

        edge_kind = "undirected" if source == target else "directed"
        group.set("data-edge-source", source)
        group.set("data-edge-target", target)
        group.set("data-edge-kind", edge_kind)
        append_class(group, "interactive-edge")
        edge_count += 1

    return len(node_ids), edge_count


def annotate_plantuml_description(root: ET.Element) -> tuple[int, int]:
    node_count = 0
    edge_count = 0

    for group in root.findall(".//svg:g", NS):
        classes = set((group.get("class") or "").split())

        if "entity" in classes:
            node_id = group.get("id")
            if not node_id:
                continue
            group.set("data-node-id", node_id)
            append_class(group, "interactive-node")
            node_count += 1
            continue

        if "link" not in classes:
            continue

        source = group.get("data-entity-1")
        target = group.get("data-entity-2")
        if not source or not target:
            continue

        group.set("data-edge-source", source)
        group.set("data-edge-target", target)
        group.set("data-edge-kind", "directed")
        append_class(group, "interactive-edge")
        edge_count += 1

    return node_count, edge_count


def annotate_svg(engine: str, svg_text: str) -> tuple[str, dict[str, str | int]]:
    cleaned = clean_svg_text(svg_text)
    root = ET.fromstring(cleaned)
    soften_svg_background(root)

    if engine == "graphviz":
        node_count, edge_count = annotate_graphviz_like(root)
        tier = "full" if edge_count else "best-effort"
    elif engine == "erd":
        node_count, edge_count = annotate_graphviz_like(root)
        tier = "best-effort"
    elif engine == "mermaid":
        node_count, edge_count = annotate_mermaid(root)
        tier = "best-effort"
    elif engine == "plantuml" and root.get("data-diagram-type") == "SEQUENCE":
        node_count, edge_count = annotate_sequence(root)
        tier = "full"
    elif engine in {"plantuml", "c4plantuml"}:
        node_count, edge_count = annotate_plantuml_description(root)
        tier = "full" if edge_count else "best-effort"
    else:
        node_count = 0
        edge_count = 0
        tier = "limited"

    root.set("data-interactive-engine", engine)
    root.set("data-interactive-tier", tier)
    return ET.tostring(root, encoding="unicode"), {
        "engine": engine,
        "nodes": node_count,
        "edges": edge_count,
        "tier": tier,
    }


# Per-engine accent colour (matches the gallery index).
ENGINE_COLORS: dict[str, tuple[str, str]] = {
    "plantuml":   ("168, 85, 247",  "#a855f7"),
    "c4plantuml": ("99, 102, 241",  "#6366f1"),
    "graphviz":   ("251, 191, 36",  "#fbbf24"),
    "mermaid":    ("45, 212, 191",  "#2dd4bf"),
    "erd":        ("251, 113, 133", "#fb7185"),
}


VIEWER_STYLE = """
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
  display: flex; flex-direction: column; height: 100vh; overflow: hidden;
}
#app[data-theme="light"] {
  --bg: #eceef2; --bg2: #ffffff; --bg3: #f6f7f9; --panel: #ffffff; --panel2: #eef0f4;
  --canvas: #fafbfc; --border: rgba(15,20,35,.11); --border2: rgba(15,20,35,.07);
  --text: #161a22; --text2: #454b57; --muted: #727884; --faint: #9aa0ac;
  --accent: #4f46e5; --accent-soft: rgba(79,70,229,.1);
  --dot: rgba(15,20,35,.06); --input: #f2f3f6;
}
#app[data-theme="dark"] #content svg,
#app[data-theme="dark"] #mini svg { filter: invert(1) hue-rotate(180deg); }

a { color: inherit; text-decoration: none; }
.mono { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace; }

/* nav */
.kc-nav {
  display: flex; align-items: center; gap: 11px; padding: 0 18px; height: 52px;
  border-bottom: 1px solid var(--border); background: var(--bg2); flex: none;
}
.kc-back {
  display: inline-flex; align-items: center; gap: 6px; font: 500 12px/1 'JetBrains Mono', monospace;
  color: var(--text2); padding: 6px 11px; background: var(--input);
  border: 1px solid var(--border); border-radius: 8px; cursor: pointer;
  transition: background .15s, color .15s;
}
.kc-back:hover { color: var(--text); background: var(--panel2); }
.kc-back svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 2.2; stroke-linecap: round; }
.kc-sep { color: var(--faint); }
.kc-title { font: 600 13.5px system-ui; color: var(--text); letter-spacing: -.01em; }
.kc-pill {
  display: inline-flex; align-items: center; gap: 5px; padding: 2px 9px; border-radius: 999px;
  font: 600 10px/1 'JetBrains Mono', monospace;
}
.kc-pill .d { width: 5px; height: 5px; border-radius: 50%; }
.kc-nav-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.kc-btn {
  display: inline-flex; align-items: center; gap: 7px; font: 600 11px/1 'JetBrains Mono', monospace;
  color: var(--text); padding: 7px 12px; background: var(--panel2);
  border: 1px solid var(--border); border-radius: 8px; cursor: pointer;
  transition: background .15s, border-color .15s;
}
.kc-btn:hover { border-color: var(--accent); }
.kc-btn svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 2; }
.kc-icon {
  width: 32px; height: 31px; border-radius: 8px; background: var(--input);
  border: 1px solid var(--border); color: var(--accent); display: flex;
  align-items: center; justify-content: center; cursor: pointer;
}
.kc-icon svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

/* body */
.kc-body { flex: 1; display: flex; min-height: 0; }

.kc-viewport {
  flex: 1; position: relative; overflow: hidden; background: var(--canvas);
  background-image: radial-gradient(var(--dot) 1px, transparent 1px); background-size: 22px 22px;
  cursor: grab; touch-action: none; user-select: none;
}
.kc-viewport.dragging { cursor: grabbing; }
.kc-content { position: absolute; top: 0; left: 0; transform-origin: 0 0; will-change: transform; }
.kc-content svg { display: block; width: max-content; max-width: none; height: auto; overflow: visible; background: transparent !important; }
.kc-hint {
  position: absolute; left: 18px; top: 15px; font: 500 11px/1 'JetBrains Mono', monospace;
  color: var(--faint); pointer-events: none;
}
.kc-toolbar {
  position: absolute; left: 18px; bottom: 18px; display: flex; gap: 5px; padding: 5px;
  background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,.28);
}
.kc-toolbar button {
  height: 30px; border-radius: 6px; background: var(--panel2); border: 0;
  font: 600 11px/1 'JetBrains Mono', monospace; color: var(--text2); cursor: pointer;
  transition: background .12s, color .12s;
}
.kc-toolbar button.sq { width: 32px; font-size: 16px; }
.kc-toolbar button:not(.sq) { padding: 0 12px; }
.kc-toolbar button:hover { background: var(--accent-soft); color: var(--text); }
.kc-status {
  position: absolute; right: 18px; bottom: 18px; font: 500 11px/1 'JetBrains Mono', monospace;
  color: var(--faint); background: var(--panel); border: 1px solid var(--border);
  border-radius: 999px; padding: 5px 12px; pointer-events: none;
}

/* panel */
.kc-panel {
  width: 272px; flex: none; border-left: 1px solid var(--border); background: var(--bg3);
  display: flex; flex-direction: column; min-height: 0;
}
.kc-panel-head {
  padding: 14px 14px 10px; font: 600 10px/1 'JetBrains Mono', monospace;
  letter-spacing: .11em; text-transform: uppercase; color: var(--faint);
  display: flex; align-items: center; gap: 8px;
}
.kc-panel-head b { color: var(--text2); font-weight: 600; }
.kc-search { padding: 0 12px 11px; border-bottom: 1px solid var(--border2); }
.kc-search label { display: flex; align-items: center; gap: 8px; padding: 0 11px; height: 32px; background: var(--input); border: 1px solid var(--border); border-radius: 8px; }
.kc-search svg { width: 12px; height: 12px; fill: none; stroke: var(--faint); stroke-width: 2; flex: none; }
.kc-search input { flex: 1; background: transparent; border: 0; outline: 0; color: var(--text); font: 400 12px system-ui; }
.kc-search input::placeholder { color: var(--faint); }
.kc-node-list { flex: 1; overflow: auto; padding: 6px 8px; min-height: 0; }
.kc-node {
  display: flex; align-items: center; gap: 9px; padding: 8px 10px; border-radius: 8px;
  border: 1px solid transparent; cursor: pointer; transition: background .13s;
}
.kc-node:hover { background: var(--accent-soft); }
.kc-node .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); flex: none; transition: background .13s; }
.kc-node .name { font: 500 12px system-ui; flex: 1; color: var(--text2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kc-node .ct { font: 500 10px/1 'JetBrains Mono', monospace; color: var(--faint); }
.kc-node.sel { background: var(--panel2); border-color: var(--accent-soft); }
.kc-node.sel .dot { background: var(--accent); }
.kc-node.sel .name { color: var(--text); }
.kc-empty { padding: 26px 16px; text-align: center; font: 500 12px/1.6 system-ui; color: var(--muted); }

.kc-mini-wrap { padding: 12px; border-top: 1px solid var(--border2); }
.kc-mini {
  position: relative; border: 1px solid var(--border); border-radius: 9px; height: 100px;
  background: var(--canvas); overflow: hidden;
}
.kc-mini svg { position: absolute; inset: 0; width: 100%; height: 100%; padding: 8px; opacity: .55; }
.kc-mini-rect { position: absolute; border: 1.5px solid var(--accent); border-radius: 3px; background: var(--accent-soft); pointer-events: none; }
.kc-mini-label { font: 600 9.5px/1 'JetBrains Mono', monospace; letter-spacing: .1em; text-transform: uppercase; color: var(--faint); margin-top: 8px; }

/* toast */
.kc-toast {
  position: fixed; left: 50%; bottom: 26px; transform: translateX(-50%) translateY(12px);
  z-index: 60; display: flex; align-items: center; gap: 9px; padding: 11px 17px;
  background: var(--panel); border: 1px solid var(--border); border-radius: 11px;
  box-shadow: 0 14px 40px rgba(0,0,0,.4); font: 600 12.5px system-ui; color: var(--text);
  opacity: 0; pointer-events: none; transition: opacity .2s, transform .2s;
}
.kc-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.kc-toast .d { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; }

/* interactive highlighting — calm monochrome */
.interactive-node { cursor: pointer; transition: opacity .16s ease; }
.interactive-edge { transition: opacity .16s ease; }
.interactive-node.is-dimmed, .interactive-edge.is-dimmed { opacity: .24; }
.interactive-node.is-active, .interactive-node.is-connected, .interactive-edge.is-connected { opacity: 1; }
.interactive-node.is-active rect, .interactive-node.is-active ellipse, .interactive-node.is-active circle,
.interactive-node.is-active polygon, .interactive-node.is-active path {
  stroke: var(--accent) !important; stroke-width: 2.1px !important;
}
.interactive-node.is-connected rect, .interactive-node.is-connected ellipse, .interactive-node.is-connected circle,
.interactive-node.is-connected polygon, .interactive-node.is-connected path {
  stroke: var(--accent) !important; stroke-width: 1.6px !important;
}
.interactive-edge.is-connected path, .interactive-edge.is-connected line, .interactive-edge.is-connected polyline {
  stroke: var(--accent) !important; stroke-width: 2px !important; stroke-linecap: round;
}
.interactive-edge.is-connected polygon { stroke: var(--accent) !important; fill: var(--accent) !important; }
.interactive-edge.is-connected text, .interactive-edge.is-connected tspan {
  fill: var(--accent) !important; stroke: none !important; font-weight: 700 !important;
}
.interactive-edge.edge-flow-forward path, .interactive-edge.edge-flow-forward line, .interactive-edge.edge-flow-forward polyline {
  stroke-dasharray: 10 7; animation: kc-flow-f 900ms linear infinite;
}
.interactive-edge.edge-flow-reverse path, .interactive-edge.edge-flow-reverse line, .interactive-edge.edge-flow-reverse polyline {
  stroke-dasharray: 10 7; animation: kc-flow-r 900ms linear infinite;
}
.interactive-edge.edge-neutral path, .interactive-edge.edge-neutral line, .interactive-edge.edge-neutral polyline {
  stroke-dasharray: 8 7; animation: kc-flow-n 1200ms ease-in-out infinite;
}
@keyframes kc-flow-f { to { stroke-dashoffset: -17; } }
@keyframes kc-flow-r { to { stroke-dashoffset: 17; } }
@keyframes kc-flow-n { 0% { stroke-dashoffset: 0; } 50% { stroke-dashoffset: 9; } 100% { stroke-dashoffset: 18; } }

@media (max-width: 760px) {
  .kc-panel { display: none; }
}
"""


VIEWER_SCRIPT = """
(function () {
  const app = document.getElementById("app");
  const viewport = document.getElementById("viewport");
  const content = document.getElementById("content");
  const statusEl = document.getElementById("status");
  const svg = content.querySelector("svg");
  const nodeListEl = document.getElementById("node-list");
  const nodeSearch = document.getElementById("node-search");
  const nodeCountEl = document.getElementById("node-count");
  const mini = document.getElementById("mini");
  const miniRect = document.getElementById("mini-rect");
  const themeToggle = document.getElementById("theme-toggle");
  const copyBtn = document.getElementById("copy-url");
  const toast = document.getElementById("toast");
  const KROKI_URL = window.__KROKI_URL__ || "";
  const THEME_KEY = "kroki-viewer-theme";

  // theme
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "light" || saved === "dark") app.setAttribute("data-theme", saved);
  } catch (e) {}
  themeToggle.addEventListener("click", () => {
    const next = app.getAttribute("data-theme") === "light" ? "dark" : "light";
    app.setAttribute("data-theme", next);
    try { localStorage.setItem(THEME_KEY, next); } catch (e) {}
  });

  // copy url
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      if (KROKI_URL && navigator.clipboard) navigator.clipboard.writeText(KROKI_URL).catch(() => {});
      toast.classList.add("show");
      clearTimeout(window.__kcToast);
      window.__kcToast = setTimeout(() => toast.classList.remove("show"), 1900);
    });
  }

  if (!svg) return;

  const nodes = Array.from(svg.querySelectorAll("[data-node-id]"));
  const edges = Array.from(svg.querySelectorAll("[data-edge-source][data-edge-target]"));

  const PADDING = 40;
  const SCALE_STEP = 1.16;
  const MIN_SCALE = 0.08;
  const MAX_SCALE = 3.5;

  const rawBounds = svg.getBBox();
  const bounds = (rawBounds.width > 0 && rawBounds.height > 0) ? rawBounds : null;

  // minimap clone (before we mutate the live svg transform)
  if (bounds) {
    const clone = svg.cloneNode(true);
    clone.removeAttribute("style");
    clone.removeAttribute("width");
    clone.removeAttribute("height");
    clone.setAttribute("viewBox", bounds.x + " " + bounds.y + " " + bounds.width + " " + bounds.height);
    clone.setAttribute("preserveAspectRatio", "xMidYMid meet");
    clone.querySelectorAll("[data-node-id],[data-edge-source]").forEach((el) => {
      el.classList.remove("interactive-node", "interactive-edge");
      el.style.pointerEvents = "none";
    });
    mini.insertBefore(clone, miniRect);
  }

  let scale = 1, tx = 0, ty = 0, bw = 1, bh = 1;

  if (bounds) {
    svg.style.transformOrigin = "top left";
    svg.style.transform = "translate(" + (-bounds.x) + "px," + (-bounds.y) + "px)";
    content.style.width = bounds.width + "px";
    content.style.height = bounds.height + "px";
    bw = bounds.width; bh = bounds.height;
  }

  const clamp = (v) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, v));

  function apply() {
    content.style.transform = "translate(" + tx + "px," + ty + "px) scale(" + scale + ")";
    statusEl.textContent = "Zoom " + Math.round(scale * 100) + "%";
    updateMini();
  }

  function updateMini() {
    if (!miniRect || !mini || !bw) return;
    const mb = mini.getBoundingClientRect();
    const pad = 8;
    const availW = mb.width - pad * 2, availH = mb.height - pad * 2;
    const s = Math.min(availW / bw, availH / bh);
    const dispW = bw * s, dispH = bh * s;
    const offX = pad + (availW - dispW) / 2;
    const offY = pad + (availH - dispH) / 2;
    const vr = viewport.getBoundingClientRect();
    const vx = -tx / scale, vy = -ty / scale;
    const vw = vr.width / scale, vh = vr.height / scale;
    let rx = offX + (vx / bw) * dispW;
    let ry = offY + (vy / bh) * dispH;
    let rw = (vw / bw) * dispW;
    let rh = (vh / bh) * dispH;
    // clamp to displayed area
    const left = Math.max(offX, rx), top = Math.max(offY, ry);
    const right = Math.min(offX + dispW, rx + rw), bottom = Math.min(offY + dispH, ry + rh);
    miniRect.style.left = left + "px";
    miniRect.style.top = top + "px";
    miniRect.style.width = Math.max(0, right - left) + "px";
    miniRect.style.height = Math.max(0, bottom - top) + "px";
  }

  function fit() {
    const r = viewport.getBoundingClientRect();
    scale = clamp(Math.min((r.width - PADDING * 2) / bw, (r.height - PADDING * 2) / bh));
    tx = (r.width - bw * scale) / 2;
    ty = (r.height - bh * scale) / 2;
    apply();
    statusEl.textContent = "Fit " + Math.round(scale * 100) + "%";
  }

  function zoomAt(factor, cx, cy) {
    const r = viewport.getBoundingClientRect();
    const px = cx - r.left, py = cy - r.top;
    const ns = clamp(scale * factor);
    const k = ns / scale;
    tx = px - (px - tx) * k;
    ty = py - (py - ty) * k;
    scale = ns; apply();
  }

  function actual() {
    const r = viewport.getBoundingClientRect();
    scale = 1; tx = (r.width - bw) / 2; ty = (r.height - bh) / 2; apply();
  }

  // ── highlighting ──
  const nodeMap = new Map();
  const centerCache = new Map();
  nodes.forEach((n) => {
    const id = n.dataset.nodeId;
    if (!nodeMap.has(id)) nodeMap.set(id, []);
    nodeMap.get(id).push(n);
  });

  function center(id) {
    if (centerCache.has(id)) return centerCache.get(id);
    const els = nodeMap.get(id) || [];
    let x = 0, y = 0, c = 0;
    els.forEach((el) => { const b = el.getBBox(); if (isFinite(b.x)) { x += b.x + b.width / 2; y += b.y + b.height / 2; c++; } });
    const r = c ? { x: x / c, y: y / c } : null;
    centerCache.set(id, r); return r;
  }

  function flowClass(s, t) {
    const a = center(s), b = center(t);
    if (!a || !b) return "edge-flow-forward";
    const dx = b.x - a.x, dy = b.y - a.y;
    if (Math.abs(dx) >= Math.abs(dy)) return dx >= 0 ? "edge-flow-forward" : "edge-flow-reverse";
    return dy >= 0 ? "edge-flow-forward" : "edge-flow-reverse";
  }

  let selected = null;

  function reset() {
    selected = null;
    nodes.forEach((n) => n.classList.remove("is-dimmed", "is-active", "is-connected"));
    edges.forEach((e) => e.classList.remove("is-dimmed", "is-connected", "edge-neutral", "edge-flow-forward", "edge-flow-reverse"));
    nodeListEl.querySelectorAll(".kc-node.sel").forEach((el) => el.classList.remove("sel"));
  }

  function focus(id) {
    reset();
    selected = id;
    nodes.forEach((n) => n.classList.add("is-dimmed"));
    edges.forEach((e) => e.classList.add("is-dimmed"));
    (nodeMap.get(id) || []).forEach((n) => { n.classList.remove("is-dimmed"); n.classList.add("is-active"); });
    edges.forEach((e) => {
      const s = e.dataset.edgeSource, t = e.dataset.edgeTarget;
      if (s !== id && t !== id) return;
      e.classList.remove("is-dimmed"); e.classList.add("is-connected");
      const directed = e.dataset.edgeKind === "directed";
      if (!directed || s === t) e.classList.add("edge-neutral");
      else e.classList.add(flowClass(s, t));
      [s, t].forEach((rid) => (nodeMap.get(rid) || []).forEach((rn) => {
        rn.classList.remove("is-dimmed");
        rn.classList.add(rid === id ? "is-active" : "is-connected");
      }));
    });
    const item = nodeListEl.querySelector('.kc-node[data-id="' + (window.CSS && CSS.escape ? CSS.escape(id) : id) + '"]');
    if (item) item.classList.add("sel");
  }

  nodes.forEach((n) => n.addEventListener("click", (ev) => { ev.stopPropagation(); focus(n.dataset.nodeId); }));
  viewport.addEventListener("click", (ev) => { if (!ev.target.closest("[data-node-id]") && !justDragged) reset(); });

  // ── node list ──
  const seen = new Set();
  const order = [];
  nodes.forEach((n) => { const id = n.dataset.nodeId; if (!seen.has(id)) { seen.add(id); order.push(id); } });
  const edgeCount = new Map();
  edges.forEach((e) => {
    edgeCount.set(e.dataset.edgeSource, (edgeCount.get(e.dataset.edgeSource) || 0) + 1);
    edgeCount.set(e.dataset.edgeTarget, (edgeCount.get(e.dataset.edgeTarget) || 0) + 1);
  });

  if (order.length) {
    nodeCountEl.textContent = "· " + order.length;
    order.forEach((id) => {
      const row = document.createElement("div");
      row.className = "kc-node";
      row.dataset.id = id;
      row.innerHTML = '<span class="dot"></span><span class="name"></span><span class="ct mono">' + (edgeCount.get(id) || 0) + "</span>";
      row.querySelector(".name").textContent = id;
      row.addEventListener("click", () => focus(id));
      nodeListEl.appendChild(row);
    });
    nodeSearch.addEventListener("input", () => {
      const q = nodeSearch.value.trim().toLowerCase();
      nodeListEl.querySelectorAll(".kc-node").forEach((row) => {
        row.style.display = (!q || row.dataset.id.toLowerCase().includes(q)) ? "" : "none";
      });
    });
  } else {
    const panelSearch = document.querySelector(".kc-search");
    if (panelSearch) panelSearch.style.display = "none";
    nodeListEl.innerHTML = '<div class="kc-empty">Node highlighting ships via the Kroki annotator for this engine. Pan &amp; zoom still work here.</div>';
  }

  // ── pan / zoom wiring ──
  viewport.addEventListener("wheel", (e) => {
    e.preventDefault();
    if (e.ctrlKey || e.metaKey || e.altKey) { zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX, e.clientY); return; }
    zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX, e.clientY);
  }, { passive: false });

  let drag = false, sx = 0, sy = 0, ox = 0, oy = 0, justDragged = false;
  viewport.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    drag = true; justDragged = false; sx = e.clientX; sy = e.clientY; ox = tx; oy = ty;
    viewport.classList.add("dragging"); viewport.setPointerCapture(e.pointerId);
  });
  viewport.addEventListener("pointermove", (e) => {
    if (!drag) return;
    if (Math.abs(e.clientX - sx) + Math.abs(e.clientY - sy) > 3) justDragged = true;
    tx = ox + (e.clientX - sx); ty = oy + (e.clientY - sy); apply();
  });
  const endDrag = () => { if (!drag) return; drag = false; viewport.classList.remove("dragging"); setTimeout(() => { justDragged = false; }, 0); };
  viewport.addEventListener("pointerup", endDrag);
  viewport.addEventListener("pointercancel", endDrag);

  document.getElementById("zoom-in").addEventListener("click", () => { const r = viewport.getBoundingClientRect(); zoomAt(SCALE_STEP, r.left + r.width / 2, r.top + r.height / 2); });
  document.getElementById("zoom-out").addEventListener("click", () => { const r = viewport.getBoundingClientRect(); zoomAt(1 / SCALE_STEP, r.left + r.width / 2, r.top + r.height / 2); });
  document.getElementById("fit-view").addEventListener("click", fit);
  document.getElementById("actual-size").addEventListener("click", actual);

  window.addEventListener("keydown", (e) => {
    if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
    if (e.key === "+" || e.key === "=") { e.preventDefault(); const r = viewport.getBoundingClientRect(); zoomAt(SCALE_STEP, r.left + r.width / 2, r.top + r.height / 2); }
    else if (e.key === "-" || e.key === "_") { e.preventDefault(); const r = viewport.getBoundingClientRect(); zoomAt(1 / SCALE_STEP, r.left + r.width / 2, r.top + r.height / 2); }
    else if (e.key === "0") { e.preventDefault(); fit(); }
    else if (e.key === "1") { e.preventDefault(); actual(); }
    else if (e.key === "Escape") { reset(); }
  });

  window.addEventListener("resize", updateMini);
  fit();
})();
"""


def build_html_document(
    svg_markup: str,
    title: str,
    metadata: dict[str, str | int],
    kroki_url: str | None = None,
) -> str:
    engine = str(metadata["engine"])
    tool_rgb, tool_hex = ENGINE_COLORS.get(engine, ("99, 102, 241", "#6366f1"))
    safe_title = html.escape(title)

    copy_button = ""
    if kroki_url:
        copy_button = (
            '<button class="kc-btn" id="copy-url" type="button">'
            '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="2"/>'
            '<path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>Copy Kroki URL</button>'
        )

    pill = (
        f'<span class="kc-pill" style="background:rgba({tool_rgb},.13);'
        f'border:1px solid rgba({tool_rgb},.32);color:{tool_hex}">'
        f'<span class="d" style="background:{tool_hex}"></span>{html.escape(engine)}</span>'
    )

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
    <nav class="kc-nav">
      <a class="kc-back" href="../index.html"><svg viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6"/></svg>Gallery</a>
      <span class="kc-sep">/</span>
      <span class="kc-title">__TITLE__</span>
      __PILL__
      <div class="kc-nav-right">
        __COPY_BUTTON__
        <button class="kc-icon" id="theme-toggle" type="button" aria-label="Toggle theme"><svg viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg></button>
      </div>
    </nav>
    <div class="kc-body">
      <div class="kc-viewport" id="viewport" tabindex="0">
        <div class="kc-content" id="content">__SVG__</div>
        <div class="kc-hint">click a node &middot; connected paths lift, rest dim &middot; drag to pan &middot; scroll to zoom</div>
        <div class="kc-toolbar">
          <button class="sq" id="zoom-out" type="button" aria-label="Zoom out">&minus;</button>
          <button class="sq" id="zoom-in" type="button" aria-label="Zoom in">+</button>
          <button id="fit-view" type="button">Fit</button>
          <button id="actual-size" type="button">100%</button>
        </div>
        <div class="kc-status" id="status">Fit</div>
      </div>
      <aside class="kc-panel">
        <div class="kc-panel-head"><b>Nodes</b> <span id="node-count"></span></div>
        <div class="kc-search">
          <label><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input id="node-search" placeholder="Filter nodes" autocomplete="off"></label>
        </div>
        <div class="kc-node-list" id="node-list"></div>
        <div class="kc-mini-wrap">
          <div class="kc-mini" id="mini"><div class="kc-mini-rect" id="mini-rect"></div></div>
          <div class="kc-mini-label">Minimap &middot; viewport region</div>
        </div>
      </aside>
    </div>
    <div class="kc-toast" id="toast"><span class="d"></span>Kroki URL copied to clipboard</div>
  </div>
  <script>window.__KROKI_URL__ = __KROKI_URL_JSON__;</script>
  <script>__SCRIPT__</script>
</body>
</html>
"""

    replacements = {
        "__STYLE__": VIEWER_STYLE,
        "__SCRIPT__": VIEWER_SCRIPT,
        "__SVG__": svg_markup,
        "__PILL__": pill,
        "__COPY_BUTTON__": copy_button,
        "__KROKI_URL_JSON__": json.dumps(kroki_url or ""),
    }
    # Title appears twice; replace it after the structural tokens so a title
    # containing "__..." can never collide with a real token.
    out = shell
    for token, value in replacements.items():
        out = out.replace(token, value)
    out = out.replace("__TITLE__", safe_title)
    return out


def build_interactive_html_file(
    engine: str,
    svg_text: str,
    output_path: pathlib.Path,
    title: str,
    kroki_url: str | None = None,
) -> dict[str, str | int]:
    annotated_svg, metadata = annotate_svg(engine=engine, svg_text=svg_text)
    html_doc = build_html_document(
        svg_markup=annotated_svg, title=title, metadata=metadata, kroki_url=kroki_url
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrap a Kroki SVG in an interactive HTML viewer.")
    parser.add_argument("--engine", required=True, help="Kroki engine used to render the SVG.")
    parser.add_argument("--input", required=True, help="Path to the rendered SVG file.")
    parser.add_argument("--output", required=True, help="Path to write the interactive HTML.")
    parser.add_argument("--title", help="Viewer title. Defaults to the SVG stem.")
    parser.add_argument("--kroki-url", help="Shareable Kroki GET URL for the Copy button.")
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    output_path = pathlib.Path(args.output)
    title = args.title or input_path.stem.replace("-", " ").title()
    svg_text = input_path.read_text(encoding="utf-8")

    try:
        metadata = build_interactive_html_file(
            engine=args.engine,
            svg_text=svg_text,
            output_path=output_path,
            title=title,
            kroki_url=args.kroki_url,
        )
    except ET.ParseError as exc:
        print(f"Interactive build failed: {exc}", file=sys.stderr)
        return 1

    print(f"Interactive HTML: {output_path}")
    print(
        "Interactive summary:"
        f" engine={metadata['engine']}"
        f" tier={metadata['tier']}"
        f" nodes={metadata['nodes']}"
        f" edges={metadata['edges']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
