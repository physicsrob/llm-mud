import asyncio
from pathlib import Path
from mad.core.location import Location, LocationExit
from mad.core.world import World
from mad.gen.data_model import (
    WorldDescription, LocationDescription, LocationDescriptionWithExits, 
    WorldDesign, StoryWorldComponents
)
from .describe_world_agent import describe_world
from .create_character_agent import create_character_agent
from .create_world_story_agent import create_story_world
from .world_merger_agent import merge_story_worlds, apply_merge_plan
from .world_improver_agent import improve_world_design
from .location_exit_agent import get_location_exits
from devtools import debug

# import logfire
# logfire.configure(
#     send_to_logfire=False
# )

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
        task = asyncio.create_task(create_story_world(world_desc, title, theme))
        tasks.append(task)
    
    # Wait for all tasks to complete
    story_worlds = await asyncio.gather(*tasks)

    # If we have multiple stories, merge them
    starting_location_id = None
    if len(story_worlds) > 1:
        print("\nMerging story worlds...")
        merge_plan = await merge_story_worlds(story_worlds)
        
        # Apply the merge plan
        print("\nApplying merge plan...")
        merged_world = apply_merge_plan(merge_plan, story_worlds)
        starting_location_id = merge_plan.starting_location_id
    elif len(story_worlds) == 1:
        merged_world = story_worlds[0]
    else:
        raise ValueError("No story worlds were generated")
    
    # Generate detailed exits for all locations
    print("\nGenerating location exits...")
    locations_with_exits_tasks = []
    for location in merged_world.locations:
        # Get connected location IDs for this location
        connected_ids = merged_world.location_connections.get(location.id, [])
        task = asyncio.create_task(
            get_location_exits(location, merged_world.locations, connected_ids)
        )
        locations_with_exits_tasks.append(task)
    
    # Wait for all exit generation tasks to complete
    locations_with_exits = await asyncio.gather(*locations_with_exits_tasks)
    
    # If no starting location was specified or only one story, use the first location
    if not starting_location_id and locations_with_exits:
        starting_location_id = locations_with_exits[0].id
    
    # Create the WorldDesign
    world_design = WorldDesign(
        world_description=world_desc,
        locations=locations_with_exits,
        characters=merged_world.characters,
        character_locations=merged_world.character_locations,
        starting_location_id=starting_location_id
    )
    
    return world_design


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
    for location_with_exits in world_design.locations:
        # Create LocationExit objects
        location_exit_objects = [
            LocationExit(
                destination_id=exit.destination_id,
                exit_description=exit.exit_description,
                exit_name=exit.exit_name
            ) for exit in location_with_exits.exits
        ]
        
        # Convert LocationDescriptionWithExits to a Location object
        location = Location(
            id=location_with_exits.id,
            title=location_with_exits.title,
            brief_description=location_with_exits.brief_description,
            long_description=location_with_exits.long_description,
            exits={exit.exit_name: exit.destination_id for exit in location_with_exits.exits},
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
    
    # Generate detailed exits for all locations
    print("\nRecreating location exits...")
    locations_with_exits_tasks = []
    for location in world_design.locations:
        # Get connected location IDs for this location
        connected_ids = [exit.destination_id for exit in location.exits]
        task = asyncio.create_task(
            get_location_exits(
                LocationDescription(
                    id=location.id,
                    title=location.title,
                    brief_description=location.brief_description,
                    long_description=location.long_description
                ),
                [
                    LocationDescription(
                        id=loc.id,
                        title=loc.title,
                        brief_description=loc.brief_description,
                        long_description=loc.long_description
                    ) for loc in world_design.locations
                ],
                connected_ids
            )
        )
        locations_with_exits_tasks.append(task)
    
    # Wait for all exit generation tasks to complete
    locations_with_exits = await asyncio.gather(*locations_with_exits_tasks)
    
    # Update the locations in the world design
    world_design.locations.clear()
    world_design.locations.extend(locations_with_exits)
        
