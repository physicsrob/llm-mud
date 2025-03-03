from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List, Tuple

from mad.gen.data_model import WorldDesign
from mad.config import powerful_model_instance


# The prompt that guides location duplication detection
location_duplication_prompt = """
You are a master world builder with expertise in narrative design and world architecture.

Your task is to examine two locations from different story worlds and determine if they represent the same physical location.

Consider these factors:
- Similar names and titles often suggest the same location
- Similar descriptions of the environment or architecture
- Connection rooms (e.g paths, corridors, hallways) should usually not be marked as duplicate

Be conservative in your assessment - only identify locations as duplicates if they are clearly intended to represent the same place.
"""

# The prompt that guides finding logical merge points between worlds
merge_points_prompt = """
You are a master world builder specializing in creating cohesive, interconnected story worlds.

Your task is to identify natural connection points between two different story worlds. These connection 
points will serve as doorways or passages that link the worlds, allowing characters and players to 
travel between them.

Ideal connection points should:
1. Make narrative sense (e.g., a forest in one world connecting to woods in another)
2. Not disrupt the internal logic of either world
3. Allow for natural, believable travel between worlds
4. Preferably be peripheral locations rather than central hubs
5. Work in both directions (characters from either world might discover the connection)

Choose 1-2 pairs of locations that would make the most seamless and narratively interesting connections.
Each pair of locations will be the location id from a location in world 1 combined with the location id from a location in world 2.

"""

async def are_locations_duplicate(design1: WorldDesign, design2: WorldDesign, location_id1: str, location_id2: str) -> bool:
    """
    Determine if two locations from different world designs represent the same physical location.
    
    Args:
        design1: First world design containing the first location
        design2: Second world design containing the second location
        location_id1: ID of the location in the first world design
        location_id2: ID of the location in the second world design
        
    Returns:
        Boolean indicating whether the locations are duplicates
    """
    # Find the locations in their respective designs
    location1 = design1.find_location_by_id(location_id1)
    location2 = design2.find_location_by_id(location_id2)
    
    if not location1 or not location2:
        # If either location doesn't exist, they can't be duplicates
        return False
    
    # Initialize the agent for duplication detection
    duplication_agent = Agent(
        model=powerful_model_instance,
        result_type=bool,
        system_prompt=location_duplication_prompt,
        retries=1,
        model_settings={"temperature": 0.1},
    )
    
    # Run the agent to detect duplication
    user_prompt = f"""
    I need to determine if these two locations from different story worlds represent the same physical location.
    
    LOCATION 1:
    Title: {location1.title}
    Description: {location1.brief_description}
    
    LOCATION 2:
    Title: {location2.title}
    Description: {location2.brief_description}
    
    Please analyze these locations and determine if they are duplicates of the same place.
    """
    
    result = await duplication_agent.run(user_prompt)
    return result.data


class _MergePointsResult(BaseModel):
    """Result of finding merge points between two world designs."""
    merge_points: List[Tuple[str, str]] = Field(
        description="List of tuples containing location IDs that should be connected. Each tuple contains (design1_location_id, design2_location_id)",
        min_items=1,
        max_items=2
    )


async def find_merge_points(design1: WorldDesign, design2: WorldDesign) -> List[Tuple[str, str]]:
    """
    Identify logical connection points between two world designs.
    
    This function analyzes locations in both world designs and determines which 
    pairs of locations would make the most natural and narratively interesting
    connections between the worlds.
    
    Args:
        design1: The first world design
        design2: The second world design
        
    Returns:
        A list of tuples containing pairs of location IDs (design1_id, design2_id)
        that should be connected
        
    Raises:
        ValueError: If no valid merge points can be found
    """
    # Get sets of valid location IDs for validation
    design1_location_ids = {loc.id for loc in design1.locations}
    design2_location_ids = {loc.id for loc in design2.locations}
    
    # Initialize the agent for finding merge points
    merge_agent = Agent(
        model=powerful_model_instance,
        result_type=_MergePointsResult,
        system_prompt=merge_points_prompt,
        retries=2,  # Increased retries for better reliability
        model_settings={"temperature": 0.3},
    )
    
    # Prepare location details for both worlds
    world1_locations = []
    world2_locations = []
    
    # Format locations from design1
    for location in design1.locations:
        world1_locations.append(
            f"World 1 Location ID: {location.id}\n"
            f"Title: {location.title}\n"
            f"Description: {location.brief_description}\n"
            f"---\n"
        )
    
    # Format locations from design2
    for location in design2.locations:
        world2_locations.append(
            f"World 2 Location ID: {location.id}\n"
            f"Title: {location.title}\n"
            f"Description: {location.brief_description}\n"
            f"---\n"
        )
    
    # Add explicit lists of valid IDs
    valid_ids_world1 = sorted(list(design1_location_ids))
    valid_ids_world2 = sorted(list(design2_location_ids))
    
    # Create the prompt for the agent
    user_prompt = f"""
    I need to identify 1-2 pairs of locations that would serve as natural connection points between two story worlds.
    
    Locations in World 1:
    {''.join(world1_locations)}
    
    Locations in World 2:
    {''.join(world2_locations)}
    
    Valid location IDs for World 1: {valid_ids_world1}
    Valid location IDs for World 2: {valid_ids_world2}
    
    Please analyze these worlds and identify 1-2 pairs of locations (one from each world) that would 
    make the most natural and narratively interesting connection points between them.
    
    For each connection, specify the location ID from World 1 and the location ID from World 2 that 
    should be connected. Include your reasoning for why these would make good merge points.
    
    IMPORTANT: The location IDs you select MUST be from the valid ID lists provided above.
    """
    
    # Run the agent to find merge points
    result = await merge_agent.run(user_prompt)
    merge_points = result.data.merge_points
    
    # Validate the merge points
    valid_merge_points = []
    for point1, point2 in merge_points:
        # Check if both IDs exist in their respective designs
        if point1 in design1_location_ids and point2 in design2_location_ids:
            valid_merge_points.append((point1, point2))
        else:
            print(f"Warning: Invalid merge point ({point1}, {point2}) - IDs not found in designs")
    
    # Ensure we have at least one valid merge point
    if not valid_merge_points:
        print(f"FATAL ERROR: Could not merge worlds!")
        exit()

    return valid_merge_points


async def harmonize_worlds(design1: WorldDesign, design2: WorldDesign):
    """
    Harmonize two world designs by identifying and resolving duplicate locations.
    
    This function identifies key locations in both world designs that represent the same
    physical places. When duplicates are found, it updates the IDs in design2 to match
    those in design1, effectively preparing the worlds to be merged without duplication.
    
    The function also ensures all non-duplicate location IDs are distinct across both worlds
    by adding a suffix to any conflicting IDs in design2.
    
    The function modifies design2 in place, leaving design1 unchanged. Only key locations
    (those with is_key=True) are considered for harmonization, as connector locations
    typically should remain distinct.
    
    Args:
        design1: The primary world design, which remains unchanged
        design2: The secondary world design to harmonize with design1, modified in place
    """
    import asyncio
    
    # First phase: identify intentional duplicates (same physical location)
    location1_ids = set(loc.id for loc in design1.locations)
    location2_ids = set(loc.id for loc in design2.locations)
    
    # Filter for key locations only
    key_locations1 = [loc for loc in design1.locations if loc.is_key]
    key_locations2 = [loc for loc in design2.locations if loc.is_key]
    
    # Create tasks for all location pairs that need to be checked
    tasks = []
    location_pairs = []
    
    for location1 in key_locations1:
        for location2 in key_locations2:
            task = are_locations_duplicate(design1, design2, location1.id, location2.id)
            tasks.append(task)
            location_pairs.append((location1, location2))
    
    # Run all duplication checks concurrently
    dupe_results = await asyncio.gather(*tasks)
    
    # Process the results
    for (location1, location2), is_dupe in zip(location_pairs, dupe_results):
        if is_dupe:
            design2.rename_location_id(location2.id, location1.id)
        elif location2.id in location1_ids:
            # ID conflict but not a duplicate location - create a unique ID with suffix
            suffix = 1
            while (f"{location2.id}_{suffix}" in location1_ids) or (f"{location2.id}_{suffix}" in location2_ids):
                suffix += 1
            design2.rename_location_id(location2.id, f"{location2.id}_{suffix}")


async def merge_worlds(design1: WorldDesign, design2: WorldDesign):
    """
    Merge design2 into design1. Modifies both designs in place.
    """
    
    # Step 1: Harmonize worlds
    await harmonize_worlds(design1, design2)

    # Step 2: Find points where we can link the two worlds
    merge_points = await find_merge_points(design1, design2)

    # Step 3: Add all locations and characters from design2 to design1
    design1.add_design(design2)

    # Step 4: Link at the merge points
    for loc1, loc2 in merge_points:
        design1.ensure_bidirectional_exits(loc1, loc2)


