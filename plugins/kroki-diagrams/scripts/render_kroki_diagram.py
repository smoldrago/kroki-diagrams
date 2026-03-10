#!/usr/bin/env python3
import argparse
import base64
import json
import pathlib
import subprocess
import sys
import zlib

from build_diagram_index import META_FILENAME, build_diagram_index
from build_interactive_kroki_html import build_interactive_html_file

SUPPORTED_ENGINES = [
    "plantuml",
    "c4plantuml",
    "mermaid",
    "graphviz",
    "bpmn",
    "erd",
]


def build_kroki_url(engine: str, fmt: str, source: str) -> str:
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(source.encode("utf-8")) + compressor.flush()
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return f"https://kroki.io/{engine}/{fmt}/{encoded}"


def render(engine: str, fmt: str, source: str) -> bytes:
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "-X",
            "POST",
            f"https://kroki.io/{engine}/{fmt}",
            "-H",
            "Content-Type: text/plain; charset=utf-8",
            "--data-binary",
            "@-",
        ],
        input=source.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"curl failed with code {result.returncode}")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render PlantUML or C4-PlantUML diagrams through Kroki."
    )
    parser.add_argument(
        "--engine",
        required=True,
        choices=SUPPORTED_ENGINES,
        help="Kroki engine to use.",
    )
    parser.add_argument("--input", required=True, help="Path to .puml source file.")
    parser.add_argument(
        "--format",
        default="svg",
        choices=["svg", "png", "pdf", "txt"],
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        help="Path to write the rendered output. Defaults next to input with matching extension.",
    )
    parser.add_argument(
        "--interactive-output",
        help="Optional HTML output path for an interactive SVG wrapper.",
    )
    parser.add_argument(
        "--interactive-title",
        help="Title used by the interactive HTML wrapper.",
    )
    parser.add_argument(
        "--summary",
        help="Optional short summary stored for generated index pages.",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Do not create or update the parent index.html.",
    )
    parser.add_argument(
        "--print-url-only",
        action="store_true",
        help="Only print the shareable Kroki GET URL and do not render via POST.",
    )
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    source = input_path.read_text(encoding="utf-8")
    url = build_kroki_url(args.engine, args.format, source)

    if args.print_url_only:
        print(url)
        return 0

    output_path = pathlib.Path(args.output) if args.output else input_path.with_suffix(f".{args.format}")

    try:
        rendered = render(args.engine, args.format, source)
    except RuntimeError as exc:
        print(f"Render failed: {exc}", file=sys.stderr)
        print(f"Kroki URL: {url}", file=sys.stderr)
        return 1

    text_probe = rendered[:2048].decode("utf-8", errors="ignore")
    if "<svg" not in text_probe and args.format == "svg":
        print("Render failed: Kroki did not return SVG output", file=sys.stderr)
        print(text_probe.strip(), file=sys.stderr)
        print(f"Kroki URL: {url}", file=sys.stderr)
        return 1

    output_path.write_bytes(rendered)
    print(f"Rendered: {output_path}")

    interactive_summary = None
    if args.interactive_output:
        if args.format != "svg":
            print("Interactive build failed: --interactive-output requires --format svg", file=sys.stderr)
            return 1
        interactive_path = pathlib.Path(args.interactive_output)
        title = args.interactive_title or input_path.stem.replace("-", " ").title()
        interactive_summary = build_interactive_html_file(
            engine=args.engine,
            svg_text=rendered.decode("utf-8"),
            output_path=interactive_path,
            title=title,
        )
        print(f"Interactive HTML: {interactive_path}")
        print(
            "Interactive summary:"
            f" tier={interactive_summary['tier']}"
            f" nodes={interactive_summary['nodes']}"
            f" edges={interactive_summary['edges']}"
        )

    artifact_dir = output_path.parent
    title = args.interactive_title or input_path.stem.replace("-", " ").title()
    meta = {
        "title": title,
        "engine": args.engine,
        "format": args.format,
        "summary": args.summary or f"Rendered with {args.engine}.",
    }
    if interactive_summary:
        meta["interactive_tier"] = interactive_summary["tier"]
    (artifact_dir / META_FILENAME).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if not args.skip_index and output_path.name == "rendered.svg":
        index_path = build_diagram_index(root=artifact_dir.parent)
        print(f"Index HTML: {index_path}")

    print(f"Kroki URL: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
