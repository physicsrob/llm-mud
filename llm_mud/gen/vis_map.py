import networkx as nx
import matplotlib

# Use Agg backend instead of GTK
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from llm_mud.gen.data_model import Edge


def visualize(edges: list[Edge], title: str, outfile: str) -> None:
    """Create and save a visualization of the world map.

    Args:
        edges: List of Edge objects representing room connections
        title: Title for the visualization
        outfile: Path where the output image should be saved
    """
    G = nx.DiGraph()

    # Build graph from edges
    for edge in edges:
        G.add_node(edge.source_id, title=edge.source_title)
        G.add_node(edge.destination_id, title=edge.destination_title)
        G.add_edge(
            edge.source_id,
            edge.destination_id,
            direction=edge.direction,
            return_direction=edge.return_direction,
        )

    plt.figure(figsize=(12, 8))

    # Try hierarchical layout first
    try:
        pos = nx.planar_layout(G)
    except:
        # Fallback to spring layout with better parameters
        pos = nx.spring_layout(G, k=2, iterations=100)

    # Draw nodes with slightly larger size
    nx.draw_networkx_nodes(G, pos, node_color="lightblue", node_size=2000, alpha=0.6)

    # Draw edges with arrows
    nx.draw_networkx_edges(
        G,
        pos,
        edge_color="gray",
        arrowsize=20,
        arrowstyle="->",
        min_source_margin=15,
        min_target_margin=15,
    )

    # Add node labels (room titles)
    labels = nx.get_node_attributes(G, "title")
    nx.draw_networkx_labels(G, pos, labels, font_size=8)

    # Add edge labels with improved positioning
    for node1, node2, data in G.edges(data=True):
        x1, y1 = pos[node1]
        x2, y2 = pos[node2]

        # Calculate edge angle
        dx = x2 - x1
        dy = y2 - y1
        angle = np.arctan2(dy, dx)

        # Calculate midpoint with offset
        mid_x = x1 + dx * 0.5
        mid_y = y1 + dy * 0.5

        # Adjust text rotation based on edge angle
        rotation = np.degrees(angle)
        if rotation > 90 or rotation < -90:
            rotation += 180

        # Add background box to labels
        bbox_props = dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8)

        # Place single direction label
        plt.annotate(
            data["direction"],
            xy=(mid_x, mid_y),
            xytext=(0, 0),
            textcoords="offset points",
            bbox=bbox_props,
            fontsize=8,
            rotation=rotation,
            rotation_mode="anchor",
            ha="center",
            va="center",
        )

    plt.title(title)
    plt.axis("off")
    plt.tight_layout()

    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"\nWorld map has been saved to '{outfile}'")
