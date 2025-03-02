from devtools import debug
import json
import random
from pydantic_ai import Agent
from copy import deepcopy

from mad.config import location_model_instance 
from mad.gen.data_model import (
    StoryWorldComponents, 
    LocationImprovementPlan, 
    LocationDescription, 
    WorldDesign,
    LocationDescriptionWithExits,
    LocationExit
)


def find_location_by_id(story_components: StoryWorldComponents, location_id: str) -> LocationDescription | None:
    """
    Helper function to find a location object by its ID.
    
    Args:
        story_components: A StoryWorldComponents object containing locations
        location_id: The ID of the location to find
        
    Returns:
        LocationDescription object if found, None otherwise
    """
    for location in story_components.locations:
        if location.id == location_id:
            return location
    return None


def ensure_bidirectional_connections(components: StoryWorldComponents, source_id: str, dest_id: str) -> None:
    """
    Ensures that a bidirectional connection exists between two locations.
    
    Args:
        components: The StoryWorldComponents to modify
        source_id: The first location ID
        dest_id: The second location ID
    """
    # Initialize connection lists if they don't exist
    if source_id not in components.location_connections:
        components.location_connections[source_id] = []
    if dest_id not in components.location_connections:
        components.location_connections[dest_id] = []
    
    # Add bidirectional connections if they don't exist
    if dest_id not in components.location_connections[source_id]:
        components.location_connections[source_id].append(dest_id)
    if source_id not in components.location_connections[dest_id]:
        components.location_connections[dest_id].append(source_id)


def get_connection_summary(components: StoryWorldComponents, new_ids: set[str] = None) -> dict:
    """
    Generates a summary of connections for all locations in the components.
    
    Args:
        components: The StoryWorldComponents to analyze
        new_ids: Optional set of location IDs to highlight as new
        
    Returns:
        Dictionary with connection counts and statistics
    """
    # Calculate connection counts for all locations
    all_connection_counts = {
        loc_id: len(connections) 
        for loc_id, connections in components.location_connections.items()
    }
    
    # Find overcrowded locations
    overcrowded = {k: v for k, v in all_connection_counts.items() if v > 4}
    
    # Calculate total rooms and connections
    total_rooms = len(components.locations)
    # Divide by 2 since connections are bidirectional
    total_connections = sum(len(connections) for connections in components.location_connections.values()) // 2
    
    # Create a list of locations with their names and connection counts, sorted by ID
    location_details = []
    for loc_id, count in sorted(all_connection_counts.items(), key=lambda x: x[0]):
        loc_name = next((loc.title for loc in components.locations if loc.id == loc_id), "Unknown")
        is_new = new_ids and loc_id in new_ids
        location_details.append({
            "id": loc_id,
            "name": loc_name,
            "connections": count,
            "is_new": is_new
        })
    
    return {
        "all_counts": all_connection_counts,
        "overcrowded": overcrowded,
        "total_rooms": total_rooms,
        "total_connections": total_connections,
        "location_details": location_details
    }


# The prompt that guides world improvement for a single location
single_location_improver_prompt = """
You are a master world builder with expertise in game level design and world architecture.

Your task is to analyze a specific location in a game world and improve its design by ensuring it doesn't have too many 
connections (no more than 4 connections per location). When a location has more than 4 connections,
you'll create new intermediate locations to better distribute these connections.

Given a specific overcrowded location, you will:

1. Analyze the input location 
   - Examine the location that has more than 4 connections to other locations
   - Determine which connections should be redistributed
   - Consider the theme and narrative purpose of these connections

2. Replace the input location with two output locations
   - When combined the two output locations should serve a similar narrative pupose as the original input location
   - In general make the two locations make sense together
   - Design new locations that can serve as intermediaries to reduce direct connections
   - Each new location should:
     * Have a unique ID
     * Have a meaningful title, brief description, and long description
     * Fit the themes and atmosphere of the locations it connects
   - Together the new locations should serve the same narrative purpose as the input location

3. REDESIGN CONNECTIONS:
   - Create a new connection map that:
     * Distributes all the input connections to one of the two new locations
     * Maintains the logical flow and narrative sense of movement between locations
     
Your solution should improve the specific overcrowded location while maintaining 
the narrative coherence and accessibility of the original design.
"""


async def improve_single_location(
    story_components: StoryWorldComponents, 
    location_id: str,
) -> LocationImprovementPlan:
    """
    Improve a single location in the world design by ensuring it has no more than 4 connections.
    
    Args:
        story_components: A StoryWorldComponents object containing locations and their connections
        location_id: The ID of the location to improve
        
    Returns:
        A LocationImprovementPlan object containing new locations and updated connections
    """
    improver_agent = Agent(
        model=location_model_instance,
        result_type=LocationImprovementPlan,
        system_prompt=single_location_improver_prompt,
        retries=3,
        model_settings={"temperature": 0.2},
    )
    
    # Get the connections for this location
    location_connections = story_components.location_connections.get(location_id, [])
    connection_count = len(location_connections)
    
    # If the location doesn't have too many connections, return an empty improvement plan
    if connection_count <= 4:
        return LocationImprovementPlan(
            new_locations=[],
            updated_connections={}
        )
    
    # Find the location details
    location_details = find_location_by_id(story_components, location_id)
    
    if not location_details:
        raise ValueError(f"Location with ID {location_id} not found in world components")
    
    # Count all connections to provide context
    all_connection_counts = {
        loc_id: len(connections) 
        for loc_id, connections in story_components.location_connections.items()
        if len(connections) > 0
    }
    
    # Build a prompt focused on this specific location
    user_prompt = f"""\
I need to improve a specific location in a world design that has too many connections (more than 4).

The location to improve is:
ID: {location_id}
Title: {location_details.title}
Brief Description: {location_details.brief_description}
Connections: {", ".join(location_connections)}

Current connection counts for all locations with more than 1 connection:
{all_connection_counts}

Here are the details of the connected locations:
"""

    # Include details of all connected locations
    for loc in story_components.locations:
        if loc.id in location_connections:
            user_prompt += f"ID: {loc.id}\nTitle: {loc.title}\nBrief: {loc.brief_description}\n"
    
    
    result = await improver_agent.run(user_prompt)
    plan = result.data
    return plan


def remove_old_location_and_connections(
    components: StoryWorldComponents,
    location_id: str
) -> list[str]:
    """
    Remove a location and all its connections from the world components.
    
    Args:
        components: StoryWorldComponents to modify in place
        location_id: ID of the location to remove
        
    Returns:
        List of IDs that connected to the removed location
    """
    # Delete the old location
    components.locations = [loc for loc in components.locations if loc.id != location_id]
    
    # Delete all connections from the old location
    if location_id in components.location_connections:
        del components.location_connections[location_id]
    
    # Remove connections to the old location and track which locations had them
    locations_connecting_to_old = []
    for loc_id, connections in list(components.location_connections.items()):
        if location_id in connections:
            components.location_connections[loc_id].remove(location_id)
            locations_connecting_to_old.append(loc_id)
            
    return locations_connecting_to_old


def handle_missing_connections(
    new_locations: list[LocationDescription],
    updated_connections: dict[str, list[str]],
    original_connections: list[str]
) -> dict[str, list[str]]:
    """
    Handle connections that might be missing from the plan.
    
    Args:
        new_locations: List of new LocationDescription objects
        updated_connections: Dictionary mapping source IDs to lists of destination IDs
        original_connections: List of original connections from the old location
        
    Returns:
        Updated connections dictionary with missing connections assigned
    """
    # Make a copy to avoid modifying the original
    updated_connections = deepcopy(updated_connections)
    
    # Track all connections to ensure all original ones are accounted for
    planned_connections = set()
    new_location_ids = [loc.id for loc in new_locations]
    
    # Check all planned outgoing connections from the new locations
    for source_id in new_location_ids:
        if source_id in updated_connections:
            for dest_id in updated_connections[source_id]:
                planned_connections.add(dest_id)
    
    # Check all planned incoming connections to the new locations
    for source_id, destinations in updated_connections.items():
        if source_id not in new_location_ids:
            for dest_id in destinations:
                if dest_id in new_location_ids:
                    planned_connections.add(source_id)
    
    # Check if all original connections are accounted for in the plan
    missing_connections = []
    for conn in original_connections:
        if conn not in planned_connections:
            missing_connections.append(conn)
    
    # If there are missing connections, randomly assign them to one of the new locations
    if missing_connections:
        print(f"Warning: Plan is missing {len(missing_connections)} connections: {missing_connections}")
        print("Randomly assigning missing connections to the new locations")
        
        # Ensure both new locations have connection entries
        for loc_id in new_location_ids:
            if loc_id not in updated_connections:
                updated_connections[loc_id] = []
        
        # Assign each missing connection to a random new location
        for conn in missing_connections:
            # Pick one of the new locations randomly
            random_loc = random.choice(new_location_ids)
            if random_loc not in updated_connections:
                updated_connections[random_loc] = []
            
            if conn not in updated_connections[random_loc]:
                updated_connections[random_loc].append(conn)
                print(f"  - Assigned missing connection {conn} to {random_loc}")
    
    return updated_connections


def add_new_locations_and_connections(
    components: StoryWorldComponents,
    new_locations: list[LocationDescription],
    updated_connections: dict[str, list[str]],
    locations_connecting_to_old: list[str]
) -> None:
    """
    Add new locations and their connections to the world components.
    
    Args:
        components: StoryWorldComponents to modify in place
        new_locations: List of new LocationDescription objects to add
        updated_connections: Dictionary mapping source IDs to lists of destination IDs
        locations_connecting_to_old: List of location IDs that connected to the removed location
    """
    # Check for unique location IDs before adding new locations
    existing_ids = {loc.id for loc in components.locations}
    for new_location in new_locations:
        if new_location.id in existing_ids:
            print(f"Warning: New location ID '{new_location.id}' already exists in the world!")
            
        # Add the new location
        components.locations.append(deepcopy(new_location))
        existing_ids.add(new_location.id)
    
    # Add the new connections from the plan
    for source_id, destinations in updated_connections.items():
        if source_id not in components.location_connections:
            components.location_connections[source_id] = []
        
        # Set the outgoing connections
        components.location_connections[source_id] = destinations.copy()
    
    # Make sure the new locations are connected to each other
    new_location_ids = [loc.id for loc in new_locations]
    if len(new_location_ids) == 2:  # If we have exactly two new locations
        # Add bidirectional connection between them
        ensure_bidirectional_connections(components, new_location_ids[0], new_location_ids[1])
    
    # Reconnect locations that previously connected to the old location
    for loc_id in locations_connecting_to_old:
        # Check if this location is already connected to any new location in the plan
        connected_to_new_loc_id = None
        
        # Check both directions of planned connections
        for new_loc_id in new_location_ids:
            if (new_loc_id in updated_connections and loc_id in updated_connections[new_loc_id]) or \
               (loc_id in updated_connections and new_loc_id in updated_connections[loc_id]):
                connected_to_new_loc_id = new_loc_id
                break
        
        # If not already connected in the plan, connect to a random new location
        if not connected_to_new_loc_id:
            # Pick one of the new locations randomly
            connected_to_new_loc_id = random.choice(new_location_ids)
            print(f"  - Reconnected {loc_id} to new location {connected_to_new_loc_id}")
        
        # Create bidirectional connection - but only to ONE of the new locations
        ensure_bidirectional_connections(components, connected_to_new_loc_id, loc_id)
    
    # Make sure every connection is bidirectional
    for source_id, destinations in list(components.location_connections.items()):
        for dest_id in destinations:
            ensure_bidirectional_connections(components, source_id, dest_id)


async def improve_single_location_and_apply(
    story_components: StoryWorldComponents,
    location_id: str,
    starting_location_id: str | None = None,
) -> tuple[StoryWorldComponents, str | None]:
    """
    Improve a single location and apply the changes immediately.
    
    Args:
        story_components: The current state of the world
        location_id: The ID of the location to improve
        starting_location_id: The current starting location ID
        
    Returns:
        Tuple of (Updated StoryWorldComponents with the improvements applied, potentially updated starting location ID)
    """
    # Get the improvement plan for this location
    location_plan = await improve_single_location(story_components, location_id)
    
    # If no improvements were suggested, return the original components
    if not location_plan.new_locations and not location_plan.updated_connections:
        print(f"No improvements could be made for location {location_id}")
        return story_components, starting_location_id
    
    # Check if plan includes exactly two new locations
    if len(location_plan.new_locations) != 2:
        print(f"Error: Expected exactly 2 new locations in the improvement plan for {location_id}, but got {len(location_plan.new_locations)}. Skipping improvement.")
        return story_components, starting_location_id
    
    # Create a copy to modify
    improved_components = deepcopy(story_components)
    
    # Check if we're splitting the starting location
    updated_starting_id = starting_location_id
    if starting_location_id == location_id:
        # Use the first new location as the starting location
        updated_starting_id = location_plan.new_locations[0].id
        print(f"Starting location {location_id} is being split. New starting location: {updated_starting_id}")
    
    # Remove old location and get list of locations that connected to it
    locations_connecting_to_old = remove_old_location_and_connections(
        improved_components, location_id
    )
    
    # Handle missing connections in the plan
    original_connections = story_components.location_connections.get(location_id, [])
    updated_connections = handle_missing_connections(
        location_plan.new_locations, 
        location_plan.updated_connections, 
        original_connections
    )
    
    # Add new locations with updated connections
    add_new_locations_and_connections(
        improved_components, 
        location_plan.new_locations, 
        updated_connections, 
        locations_connecting_to_old
    )
    
    return improved_components, updated_starting_id

async def improve_world_design(world_design: WorldDesign) -> None:
    """
    Improve a world design by ensuring no location has too many connections.
    This function processes locations one-by-one and applies improvements incrementally,
    modifying the provided WorldDesign object in place.
    
    Args:
        world_design: A WorldDesign object to improve
    """
    # Convert LocationDescriptionWithExits to regular LocationDescription and build components
    story_components = StoryWorldComponents(
        locations=[
            LocationDescription(
                id=loc.id,
                title=loc.title,
                brief_description=loc.brief_description,
                long_description=loc.long_description
            ) for loc in world_design.locations
        ],
        location_connections={
            loc.id: [exit.destination_id for exit in loc.exits]
            for loc in world_design.locations
        },
        characters=world_design.characters,
        character_locations=world_design.character_locations
    )
    
    # Track all new locations created during the improvement process
    all_new_location_ids = set()
    
    # Process locations in iterations until no overcrowded locations remain
    iteration = 1
    max_iterations = 20  # Safety limit
    
    while iteration <= max_iterations:
        # Find all overcrowded locations
        overcrowded_locations = []
        for source_id, dest_ids in story_components.location_connections.items():
            if len(dest_ids) > 4:
                overcrowded_locations.append((source_id, len(dest_ids)))
        
        # If no locations are overcrowded, we're done
        if not overcrowded_locations:
            print("No more overcrowded locations. World improvement complete.")
            break
        
        # Sort locations by number of connections (most crowded first)
        overcrowded_locations.sort(key=lambda x: x[1], reverse=True)
        print(f"\nIteration {iteration}: Found {len(overcrowded_locations)} overcrowded locations")
        
        # Take the most overcrowded location
        location_id, connection_count = overcrowded_locations[0]
        print(f"Improving location {location_id} with {connection_count} connections")
        
        # Capture existing location IDs before improvement
        existing_location_ids = {loc.id for loc in story_components.locations}
        
        # Improve this single location and apply changes
        improved_components, updated_starting_id = await improve_single_location_and_apply(
            story_components, 
            location_id,
            world_design.starting_location_id
        )
        
        # Update starting location if needed
        if updated_starting_id != world_design.starting_location_id:
            print(f"Updating starting location from {world_design.starting_location_id} to {updated_starting_id}")
            world_design.starting_location_id = updated_starting_id
        
        # Find new locations added in this iteration
        new_ids_this_iteration = {loc.id for loc in improved_components.locations} - existing_location_ids
        all_new_location_ids.update(new_ids_this_iteration)
        
        # Check if any improvements were made
        if len(improved_components.locations) > len(story_components.locations):
            # New locations were added
            new_location_count = len(improved_components.locations) - len(story_components.locations)
            print(f"Added {new_location_count} new intermediate locations: {', '.join(new_ids_this_iteration)}")
            
            # Get connection counts for old and new rooms
            old_room_connection_count = len(story_components.location_connections.get(location_id, []))
            old_room_name = next((loc.title for loc in story_components.locations if loc.id == location_id), "Unknown")
            
            # Print old room and its connection count
            print(f"\nSplit room: {location_id} ({old_room_name}) - {old_room_connection_count} connections")
            print("Into new rooms:")
            
            # Print new rooms and their connection counts
            for new_id in new_ids_this_iteration:
                new_room_connections = len(improved_components.location_connections.get(new_id, []))
                new_room_name = next((loc.title for loc in improved_components.locations if loc.id == new_id), "Unknown")
                print(f"  {new_id} ({new_room_name}) - {new_room_connections} connections")
        
        # Update our working copy
        story_components = improved_components
        
        # Get connection summary with the new locations highlighted
        summary = get_connection_summary(story_components, new_ids_this_iteration)
        
        print("\nCurrent connection counts:")
        for loc in summary["location_details"]:
            if loc["is_new"]:
                print(f"  {loc['id']} ({loc['name']}): {loc['connections']} connections [NEW]")
            else:
                print(f"  {loc['id']} ({loc['name']}): {loc['connections']} connections")
        
        # Display summary statistics
        print(f"\nTotal rooms: {summary['total_rooms']}")
        print(f"Total connections: {summary['total_connections']}")
        
        # Display overcrowded locations separately
        if summary["overcrowded"]:
            print(f"Locations still overcrowded: {len(summary['overcrowded'])}")
        
        iteration += 1
    
    if iteration > max_iterations:
        print("Reached maximum iteration count. Some locations may still be overcrowded.")
    
    # Print final summary
    final_summary = get_connection_summary(story_components)
    print(f"\nFinal world state:")
    print(f"Total rooms: {final_summary['total_rooms']}")
    print(f"Total connections: {final_summary['total_connections']}")
    
    # Update the original WorldDesign with the improved components
    # First, clear existing locations
    world_design.locations.clear()
    
    # Create LocationDescriptionWithExits objects from the improved components
    for loc in story_components.locations:
        # Get the connections for this location
        connections = story_components.location_connections.get(loc.id, [])
        
        # Create exit objects
        exits = []
        for dest_id in connections:
            # Find the destination location to get its title
            dest_loc = next((l for l in story_components.locations if l.id == dest_id), None)
            if dest_loc:
                exit_name = dest_loc.title.lower()
                exit_desc = f"There is a path to {dest_loc.title}"
                
                exits.append(LocationExit(
                    destination_id=dest_id,
                    exit_name=exit_name,
                    exit_description=exit_desc
                ))
        
        # Create the location with exits
        world_design.locations.append(LocationDescriptionWithExits(
            id=loc.id,
            title=loc.title,
            brief_description=loc.brief_description,
            long_description=loc.long_description,
            exits=exits
        ))


