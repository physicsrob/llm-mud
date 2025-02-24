from llm_mud.core.room import Room
from llm_mud.core.world import World
from llm_mud.gen.data_model import Edge, WorldDescription
from llm_mud.gen.describe_room_agent import describe_room
from .starting_room import generate_starting_room
from .add_edge_agent import add_edge
from .describe_world_agent import describe_world
from .vis_map import visualize
from devtools import debug
from llm_mud.gen.graph import get_random_room_id, get_subgraph
from llm_mud.gen.cycle_finder import suggest_cycle

max_exits = 4


async def expand_map(world_desc: WorldDescription, edges: list[Edge]) -> Edge | None:
    # Randomly select a room from the existing rooms
    room_id = get_random_room_id(edges, max_exits - 1)

    # Generate a subgraph of rooms within N steps from the selected room
    subgraph = get_subgraph(edges, room_id, 2)

    # Add an exit to the subgraph
    new_edge = await add_edge(world_desc, subgraph.edges, room_id)

    # Validate that the edge is not a duplicate
    is_duplicate = False
    for edge in edges:
        if (
            edge.source_id == new_edge.source_id
            and edge.direction == new_edge.direction
        ):
            is_duplicate = True
        if (
            edge.destination_id == new_edge.source_id
            and edge.return_direction == new_edge.direction
        ):
            is_duplicate = True

    if is_duplicate:
        print(f"Warning: Skipping duplicate edge: {new_edge}")
        return None

    # Count the number of exits in the destination room
    exits = 0
    for edge in edges:
        if edge.destination_id == new_edge.destination_id:
            exits += 1

    # If the destination room has too many exits, skip the edge
    if exits > max_exits:
        print(f"Warning: Skipping edge to room with too many exits: {new_edge}")
        return None

    # Validate that the edge does not connect to a room that is not in the subgraph
    if new_edge.destination_id in subgraph.boundary_ids:
        print(f"Warning: Skipping edge to non-subgraph room: {new_edge}")
        return None

    # Return the updated list of edges
    return new_edge


async def create_world(theme: str, room_count: int = 10) -> World:
    """Create a new world with the specified theme."""
    world_desc = await describe_world(theme)
    print("\nGenerated World:")
    debug(world_desc)

    starting_room_desc = await generate_starting_room(world_desc)
    print("\nGenerated Room:")
    debug(starting_room_desc)

    edges = [] + starting_room_desc.exits
    existing_rooms = set(edge.destination_id for edge in starting_room_desc.exits) | {
        starting_room_desc.id
    }

    while len(existing_rooms) < room_count:
        new_edge = await expand_map(world_desc, edges)
        if not new_edge:
            print("Failed to add exit")
            continue

        edges.append(new_edge)

        if new_edge.destination_id not in existing_rooms:
            print(f"New destination room {new_edge.destination_id}")
        elif new_edge.source_id not in existing_rooms:
            print(f"New source room {new_edge.source_id}")
        else:
            print(f"New edge {new_edge.source_id} -> {new_edge.destination_id}")

        cycle_edge = suggest_cycle(edges)
        if cycle_edge:
            print(f"Auto-adding cycle edge: {cycle_edge}\n")
            edges.append(cycle_edge)

        existing_rooms.add(new_edge.destination_id)
        existing_rooms.add(new_edge.source_id)

    visualize(edges, f"World Map: {theme}", "world_map.png")

    # Create a room description for each room
    rooms = {}
    for room_id in existing_rooms:
        room_desc = await describe_room(world_desc, edges, room_id)
        room_exits = {}
        for edge in edges:
            if edge.source_id == room_id:
                room_exits[edge.direction] = edge.destination_id
            elif edge.destination_id == room_id:
                room_exits[edge.return_direction] = edge.source_id
        debug(room_desc)
        rooms[room_id] = Room(
            id=room_id,
            title=room_desc.title,
            brief_description=room_desc.brief_description,
            long_description=room_desc.long_description,
            exits=room_exits,
        )

    # Create the world
    world = World(
        title=world_desc.title,
        brief_description=world_desc.brief_description,
        long_description=world_desc.long_description,
        other_details=world_desc.other_details,
        rooms=rooms,
        starting_room_id=starting_room_desc.id,
    )
    return world
