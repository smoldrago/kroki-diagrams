#!/usr/bin/env python3
import argparse
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


def build_html_document(svg_markup: str, title: str, metadata: dict[str, str | int]) -> str:
    engine = metadata["engine"]
    tier = metadata["tier"]
    nodes = metadata["nodes"]
    edges = metadata["edges"]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

    :root {{
      --bg: #e7edf4;
      --bg-deep: #d9e2ec;
      --panel: rgba(247, 250, 252, 0.9);
      --panel-strong: rgba(244, 248, 251, 0.94);
      --text: #142033;
      --muted: #607087;
      --label-highlight: #6d28d9;
      --dim-opacity: 0.42;
      --node-shadow: drop-shadow(0 0 9px rgba(120, 119, 255, 0.35));
      --panel-border: rgba(69, 89, 115, 0.18);
      --focus-ring: rgba(38, 132, 255, 0.28);
      --toolbar-shadow: rgba(31, 45, 61, 0.12);
      --canvas-grid: rgba(108, 130, 158, 0.08);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-height: 100vh;
      font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(57, 135, 255, 0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(18, 35, 58, 0.08), transparent 30%),
        linear-gradient(180deg, var(--bg) 0%, var(--bg-deep) 100%);
    }}

    .shell {{
      width: 100%;
      padding: 14px;
    }}

    .stage {{
      position: relative;
      overflow: hidden;
      padding: 10px;
      min-height: calc(100vh - 28px);
      border-radius: 20px;
      border: 1px solid var(--panel-border);
      background: linear-gradient(180deg, rgba(248, 251, 253, 0.82), rgba(238, 244, 249, 0.8));
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.72),
        0 18px 40px rgba(30, 41, 59, 0.08);
    }}

    .stage:focus-visible {{
      outline: 2px solid var(--focus-ring);
      outline-offset: 2px;
    }}

    .canvas-toolbar {{
      position: absolute;
      top: 18px;
      right: 18px;
      z-index: 5;
      display: flex;
      gap: 8px;
      align-items: center;
      padding: 8px;
      border-radius: 14px;
      background: rgba(246, 249, 252, 0.9);
      border: 1px solid var(--panel-border);
      box-shadow: 0 10px 26px var(--toolbar-shadow);
      backdrop-filter: blur(8px);
    }}

    .canvas-toolbar button {{
      border: 1px solid rgba(78, 97, 122, 0.16);
      background: linear-gradient(180deg, #fdfefe, #eef3f8);
      color: var(--text);
      border-radius: 10px;
      min-width: 40px;
      height: 36px;
      padding: 0 10px;
      font-family: "IBM Plex Mono", "SFMono-Regular", "Menlo", monospace;
      font-size: 0.9rem;
      font-weight: 600;
      letter-spacing: 0.01em;
      cursor: pointer;
      transition: transform 120ms ease, background 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
    }}

    .canvas-toolbar button:hover {{
      background: linear-gradient(180deg, #ffffff, #f2f6fb);
      border-color: rgba(38, 132, 255, 0.3);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
      transform: translateY(-1px);
    }}

    .canvas-toolbar button:active {{
      transform: translateY(0);
    }}

    .canvas-toolbar button:focus-visible {{
      outline: 2px solid var(--focus-ring);
      outline-offset: 2px;
    }}

    .canvas-viewport {{
      position: relative;
      height: calc(100vh - 48px);
      min-height: 0;
      overflow: hidden;
      border-radius: 16px;
      background:
        radial-gradient(circle at top left, rgba(255, 255, 255, 0.74), transparent 24%),
        repeating-linear-gradient(0deg, var(--canvas-grid) 0 1px, transparent 1px 28px),
        repeating-linear-gradient(90deg, var(--canvas-grid) 0 1px, transparent 1px 28px),
        linear-gradient(180deg, rgba(248, 251, 254, 0.94), rgba(233, 239, 246, 0.92));
      cursor: default;
      touch-action: none;
      user-select: none;
    }}

    .canvas-viewport.is-pan-mode {{
      cursor: grab;
    }}

    .canvas-viewport.is-dragging {{
      cursor: grabbing;
    }}

    .canvas-content {{
      position: absolute;
      top: 0;
      left: 0;
      transform-origin: 0 0;
      will-change: transform;
      overflow: visible;
    }}

    .canvas-content svg {{
      display: block;
      width: max-content;
      max-width: none;
      height: auto;
      overflow: visible;
      background: transparent !important;
    }}

    .canvas-status {{
      position: absolute;
      left: 18px;
      bottom: 18px;
      z-index: 4;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(245, 248, 251, 0.88);
      border: 1px solid var(--panel-border);
      color: var(--muted);
      font-family: "IBM Plex Mono", "SFMono-Regular", "Menlo", monospace;
      font-size: 0.82rem;
      font-weight: 500;
      letter-spacing: 0.02em;
      box-shadow: 0 10px 24px rgba(31, 45, 61, 0.08);
      backdrop-filter: blur(8px);
      pointer-events: none;
    }}

    .interactive-node {{
      cursor: pointer;
      transition: opacity 160ms ease, filter 160ms ease, transform 160ms ease;
      transform-origin: center center;
    }}

    .interactive-edge {{
      transition: opacity 160ms ease, filter 160ms ease;
    }}

    .interactive-node.is-dimmed,
    .interactive-edge.is-dimmed {{
      opacity: var(--dim-opacity);
    }}

    .interactive-node.is-active,
    .interactive-node.is-connected,
    .interactive-edge.is-connected {{
      opacity: 1;
    }}

    .interactive-node.is-active {{
      filter: var(--node-shadow);
    }}

    .interactive-node.is-active rect,
    .interactive-node.is-active ellipse,
    .interactive-node.is-active circle,
    .interactive-node.is-active polygon,
    .interactive-node.is-active path {{
      stroke-width: 2.2px !important;
      animation: rainbow-stroke 3.4s linear infinite;
    }}

    .interactive-node.is-connected rect,
    .interactive-node.is-connected ellipse,
    .interactive-node.is-connected circle,
    .interactive-node.is-connected polygon,
    .interactive-node.is-connected path {{
      stroke-width: 1.7px !important;
      animation: rainbow-stroke 3.4s linear infinite;
    }}

    .interactive-edge.is-connected path,
    .interactive-edge.is-connected line,
    .interactive-edge.is-connected polyline {{
      stroke-width: 2.2px !important;
      stroke-linecap: round;
      filter: drop-shadow(0 0 4px rgba(93, 92, 255, 0.25));
    }}

    .interactive-edge.is-connected polygon {{
      animation: rainbow-fill 3.4s linear infinite;
    }}

    .interactive-edge.is-connected text,
    .interactive-edge.is-connected tspan {{
      fill: var(--label-highlight) !important;
      stroke: none !important;
      font-weight: 700 !important;
      animation: none !important;
      filter: none !important;
    }}

    .interactive-edge.is-connected foreignObject,
    .interactive-edge.is-connected foreignObject * {{
      color: var(--label-highlight) !important;
      font-weight: 700 !important;
      animation: none !important;
      filter: none !important;
      text-shadow: none !important;
    }}

    .interactive-edge.edge-flow-forward path,
    .interactive-edge.edge-flow-forward line,
    .interactive-edge.edge-flow-forward polyline {{
      stroke-dasharray: 11 7;
      animation: rainbow-stroke 3.4s linear infinite, flow-forward 850ms linear infinite;
    }}

    .interactive-edge.edge-flow-reverse path,
    .interactive-edge.edge-flow-reverse line,
    .interactive-edge.edge-flow-reverse polyline {{
      stroke-dasharray: 11 7;
      animation: rainbow-stroke 3.4s linear infinite, flow-reverse 850ms linear infinite;
    }}

    .interactive-edge.edge-neutral path,
    .interactive-edge.edge-neutral line,
    .interactive-edge.edge-neutral polyline {{
      stroke-dasharray: 9 7;
      animation: rainbow-stroke 3.4s linear infinite, flow-neutral 1150ms ease-in-out infinite;
    }}

    @keyframes rainbow-stroke {{
      0% {{ stroke: #ff3b30; }}
      20% {{ stroke: #ff9500; }}
      40% {{ stroke: #34c759; }}
      60% {{ stroke: #0a84ff; }}
      80% {{ stroke: #5e5ce6; }}
      100% {{ stroke: #ff2d55; }}
    }}

    @keyframes rainbow-fill {{
      0% {{ fill: #ff3b30; stroke: #ff3b30; }}
      20% {{ fill: #ff9500; stroke: #ff9500; }}
      40% {{ fill: #34c759; stroke: #34c759; }}
      60% {{ fill: #0a84ff; stroke: #0a84ff; }}
      80% {{ fill: #5e5ce6; stroke: #5e5ce6; }}
      100% {{ fill: #ff2d55; stroke: #ff2d55; }}
    }}

    @keyframes flow-forward {{
      to {{ stroke-dashoffset: -18; }}
    }}

    @keyframes flow-reverse {{
      to {{ stroke-dashoffset: 18; }}
    }}

    @keyframes flow-neutral {{
      0% {{ stroke-dashoffset: 0; filter: brightness(1); }}
      50% {{ stroke-dashoffset: 10; filter: brightness(1.2); }}
      100% {{ stroke-dashoffset: 20; filter: brightness(1); }}
    }}

    @media (max-width: 720px) {{
      .shell {{
        padding: 8px;
      }}

      .canvas-toolbar {{
        top: 12px;
        right: 12px;
        gap: 6px;
        padding: 6px;
      }}

      .canvas-toolbar button {{
        min-width: 36px;
        height: 34px;
        padding: 0 8px;
      }}

      .canvas-viewport {{
        height: calc(100vh - 28px);
      }}

      .canvas-status {{
        left: 12px;
        bottom: 12px;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="stage" id="diagram-stage" tabindex="0" aria-label="Interactive diagram canvas">
      <div class="canvas-toolbar" aria-label="Canvas controls">
        <button type="button" id="zoom-out" aria-label="Zoom out">-</button>
        <button type="button" id="zoom-in" aria-label="Zoom in">+</button>
        <button type="button" id="fit-view" aria-label="Fit to screen">Fit</button>
        <button type="button" id="actual-size" aria-label="Reset to one hundred percent">100%</button>
      </div>
      <div class="canvas-viewport" id="diagram-viewport">
        <div class="canvas-content" id="diagram-content">
          {svg_markup}
        </div>
      </div>
      <div class="canvas-status" id="diagram-status">Fit 100%</div>
    </section>
  </main>
  <script>
    const stage = document.getElementById("diagram-stage");
    const viewport = document.getElementById("diagram-viewport");
    const content = document.getElementById("diagram-content");
    const status = document.getElementById("diagram-status");
    const zoomInButton = document.getElementById("zoom-in");
    const zoomOutButton = document.getElementById("zoom-out");
    const fitButton = document.getElementById("fit-view");
    const actualSizeButton = document.getElementById("actual-size");
    const svg = content.querySelector("svg");

    if (svg) {{
      const nodes = Array.from(svg.querySelectorAll("[data-node-id]"));
      const edges = Array.from(svg.querySelectorAll("[data-edge-source][data-edge-target]"));
      const PADDING = 28;
      const PAN_STEP = 60;
      const SCALE_STEP = 1.16;
      const MIN_SCALE = 0.08;
      const MAX_SCALE = 3.5;
      const rawBounds = svg.getBBox();
      const normalizedBounds = (Number.isFinite(rawBounds.width) && rawBounds.width > 0 && Number.isFinite(rawBounds.height) && rawBounds.height > 0)
        ? rawBounds
        : null;

      let scale = 1;
      let translateX = 0;
      let translateY = 0;
      let fitScale = 1;
      let isSpacePressed = false;
      let isDragging = false;
      let activePointerId = null;
      let dragStartX = 0;
      let dragStartY = 0;
      let dragOriginX = 0;
      let dragOriginY = 0;
      let shouldAutoFitOnResize = true;
      let selectedNodeId = null;

      if (normalizedBounds) {{
        svg.style.transform = `translate(${{-normalizedBounds.x}}px, ${{-normalizedBounds.y}}px)`;
        svg.style.transformOrigin = "top left";
        content.style.width = `${{normalizedBounds.width}}px`;
        content.style.height = `${{normalizedBounds.height}}px`;
      }}

      const getCanvasSize = () => {{
        if (normalizedBounds) {{
          return {{ width: normalizedBounds.width, height: normalizedBounds.height }};
        }}

        const viewBox = svg.viewBox && svg.viewBox.baseVal;
        if (viewBox && viewBox.width && viewBox.height) {{
          return {{ width: viewBox.width, height: viewBox.height }};
        }}

        const box = svg.getBBox();
        return {{ width: box.width || 1, height: box.height || 1 }};
      }};

      const clampScale = (nextScale) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, nextScale));

      const applyTransform = () => {{
        content.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{scale}})`;
        const zoomPercent = Math.round(scale * 100);
        status.textContent = `Zoom ${{zoomPercent}}%`;
      }};

      const centerForScale = (nextScale) => {{
        const canvas = getCanvasSize();
        const viewportRect = viewport.getBoundingClientRect();
        return {{
          x: (viewportRect.width - canvas.width * nextScale) / 2,
          y: (viewportRect.height - canvas.height * nextScale) / 2,
        }};
      }};

      const fitToViewport = () => {{
        const canvas = getCanvasSize();
        const viewportRect = viewport.getBoundingClientRect();
        const usableWidth = Math.max(120, viewportRect.width - PADDING * 2);
        const usableHeight = Math.max(120, viewportRect.height - PADDING * 2);
        fitScale = clampScale(Math.min(usableWidth / canvas.width, usableHeight / canvas.height));
        scale = fitScale;
        const centered = centerForScale(scale);
        translateX = centered.x;
        translateY = centered.y;
        shouldAutoFitOnResize = true;
        applyTransform();
        status.textContent = `Fit ${{Math.round(scale * 100)}}%`;
      }};

      const resetToActualSize = () => {{
        scale = 1;
        const centered = centerForScale(scale);
        translateX = centered.x;
        translateY = centered.y;
        shouldAutoFitOnResize = false;
        applyTransform();
      }};

      const zoomAtPoint = (factor, clientX, clientY) => {{
        const viewportRect = viewport.getBoundingClientRect();
        const pointerX = clientX - viewportRect.left;
        const pointerY = clientY - viewportRect.top;
        const nextScale = clampScale(scale * factor);
        const scaleRatio = nextScale / scale;

        translateX = pointerX - (pointerX - translateX) * scaleRatio;
        translateY = pointerY - (pointerY - translateY) * scaleRatio;
        scale = nextScale;
        shouldAutoFitOnResize = false;
        applyTransform();
      }};

      const panBy = (dx, dy) => {{
        translateX += dx;
        translateY += dy;
        shouldAutoFitOnResize = false;
        applyTransform();
      }};

      fitToViewport();

      const nodeMap = new Map();
      const nodeCenterCache = new Map();
      for (const node of nodes) {{
        const nodeId = node.dataset.nodeId;
        if (!nodeMap.has(nodeId)) nodeMap.set(nodeId, []);
        nodeMap.get(nodeId).push(node);
      }}

      const getNodeCenter = (nodeId) => {{
        if (nodeCenterCache.has(nodeId)) return nodeCenterCache.get(nodeId);

        const relatedNodes = nodeMap.get(nodeId) || [];
        if (!relatedNodes.length) return null;

        let totalX = 0;
        let totalY = 0;
        let count = 0;

        for (const related of relatedNodes) {{
          const box = related.getBBox();
          if (!Number.isFinite(box.x) || !Number.isFinite(box.y)) continue;
          totalX += box.x + box.width / 2;
          totalY += box.y + box.height / 2;
          count += 1;
        }}

        const center = count ? {{ x: totalX / count, y: totalY / count }} : null;
        nodeCenterCache.set(nodeId, center);
        return center;
      }};

      const getFlowDirectionClass = (sourceId, targetId) => {{
        const sourceCenter = getNodeCenter(sourceId);
        const targetCenter = getNodeCenter(targetId);
        if (!sourceCenter || !targetCenter) return "edge-flow-forward";

        const dx = targetCenter.x - sourceCenter.x;
        const dy = targetCenter.y - sourceCenter.y;

        if (Math.abs(dx) >= Math.abs(dy)) {{
          return dx >= 0 ? "edge-flow-forward" : "edge-flow-reverse";
        }}

        return dy >= 0 ? "edge-flow-forward" : "edge-flow-reverse";
      }};

      const resetState = () => {{
        selectedNodeId = null;
        for (const node of nodes) {{
          node.classList.remove("is-dimmed", "is-active", "is-connected");
        }}
        for (const edge of edges) {{
          edge.classList.remove(
            "is-dimmed",
            "is-connected",
            "edge-incoming",
            "edge-outgoing",
            "edge-neutral",
            "edge-flow-forward",
            "edge-flow-reverse"
          );
        }}
      }};

      const focusNode = (nodeId) => {{
        selectedNodeId = nodeId;
        resetState();
        selectedNodeId = nodeId;

        for (const node of nodes) {{
          node.classList.add("is-dimmed");
        }}
        for (const edge of edges) {{
          edge.classList.add("is-dimmed");
        }}

        for (const active of nodeMap.get(nodeId) || []) {{
          active.classList.remove("is-dimmed");
          active.classList.add("is-active");
        }}

        for (const edge of edges) {{
          const source = edge.dataset.edgeSource;
          const target = edge.dataset.edgeTarget;
          if (source !== nodeId && target !== nodeId) continue;

          edge.classList.remove("is-dimmed");
          edge.classList.add("is-connected");

          const directed = edge.dataset.edgeKind === "directed";
          if (!directed || source === target) {{
            edge.classList.add("edge-neutral");
          }} else if (source === nodeId) {{
            edge.classList.add("edge-outgoing");
            edge.classList.add(getFlowDirectionClass(source, target));
          }} else {{
            edge.classList.add("edge-incoming");
            edge.classList.add(getFlowDirectionClass(source, target));
          }}

          for (const relatedId of [source, target]) {{
            for (const related of nodeMap.get(relatedId) || []) {{
              related.classList.remove("is-dimmed");
              related.classList.add(relatedId === nodeId ? "is-active" : "is-connected");
            }}
          }}
        }}
      }};

      for (const node of nodes) {{
        node.addEventListener("click", (event) => {{
          event.stopPropagation();
          focusNode(node.dataset.nodeId);
        }});
      }}

      svg.addEventListener("click", (event) => {{
        const clickedNode = event.target.closest("[data-node-id]");
        if (clickedNode) return;
        resetState();
      }});

      viewport.addEventListener("click", (event) => {{
        if (!event.target.closest("[data-node-id]")) {{
          resetState();
        }}
      }});

      zoomInButton.addEventListener("click", () => {{
        const rect = viewport.getBoundingClientRect();
        zoomAtPoint(SCALE_STEP, rect.left + rect.width / 2, rect.top + rect.height / 2);
      }});

      zoomOutButton.addEventListener("click", () => {{
        const rect = viewport.getBoundingClientRect();
        zoomAtPoint(1 / SCALE_STEP, rect.left + rect.width / 2, rect.top + rect.height / 2);
      }});

      fitButton.addEventListener("click", fitToViewport);
      actualSizeButton.addEventListener("click", resetToActualSize);

      viewport.addEventListener("wheel", (event) => {{
        if (event.ctrlKey || event.metaKey || event.altKey) {{
          event.preventDefault();
          const factor = Math.exp(-event.deltaY * 0.0015);
          zoomAtPoint(factor, event.clientX, event.clientY);
          return;
        }}

        event.preventDefault();
        const panX = event.shiftKey ? -event.deltaY : -event.deltaX;
        const panY = event.shiftKey ? 0 : -event.deltaY;
        panBy(panX, panY);
      }}, {{ passive: false }});

      viewport.addEventListener("pointerdown", (event) => {{
        const wantsPan = event.button === 1 || (event.button === 0 && isSpacePressed);
        if (!wantsPan) return;

        event.preventDefault();
        isDragging = true;
        activePointerId = event.pointerId;
        dragStartX = event.clientX;
        dragStartY = event.clientY;
        dragOriginX = translateX;
        dragOriginY = translateY;
        viewport.classList.add("is-dragging");
        viewport.setPointerCapture(event.pointerId);
      }});

      viewport.addEventListener("pointermove", (event) => {{
        if (!isDragging || event.pointerId !== activePointerId) return;
        translateX = dragOriginX + (event.clientX - dragStartX);
        translateY = dragOriginY + (event.clientY - dragStartY);
        shouldAutoFitOnResize = false;
        applyTransform();
      }});

      const endDrag = (event) => {{
        if (!isDragging) return;
        if (event && activePointerId !== null && event.pointerId !== activePointerId) return;
        isDragging = false;
        activePointerId = null;
        viewport.classList.remove("is-dragging");
      }};

      viewport.addEventListener("pointerup", endDrag);
      viewport.addEventListener("pointercancel", endDrag);
      viewport.addEventListener("pointerleave", endDrag);

      const updatePanModeClass = () => {{
        viewport.classList.toggle("is-pan-mode", isSpacePressed && !isDragging);
      }};

      window.addEventListener("keydown", (event) => {{
        if (event.target && /input|textarea|select/i.test(event.target.tagName)) return;

        if (event.code === "Space") {{
          event.preventDefault();
        }}

        if (event.code === "Space" && !event.repeat) {{
          isSpacePressed = true;
          updatePanModeClass();
        }}

        if (event.key === "+" || event.key === "=") {{
          event.preventDefault();
          const rect = viewport.getBoundingClientRect();
          zoomAtPoint(SCALE_STEP, rect.left + rect.width / 2, rect.top + rect.height / 2);
        }} else if (event.key === "-" || event.key === "_") {{
          event.preventDefault();
          const rect = viewport.getBoundingClientRect();
          zoomAtPoint(1 / SCALE_STEP, rect.left + rect.width / 2, rect.top + rect.height / 2);
        }} else if (event.key === "0") {{
          event.preventDefault();
          fitToViewport();
        }} else if (event.key === "1") {{
          event.preventDefault();
          resetToActualSize();
        }} else if (event.key === "ArrowLeft") {{
          event.preventDefault();
          panBy(PAN_STEP, 0);
        }} else if (event.key === "ArrowRight") {{
          event.preventDefault();
          panBy(-PAN_STEP, 0);
        }} else if (event.key === "ArrowUp") {{
          event.preventDefault();
          panBy(0, PAN_STEP);
        }} else if (event.key === "ArrowDown") {{
          event.preventDefault();
          panBy(0, -PAN_STEP);
        }}
      }});

      window.addEventListener("keyup", (event) => {{
        if (event.code === "Space") {{
          event.preventDefault();
          isSpacePressed = false;
          updatePanModeClass();
        }}
      }});

      window.addEventListener("resize", () => {{
        if (shouldAutoFitOnResize) fitToViewport();
      }});
    }}
  </script>
</body>
</html>
"""


def build_interactive_html_file(engine: str, svg_text: str, output_path: pathlib.Path, title: str) -> dict[str, str | int]:
    annotated_svg, metadata = annotate_svg(engine=engine, svg_text=svg_text)
    html = build_html_document(svg_markup=annotated_svg, title=title, metadata=metadata)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrap a Kroki SVG in an interactive HTML viewer.")
    parser.add_argument("--engine", required=True, help="Kroki engine used to render the SVG.")
    parser.add_argument("--input", required=True, help="Path to the rendered SVG file.")
    parser.add_argument("--output", required=True, help="Path to write the interactive HTML.")
    parser.add_argument("--title", help="Viewer title. Defaults to the SVG stem.")
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
