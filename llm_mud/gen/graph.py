from collections import defaultdict
import networkx as nx
from dataclasses import dataclass
import networkx as nx
import random

from llm_mud.gen.data_model import Edge


@dataclass
class SubgraphResult:
    """Results of subgraph calculation.

    Attributes:
        edges: List of edges that are within the subgraph
        fully_contained_ids: Set of room IDs where all their edges are within the subgraph
        boundary_ids: Set of room IDs that have at least one edge outside the subgraph
    """

    edges: list[Edge]
    fully_contained_ids: set[str]
    boundary_ids: set[str]


def get_room_ids(edges: list[Edge]) -> set[str]:
    """Get all room IDs from the edges."""
    return set(edge.source_id for edge in edges) | set(
        edge.destination_id for edge in edges
    )


def get_random_room_id(edges: list[Edge], max_exits: int) -> str:
    """Get a random room ID from the edges."""
    # Get all room IDs with fewer than max_exits exits
    id_counts = defaultdict(int)
    for edge in edges:
        id_counts[edge.source_id] += 1
        id_counts[edge.destination_id] += 1

    valid_room_ids = [id for id, count in id_counts.items() if count < max_exits]
    return random.choice(list(valid_room_ids))


def get_subgraph(edges: list[Edge], room_id: str, max_steps: int) -> SubgraphResult:
    """Get the subgraph of rooms within max_steps from room_id.

    Args:
        edges: List of Edge objects representing connections between rooms
        room_id: Starting room ID to build subgraph from
        max_steps: Maximum number of steps/hops from the starting room

    Returns:
        SubgraphResult containing the subgraph edges and classification of nodes
    """
    # Create a directed graph
    G = nx.DiGraph()

    # Create a mapping of node_id -> list of edges that include this node
    node_edges: dict[str, list[Edge]] = {}
    for edge in edges:
        G.add_edge(edge.source_id, edge.destination_id)
        G.add_edge(edge.destination_id, edge.source_id)

        # Add edge to both source and destination mappings
        node_edges.setdefault(edge.source_id, []).append(edge)
        node_edges.setdefault(edge.destination_id, []).append(edge)

    # Get all nodes within max_steps of our starting node
    reachable_nodes = set(nx.ego_graph(G, room_id, radius=max_steps).nodes())

    # Filter edges to only those where both ends are in our reachable set
    subgraph_edges = [
        edge
        for edge in edges
        if edge.source_id in reachable_nodes and edge.destination_id in reachable_nodes
    ]

    # Classify nodes as fully contained or boundary
    fully_contained_ids = set()
    boundary_ids = set()

    for node_id in reachable_nodes:
        # Get all edges for this node
        node_edge_list = node_edges.get(node_id, [])

        # Check if all connected nodes are in our subgraph
        all_connections_in_subgraph = all(
            edge.destination_id in reachable_nodes and edge.source_id in reachable_nodes
            for edge in node_edge_list
        )

        if all_connections_in_subgraph:
            fully_contained_ids.add(node_id)
        else:
            boundary_ids.add(node_id)

    return SubgraphResult(
        edges=subgraph_edges,
        fully_contained_ids=fully_contained_ids,
        boundary_ids=boundary_ids,
    )
