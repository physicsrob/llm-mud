import asyncio
from pathlib import Path
from mad.core.location import Location, LocationExit
from mad.core.world import World
from mad.gen.data_model import (
    WorldDescription, LocationDescription, WorldDesign
)
from .describe_world_agent import describe_world
from .create_character_agent import create_character_agent
from .story_world_design_agent import create_world_design
from .world_merger_agent import merge_worlds 
from .world_improver_agent import improve_world_design
from .location_exit_agent import get_location_exits
from devtools import debug

# import logfire
# logfire.configure(
#     send_to_logfire=False
# )

async def update_design_exits(design: WorldDesign):
    print("\nCreating location exits...")
    exits_tasks = []
    for src_id, dest_ids in design.location_connections.items():
        location = design.find_location_by_id(src_id)
        task = asyncio.create_task(
            get_location_exits(location, design.locations, dest_ids)
        )
        exits_tasks.append(task)
    
    # Wait for all exit generation tasks to complete
    exits = await asyncio.gather(*exits_tasks)
    
    exit_mapping = {}
    for (src_id, dest_ids), dest_exits in zip(design.location_connections.items(), exits):
        exit_mapping[src_id] = dest_exits

    design.location_exits = exit_mapping


async def design_world(theme: str, story_count: int = 10) -> WorldDesign:
    """
    Generate a world design based on the specified theme.
    
    This function handles the first phase of world creation, generating the design only.
    It does not create the final World/Location objects.
    
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
        task = asyncio.create_task(create_world_design(world_desc, title, theme))
        tasks.append(task)
    
    # Wait for all tasks to complete
    story_designs = await asyncio.gather(*tasks)
    if not len(story_designs):
        raise ValueError("No story worlds were generated")
    story_design = story_designs[0] 

    for other_design in story_designs[1:]:
        print("\nMerging story worlds...")
        await merge_worlds(story_design, other_design)
   
    await update_design_exits(story_design)
    return story_design


def convert_design_to_world(world_design: WorldDesign) -> World:
    """
    Convert a world design into a playable World with Location objects.
    
    This function handles the second phase of world creation, converting the design
    into actual World and Location objects that can be used in the game.
    
    Args:
        world_design: The WorldDesign to convert
        
    Returns:
        A World object that can be used in the game
    """
    # Convert to actual Location objects
    world_locations = []
    for location in world_design.locations:
        if location.id not in world_design.location_exits:
            print(f"Missing exits for location: {location.id}")
            continue

        # Create LocationExit objects
        location_exit_objects = [
            LocationExit(
                destination_id=exit.destination_id,
                exit_description=exit.exit_description,
                exit_name=exit.exit_name
            ) for exit in world_design.location_exits[location.id]
        ]
        
        location = Location(
            id=location.id,
            title=location.title,
            brief_description=location.brief_description,
            long_description=location.long_description,
            exits={exit.exit_name: exit.destination_id for exit in location_exit_objects},
            exit_objects=location_exit_objects
        )
        world_locations.append(location)
    
    # Create the World object with all locations
    world = World(
        title=world_design.world_description.title, 
        description=world_design.world_description.description,
        locations={location.id: location for location in world_locations}
    )
    
    # Set the starting location
    if world_design.starting_location_id:
        # Verify the starting location exists
        if world_design.starting_location_id not in world.locations:
            raise ValueError(f"Starting location {world_design.starting_location_id} not found in world")
        world.set_starting_location(world_design.starting_location_id)
    elif world_locations:
        # If no starting location was specified, use the first location
        world.set_starting_location(world_locations[0].id)
    else:
        # This should never happen
        raise ValueError("No locations were created")
    
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


async def improve_world_design_iteration(world_design: WorldDesign) -> None:
    """
    Improve an existing world design by running it through the improvement process again.
    Modifies the provided world_design in place.
    
    Args:
        world_design: The WorldDesign to improve, modified in place
    """
    # Run the improvement process (modifies the design in-place)
    print("\nImproving world design location-by-location...")
    await improve_world_design(world_design)
    
    await update_design_exits(world_design)
        
