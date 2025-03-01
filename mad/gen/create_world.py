import asyncio
from pathlib import Path
from mad.core.room import Room, RoomExit
from mad.core.world import World
from mad.gen.data_model import (
    WorldDescription, RoomDescription, RoomDescriptionWithExits, 
    WorldDesign, StoryWorldComponents
)
from .describe_world_agent import describe_world
from .create_character_agent import create_character_agent
from .create_world_story_agent import create_story_world
from .world_merger_agent import merge_story_worlds, apply_merge_plan
from .world_improver_agent import improve_world_design, apply_improvement_plan
from .room_exit_agent import get_room_exits
from devtools import debug

import logfire
logfire.configure(
    send_to_logfire=False
)

async def design_world(theme: str, story_count: int = 10) -> WorldDesign:
    """
    Generate a world design based on the specified theme.
    
    This function handles the first phase of world creation, generating the design only.
    It does not create the final World/Room objects.
    
    Args:
        theme: The theme of the world to create
        story_count: The number of stories to generate
        
    Returns:
        A WorldDesign object representing the complete design
    """
    world_desc = await describe_world(theme)
    print("\nGenerated World:")
    debug(world_desc)
    
    # Generate stories and their components in parallel
    print(f"\nGenerating {len(world_desc.story_titles)} stories...")
    tasks = []
    for title in world_desc.story_titles[:story_count]:
        print(f"  - {title}")
        task = asyncio.create_task(create_story_world(world_desc, title))
        tasks.append(task)
    
    # Wait for all tasks to complete
    story_worlds = await asyncio.gather(*tasks)

    # If we have multiple stories, merge them
    starting_room_id = None
    if len(story_worlds) > 1:
        print("\nMerging story worlds...")
        merge_plan = await merge_story_worlds(story_worlds)
        debug(merge_plan)
        
        # Apply the merge plan
        print("\nApplying merge plan...")
        merged_world = apply_merge_plan(merge_plan, story_worlds)
        starting_room_id = merge_plan.starting_room_id
        debug(merged_world)
    elif len(story_worlds) == 1:
        merged_world = story_worlds[0]
    else:
        raise ValueError("No story worlds were generated")
    
    # Improve the world design by balancing connections
    print("\nImproving world design...")
    improvement_plan = await improve_world_design(merged_world)
    debug(improvement_plan)
    
    # Apply the improvement plan
    print("\nApplying improvement plan...")
    improved_world = apply_improvement_plan(improvement_plan, merged_world)
    debug(improved_world)
    
    # Generate detailed exits for all rooms
    print("\nGenerating room exits...")
    rooms_with_exits_tasks = []
    for room in improved_world.locations:
        # Get connected room IDs for this room
        connected_ids = improved_world.location_connections.get(room.id, [])
        task = asyncio.create_task(
            get_room_exits(room, improved_world.locations, connected_ids)
        )
        rooms_with_exits_tasks.append(task)
    
    # Wait for all exit generation tasks to complete
    rooms_with_exits = await asyncio.gather(*rooms_with_exits_tasks)
    debug(rooms_with_exits)
    
    # If no starting room was specified or only one story, use the first room
    if not starting_room_id and rooms_with_exits:
        starting_room_id = rooms_with_exits[0].id
    
    # Create the WorldDesign
    world_design = WorldDesign(
        world_description=world_desc,
        locations=rooms_with_exits,
        characters=merged_world.characters,
        character_locations=merged_world.character_locations,
        starting_room_id=starting_room_id
    )
    
    return world_design


def convert_design_to_world(world_design: WorldDesign) -> World:
    """
    Convert a world design into a playable World with Room objects.
    
    This function handles the second phase of world creation, converting the design
    into actual World and Room objects that can be used in the game.
    
    Args:
        world_design: The WorldDesign to convert
        
    Returns:
        A World object that can be used in the game
    """
    # Convert to actual Room objects
    world_rooms = []
    for room_with_exits in world_design.locations:
        # Create RoomExit objects
        room_exit_objects = [
            RoomExit(
                destination_id=exit.destination_id,
                exit_description=exit.exit_description,
                exit_name=exit.exit_name
            ) for exit in room_with_exits.exits
        ]
        
        # Convert RoomDescriptionWithExits to a Room object
        room = Room(
            id=room_with_exits.id,
            title=room_with_exits.title,
            brief_description=room_with_exits.brief_description,
            long_description=room_with_exits.long_description,
            exits={exit.exit_name: exit.destination_id for exit in room_with_exits.exits},
            exit_objects=room_exit_objects
        )
        world_rooms.append(room)
    
    # Create the World object with all rooms
    world = World(
        title=world_design.world_description.title, 
        description=world_design.world_description.description,
        rooms={room.id: room for room in world_rooms}
    )
    
    # Set the starting room
    if world_design.starting_room_id:
        # Verify the starting room exists
        if world_design.starting_room_id not in world.rooms:
            raise ValueError(f"Starting room {world_design.starting_room_id} not found in world")
        world.set_starting_room(world_design.starting_room_id)
    elif world_rooms:
        # If no starting room was specified, use the first room
        world.set_starting_room(world_rooms[0].id)
    else:
        # This should never happen
        raise ValueError("No rooms were created")
    
    return world


async def create_world(theme: str, story_count: int = 10) -> World:
    """
    Create a new world with the specified theme.
    
    This function combines both phases of world creation: designing the world
    and converting it into a playable World object.
    
    Args:
        theme: The theme of the world to create
        story_count: The number of stories to generate
        
    Returns:
        A World object that can be used in the game
    """
    # Phase 1: Design the world
    world_design = await design_world(theme, story_count)
    
    # Phase 2: Convert the design to a World object
    world = convert_design_to_world(world_design)
    
    return world


async def improve_world_design_iteration(world_design: WorldDesign) -> WorldDesign:
    """
    Improve an existing world design by running it through the improvement process again.
    
    Args:
        world_design: The WorldDesign to improve
        
    Returns:
        An improved WorldDesign
    """
    # Convert WorldDesign to StoryWorldComponents format
    components = StoryWorldComponents(
        characters=world_design.characters,
        locations=[
            RoomDescription(
                id=room.id,
                title=room.title,
                brief_description=room.brief_description,
                long_description=room.long_description
            ) for room in world_design.locations
        ],
        character_locations=world_design.character_locations,  # Preserve character locations
        location_connections={
            room.id: [exit.destination_id for exit in room.exits]
            for room in world_design.locations
        }
    )
    
    # Run the improvement process
    print("\nImproving world design...")
    improvement_plan = await improve_world_design(components)
    debug(improvement_plan)
    
    # Apply the improvement plan
    print("\nApplying improvement plan...")
    improved_world = apply_improvement_plan(improvement_plan, components)
    debug(improved_world)
    
    # Generate detailed exits for all rooms
    print("\nRecreating room exits...")
    rooms_with_exits_tasks = []
    for room in improved_world.locations:
        # Get connected room IDs for this room
        connected_ids = improved_world.location_connections.get(room.id, [])
        task = asyncio.create_task(
            get_room_exits(room, improved_world.locations, connected_ids)
        )
        rooms_with_exits_tasks.append(task)
    
    # Wait for all exit generation tasks to complete
    rooms_with_exits = await asyncio.gather(*rooms_with_exits_tasks)
    debug(rooms_with_exits)
    
    # Create the improved WorldDesign
    improved_design = WorldDesign(
        world_description=world_design.world_description,
        locations=rooms_with_exits,
        characters=world_design.characters,
        character_locations=improved_world.character_locations,  # Preserve character locations
        starting_room_id=world_design.starting_room_id
    )
    
    return improved_design
        
