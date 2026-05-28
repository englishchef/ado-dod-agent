"""Render the DoD LangGraph workflow as ASCII from the compiled graph."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

try:
    from backend.app.graphs.workflow import build_dod_workflow
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.graphs.workflow import build_dod_workflow

START_NODE = "__start__"
END_NODE = "__end__"
DEFAULT_OUTPUT = Path("backend/app/graphs/workflow_ascii.txt")


@dataclass(frozen=True)
class GraphEdge:
    """Small graph edge DTO detached from LangGraph internals."""

    source: str
    target: str
    label: str | None = None
    conditional: bool = False


def build_ascii_from_workflow() -> str:
    """Build ASCII art from the actual compiled DoD workflow graph."""

    graph = build_dod_workflow().get_graph()
    edges = [
        GraphEdge(
            source=str(edge.source),
            target=str(edge.target),
            label=str(edge.data) if edge.data is not None else None,
            conditional=bool(edge.conditional),
        )
        for edge in graph.edges
    ]
    return render_ascii(edges)


def render_ascii(edges: Iterable[GraphEdge]) -> str:
    """Render a readable workflow diagram from graph edges."""

    edge_list = list(edges)
    conditional_by_source = _conditional_edges_by_source(edge_list)
    normal_by_source = _normal_edges_by_source(edge_list)
    main_path = _main_path(edge_list, conditional_by_source, normal_by_source)

    lines = [
        "DoD LangGraph Workflow - Generated From Compiled Graph",
        "=====================================================",
        "",
        "Detailed view",
        "-------------",
        "",
    ]
    lines.extend(_render_detailed(main_path, conditional_by_source, normal_by_source))
    lines.extend(
        [
            "",
            "Compact view",
            "------------",
            "",
        ]
    )
    lines.extend(_render_compact(main_path, conditional_by_source, normal_by_source))
    lines.extend(
        [
            "",
            "Graph-derived edges",
            "-------------------",
            "",
        ]
    )
    lines.extend(_render_edge_table(edge_list))
    lines.extend(
        [
            "",
            "Scope notes",
            "-----------",
            "",
            "- This file is generated from `build_dod_workflow().get_graph()`.",
            "- Conditional route labels come from compiled LangGraph edge metadata.",
            "- No ServiceNow writeback is represented in this graph.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_ascii(output_path: Path) -> Path:
    """Write the generated ASCII workflow to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_ascii_from_workflow(), encoding="utf-8")
    return output_path


def _render_detailed(
    main_path: list[str],
    conditional_by_source: dict[str, list[GraphEdge]],
    normal_by_source: dict[str, list[GraphEdge]],
) -> list[str]:
    lines: list[str] = []
    for index, node in enumerate(main_path):
        lines.append(_display_node(node))
        if node == END_NODE:
            break

        conditional_edges = conditional_by_source.get(node, [])
        failed_edge = _edge_with_label(conditional_edges, "failed")
        continue_edge = _edge_with_label(conditional_edges, "continue")
        if failed_edge:
            route_name = _route_name(node)
            lines.extend(
                [
                    "  |",
                    "  v",
                    route_name,
                    "  |---------------- failed ----------------|",
                ]
            )
            lines.extend(_render_branch_chain(failed_edge.target, normal_by_source))
            if continue_edge:
                lines.extend(["  |", "  | continue", "  v"])
            continue

        if index < len(main_path) - 1:
            lines.extend(["  |", "  v"])
    return lines


def _render_branch_chain(
    target: str,
    normal_by_source: dict[str, list[GraphEdge]],
) -> list[str]:
    chain = _linear_chain(target, normal_by_source)
    lines: list[str] = []
    for index, node in enumerate(chain):
        prefix = "  |                                  "
        if node == END_NODE:
            lines.append("  |                                       END")
        else:
            lines.append(f"{prefix}{_display_node(node)}")
        if index < len(chain) - 1:
            lines.append("  |                                        |")
            lines.append("  |                                        v")
    return lines


def _render_compact(
    main_path: list[str],
    conditional_by_source: dict[str, list[GraphEdge]],
    normal_by_source: dict[str, list[GraphEdge]],
) -> list[str]:
    lines = [_display_node(main_path[0])]
    for node in main_path[1:]:
        previous = main_path[main_path.index(node) - 1]
        failed_edge = _edge_with_label(conditional_by_source.get(previous, []), "failed")
        if failed_edge:
            branch = " -> ".join(
                _display_node(item)
                for item in _linear_chain(failed_edge.target, normal_by_source)
            )
            lines.append(f"  -> [failed?] {branch}")
        lines.append(f"  -> {_display_node(node)}")
    return lines


def _render_edge_table(edges: list[GraphEdge]) -> list[str]:
    output: list[str] = []
    for edge in sorted(edges, key=lambda item: (item.source, item.label or "", item.target)):
        label = f" [{edge.label}]" if edge.label else ""
        edge_type = "conditional" if edge.conditional else "direct"
        output.append(
            f"- {_display_node(edge.source)} -> {_display_node(edge.target)}{label} ({edge_type})"
        )
    return output


def _main_path(
    edges: list[GraphEdge],
    conditional_by_source: dict[str, list[GraphEdge]],
    normal_by_source: dict[str, list[GraphEdge]],
) -> list[str]:
    del edges
    path = [START_NODE]
    current = START_NODE
    seen = {START_NODE}
    while current != END_NODE:
        next_node = _continue_target(current, conditional_by_source, normal_by_source)
        if next_node is None or next_node in seen:
            break
        path.append(next_node)
        seen.add(next_node)
        current = next_node
    return path


def _continue_target(
    source: str,
    conditional_by_source: dict[str, list[GraphEdge]],
    normal_by_source: dict[str, list[GraphEdge]],
) -> str | None:
    continue_edge = _edge_with_label(conditional_by_source.get(source, []), "continue")
    if continue_edge:
        return continue_edge.target
    normal_edges = normal_by_source.get(source, [])
    if len(normal_edges) == 1:
        return normal_edges[0].target
    return None


def _linear_chain(source: str, normal_by_source: dict[str, list[GraphEdge]]) -> list[str]:
    chain = [source]
    current = source
    seen = {source}
    while current != END_NODE:
        normal_edges = normal_by_source.get(current, [])
        if len(normal_edges) != 1:
            break
        target = normal_edges[0].target
        if target in seen:
            break
        chain.append(target)
        seen.add(target)
        current = target
    return chain


def _conditional_edges_by_source(edges: list[GraphEdge]) -> dict[str, list[GraphEdge]]:
    grouped: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in edges:
        if edge.conditional:
            grouped[edge.source].append(edge)
    return grouped


def _normal_edges_by_source(edges: list[GraphEdge]) -> dict[str, list[GraphEdge]]:
    grouped: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in edges:
        if not edge.conditional:
            grouped[edge.source].append(edge)
    return grouped


def _edge_with_label(edges: list[GraphEdge], label: str) -> GraphEdge | None:
    for edge in edges:
        if edge.label == label:
            return edge
    return None


def _route_name(source: str) -> str:
    if source == "collect_raw_metadata":
        return "route_after_collect_raw"
    if source == "build_evidence_buckets":
        return "route_after_evidence"
    if source == "generate_llm_outputs":
        return "route_after_llm"
    if source == "normalize_canonical":
        return "route_after_normalize"
    if source == "validate_input":
        return "route_after_validate_input"
    return f"route_after_{source}"


def _display_node(node: str) -> str:
    if node == START_NODE:
        return "START"
    if node == END_NODE:
        return "END"
    return node


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render backend.app.graphs.workflow as ASCII from the compiled graph."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output path for generated ASCII workflow.",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print generated ASCII to stdout after writing it.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    output_path = write_ascii(args.output)
    if args.print:
        print(output_path.read_text(encoding="utf-8"))
    else:
        print(f"Wrote workflow ASCII to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
