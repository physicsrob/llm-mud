import asyncio
from mad.core.room import Room
from mad.core.world import World
from mad.gen.data_model import Edge, WorldDescription
from mad.gen.describe_room_agent import describe_room
from .starting_room import generate_starting_room
from .add_edge_agent import add_edge
from .describe_world_agent import describe_world
from .vis_map import visualize
from .create_character_agent import create_character_agent
from .create_world_story_agent import create_world_story, WorldStory
from .describe_story_characters_agent import describe_story_characters, StoryCharacters
from devtools import debug
from mad.gen.graph import get_random_room_id, get_subgraph
from mad.gen.cycle_finder import suggest_cycle

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


async def create_world(theme: str, room_count: int = 10, 
                 skip_map: bool = False, 
                 skip_room_details: bool = False, 
                 skip_chars: bool = False,
                 skip_stories: bool = False) -> World:
    """Create a new world with the specified theme.
    
    Args:
        theme: The theme of the world
        room_count: The number of rooms to generate
        skip_map: If True, don't generate connections between rooms
        skip_room_details: If True, don't generate detailed room descriptions
        skip_chars: If True, don't generate characters for rooms
        skip_stories: If True, don't generate stories for the world
    """
    world_desc = await describe_world(theme)
    print("\nGenerated World:")
    debug(world_desc)
    
    # Start generating stories in parallel if not skipped
    stories_tasks = []
    if not skip_stories and world_desc.story_titles:
        print("\nGenerating stories in parallel...")
        for title in world_desc.story_titles:
            task = asyncio.create_task(create_world_story(world_desc, title))
            stories_tasks.append(task)
    
    if stories_tasks:
        print("\nAwaiting story generation tasks...")
        stories = await asyncio.gather(*stories_tasks)
        print(f"\nGenerated {len(stories)} stories:")
        
        # Process characters from each story in parallel
        character_tasks = []
        for story in stories:
            print(f"\n--- {story.title} ---")
            print(f"Length: {len(story.content)} characters")
            # Print a condensed version of the story (first 500 chars)
            preview = story.content[:500] + "..." if len(story.content) > 500 else story.content
            print(preview)
            
            # Create task to extract characters from the story
            task = asyncio.create_task(describe_story_characters(story))
            character_tasks.append(task)
        
        # Wait for all character extraction tasks to complete
        print("\nExtracting characters from stories...")
        story_characters = await asyncio.gather(*character_tasks)
        
        # Display the characters from each story
        for i, characters in enumerate(story_characters):
            story_title = stories[i].title
            print(f"\nCharacters from '{story_title}':")
            for character in characters.characters:
                print(f"  - {character.name}: {character.description}")

    # Always create at least the starting room
    starting_room_desc = await generate_starting_room(world_desc)
    print("\nGenerated Room:")
    debug(starting_room_desc)

    edges = []
    existing_rooms = {starting_room_desc.id}
    
    # Only generate the map if not skipped
    if not skip_map:
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
    else:
        # For a disconnected world, just create placeholders for the requested number of rooms
        print("Skipping map generation - creating disconnected rooms")
        for i in range(1, room_count):
            room_id = f"room_{i}"
            existing_rooms.add(room_id)

    # Create a room description for each room
    rooms = {}
    for room_id in existing_rooms:
        if room_id == starting_room_desc.id:
            # Always use the starting room description we already generated
            room_desc = starting_room_desc
        elif skip_room_details:
            # Create minimal placeholder rooms if details are skipped
            room_desc_title = f"Room {room_id}"
            room_desc = type('PlaceholderRoom', (), {
                'id': room_id,
                'title': room_desc_title,
                'brief_description': f"A placeholder room in {world_desc.title}",
                'long_description': f"A placeholder room in {world_desc.title}. No detailed description available."
            })
        else:
            # Generate detailed room descriptions
            room_desc = await describe_room(world_desc, edges, room_id)
            debug(room_desc)
        
        # Set up room exits if we have a map
        room_exits = {}
        if not skip_map:
            for edge in edges:
                if edge.source_id == room_id:
                    room_exits[edge.direction] = edge.destination_id
                elif edge.destination_id == room_id:
                    room_exits[edge.return_direction] = edge.source_id
        
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
        description=world_desc.description,
        rooms=rooms,
        starting_room_id=starting_room_desc.id,
    )
    
    # Create characters only if not skipped
    if not skip_chars:
        print("\nGenerating characters for each room...")
        chars = []

        for room_id, room in rooms.items():
            character = await create_character_agent(world_desc, room, world, chars)
            
            # Add character to the world
            world.characters[character.id] = character
            
            # Add character to the room
            if room_id not in world.room_characters:
                world.room_characters[room_id] = []
            world.room_characters[room_id].append(character.id)
            chars.append(character)
            
            print(f"Created character '{character.name}' in room '{room.title}'")
    else:
        print("Skipping character generation")
    
    
    return world
