from collections import defaultdict
import numpy as np
from typing import TypeAlias

from llm_mud.gen.data_model import Edge

# Types
Vector3D: TypeAlias = np.ndarray  # shape (3,) dtype=float
PathInfo: TypeAlias = tuple[list[Edge], Vector3D]
EdgeKey: TypeAlias = tuple[str, str]  # (source_id, destination_id

DIRECTION_VECTORS: dict[str, np.ndarray] = {
    "north": np.array([1.0, 0.0, 0.0]),
    "south": np.array([-1.0, 0.0, 0.0]),
    "east": np.array([0.0, 1.0, 0.0]),
    "west": np.array([0.0, -1.0, 0.0]),
    "northeast": np.array([1.0, 1.0, 0.0]),
    "northwest": np.array([1.0, -1.0, 0.0]),
    "southeast": np.array([-1.0, 1.0, 0.0]),
    "southwest": np.array([-1.0, -1.0, 0.0]),
    "up": np.array([0.0, 0.0, 1.0]),
    "down": np.array([0.0, 0.0, -1.0]),
}


def get_edge_vector(edge: Edge) -> Vector3D:
    """Convert an edge's direction into a 3D vector."""
    return DIRECTION_VECTORS.get(edge.direction.lower(), np.array([0.0, 0.0, 100.0]))


def build_adjacency_list(
    edges: list[Edge],
) -> defaultdict[str, list[tuple[Edge, Vector3D]]]:
    """Build an adjacency list representation of the graph."""
    adj_list = defaultdict(list)

    for edge in edges:
        adj_list[edge.source_id].append((edge, get_edge_vector(edge)))

        reverse_edge = edge.get_reverse_edge()
        adj_list[edge.destination_id].append(
            (reverse_edge, get_edge_vector(reverse_edge))
        )

    return adj_list


def find_paths_from_node(
    start_node: str,
    adj_list: defaultdict[str, list[tuple[Edge, Vector3D]]],
    min_length: int = 2,
    max_length: int = 4,
) -> list[PathInfo]:
    """
    Find all paths starting from a given node with length between min_length and max_length.
    """
    used_edges: set[EdgeKey] = set()
    visited_nodes: set[str] = {start_node}  # Track visited nodes

    def dfs(
        current_node: str, current_edges: list[Edge], total_displacement: Vector3D
    ) -> list[PathInfo]:
        paths = []
        if len(current_edges) >= min_length:
            paths.append((current_edges.copy(), total_displacement))

        if len(current_edges) >= max_length:
            return paths

        for edge, vector in adj_list[current_node]:
            edge_key = (edge.source_id, edge.destination_id)
            if (
                edge_key in used_edges
                or (edge.destination_id, edge.source_id) in used_edges
                or edge.destination_id in visited_nodes
            ):
                continue

            used_edges.add(edge_key)
            visited_nodes.add(edge.destination_id)
            current_edges.append(edge)

            paths.extend(
                dfs(edge.destination_id, current_edges, total_displacement + vector)
            )

            current_edges.pop()
            used_edges.remove(edge_key)
            visited_nodes.remove(edge.destination_id)

        return paths

    return dfs(start_node, [], np.zeros(3))


def format_path(edges: list[Edge]) -> str:
    """Format a path of edges into a readable string."""
    if not edges:
        return ""

    parts = []
    # Add first room
    parts.append(edges[0].source_title)

    # Add each edge and destination
    for edge in edges:
        parts.append(f"-- ({edge.direction}) -->")
        parts.append(edge.destination_title)

    return " ".join(parts)


def suggest_cycle(edges: list[Edge]) -> Edge | None:
    """
    Finds an Edge which when added would add a cycle to the graph.

    A "perfect" cycle is one where:
    1. The path starts and ends at different rooms
    2. The displacement from start to end exactly matches one of our direction vectors
    3. No room is visited twice in the path

    Returns:
        Edge | None: A suggested edge that would complete the cycle, or None if no perfect cycle is found
    """
    adj_list = build_adjacency_list(edges)

    # Find all paths from each starting node
    all_paths: list[PathInfo] = []
    for start_node in adj_list.keys():
        paths = find_paths_from_node(start_node, adj_list)
        all_paths.extend(paths)

    # For each path, check if its displacement exactly matches a direction vector
    for path_edges, displacement in all_paths:
        # Get start and end rooms
        start_room = path_edges[0].source_id
        start_room_title = path_edges[0].source_title
        end_room = path_edges[-1].destination_id
        end_room_title = path_edges[-1].destination_title

        # Skip if the start and end are already connected
        if any(x for x in adj_list[start_room] if x[0].destination_id == end_room):
            continue

        # Skip if the start or end rooms already have more than 4 exits
        if len(adj_list[start_room]) >= 4 or len(adj_list[end_room]) >= 4:
            continue

        # Skip if we've returned to the start
        if start_room == end_room:
            continue

        # Check if displacement matches any direction vector
        for direction, vector in DIRECTION_VECTORS.items():
            if np.array_equal(
                displacement, -vector
            ):  # Note the negative since we want to close the cycle
                # Found a perfect match! Create the closing edge
                return Edge(
                    source_id=end_room,
                    source_title=end_room_title,
                    destination_id=start_room,
                    destination_title=start_room_title,
                    direction=direction,
                    return_direction=next(
                        d
                        for d, v in DIRECTION_VECTORS.items()
                        if np.array_equal(v, vector)
                    ),
                )

    return None


def find_and_print_incomplete_cycles(edges: list[Edge], n_paths: int = 5) -> None:
    """Find and print the N paths in the graph that are closest to forming cycles."""
    adj_list = build_adjacency_list(edges)

    # Find all paths from each starting node
    all_paths: list[PathInfo] = []
    for start_node in adj_list.keys():
        paths = find_paths_from_node(start_node, adj_list)
        all_paths.extend(paths)

    # Sort by displacement magnitude
    sorted_paths = sorted(all_paths, key=lambda p: np.linalg.norm(p[1]))[:n_paths]

    # Print results
    for i, (path_edges, displacement) in enumerate(sorted_paths, 1):
        displacement_magnitude = np.linalg.norm(displacement)

        # Find best closing direction
        best_direction = min(
            DIRECTION_VECTORS.items(), key=lambda x: np.linalg.norm(displacement + x[1])
        )[0]

        print(f"\nAlmost Cycle {i} (displacement: {displacement_magnitude:.2f}):")
        print(format_path(path_edges))
        print(
            f"Suggested connection: {path_edges[-1].destination_title} --({best_direction})--> {path_edges[0].source_title}"
        )
