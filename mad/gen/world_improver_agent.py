from devtools import debug
import json
import random
from pydantic_ai import Agent
from copy import deepcopy

from mad.config import location_model_instance 
from mad.gen.data_model import (
    LocationImprovementPlan, 
    LocationDescription, 
    WorldDesign,
    LocationDescriptionWithExits,
    LocationExit
)

def get_connection_summary(world_design: WorldDesign, new_ids: set[str] = None) -> dict:
    """
    Generates a summary of connections for all locations in the world design.
    
    Args:
        world_design: The WorldDesign to analyze
        new_ids: Optional set of location IDs to highlight as new
        
    Returns:
        Dictionary with connection counts and statistics
    """
    # Calculate connection counts for all locations
    all_connection_counts = {
        loc.id: len(loc.exits) 
        for loc in world_design.locations
    }
    
    # Find overcrowded locations
    overcrowded = {k: v for k, v in all_connection_counts.items() if v > 4}
    
    # Calculate total rooms and connections
    total_rooms = len(world_design.locations)
    # Divide by 2 since connections are bidirectional
    total_connections = sum(len(loc.exits) for loc in world_design.locations) // 2
    
    # Create a list of locations with their names and connection counts, sorted by ID
    location_details = []
    for loc_id, count in sorted(all_connection_counts.items(), key=lambda x: x[0]):
        loc = world_design.find_location_by_id(loc_id)
        if loc:
            is_new = new_ids and loc_id in new_ids
            location_details.append({
                "id": loc_id,
                "name": loc.title,
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
    world_design: WorldDesign, 
    location_id: str,
) -> LocationImprovementPlan:
    """
    Improve a single location in the world design by ensuring it has no more than 4 connections.
    
    Args:
        world_design: A WorldDesign object containing locations and their exits
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
    
    # Get the location
    location = world_design.find_location_by_id(location_id)
    if not location:
        raise ValueError(f"Location with ID {location_id} not found in world design")
    
    # Get connections for this location
    connection_count = len(location.exits)
    
    # If the location doesn't have too many connections, return an empty improvement plan
    if connection_count <= 4:
        return LocationImprovementPlan(
            new_locations=[],
            updated_connections={}
        )
    
    # Count all connections to provide context
    all_connection_counts = {
        loc.id: len(loc.exits) 
        for loc in world_design.locations
        if len(loc.exits) > 0
    }
    
    # Build a prompt focused on this specific location
    user_prompt = f"""\
I need to improve a specific location in a world design that has too many connections (more than 4).

The location to improve is:
ID: {location_id}
Title: {location.title}
Brief Description: {location.brief_description}
Connections: {", ".join([exit.destination_id for exit in location.exits])}

Current connection counts for all locations with more than 1 connection:
{all_connection_counts}

Here are the details of the connected locations:
"""

    # Include details of all connected locations
    for exit in location.exits:
        connected_loc = world_design.find_location_by_id(exit.destination_id)
        if connected_loc:
            user_prompt += f"ID: {connected_loc.id}\nTitle: {connected_loc.title}\nBrief: {connected_loc.brief_description}\n"
    
    result = await improver_agent.run(user_prompt)
    plan = result.data
    return plan

def handle_missing_connections(
    world_design: WorldDesign,
    new_locations: list[LocationDescription],
    updated_connections: dict[str, list[str]],
    original_location_id: str
) -> None:
    """
    Handle connections that might be missing from the plan by modifying the updated_connections dict in place.
    
    Args:
        world_design: The world design containing the original location
        new_locations: List of new LocationDescription objects
        updated_connections: Dictionary mapping source IDs to lists of destination IDs to modify
        original_location_id: ID of the original location being replaced
    """
    # Get original location's connections
    original_location = world_design.find_location_by_id(original_location_id)
    if not original_location:
        # Location might already be removed, but we'll handle that gracefully
        original_connections = []
    else:
        original_connections = [exit.destination_id for exit in original_location.exits]
    
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


def add_new_locations_and_connections(
    world_design: WorldDesign,
    new_locations: list[LocationDescription],
    updated_connections: dict[str, list[str]],
    locations_connecting_to_old: list[str]
) -> None:
    """
    Add new locations and their connections to the world design.
    
    Args:
        world_design: WorldDesign to modify in place
        new_locations: List of new LocationDescription objects to add
        updated_connections: Dictionary mapping source IDs to lists of destination IDs
        locations_connecting_to_old: List of location IDs that connected to the removed location
    """
    # Add new locations using WorldDesign's add_location method
    new_location_ids = []
    for new_location in new_locations:
        try:
            world_design.add_location(new_location)
            new_location_ids.append(new_location.id)
        except ValueError as e:
            print(f"Warning: {e}")
    
    # Add the new connections from the plan
    for source_id, destinations in updated_connections.items():
        source_loc = world_design.find_location_by_id(source_id)
        if not source_loc:
            # This might be a new location we haven't processed yet
            continue
        
        # Clear existing exits only for new locations that were just added
        if source_id in new_location_ids:
            source_loc.exits = []
        
        # Add planned exits using bidirectional connections
        for dest_id in destinations:
            if world_design.find_location_by_id(dest_id):
                world_design.ensure_bidirectional_exits(source_id, dest_id)
    
    # Make sure the new locations are connected to each other
    if len(new_location_ids) == 2:  # If we have exactly two new locations
        world_design.ensure_bidirectional_exits(new_location_ids[0], new_location_ids[1])
    
    # Reconnect locations that previously connected to the old location
    for loc_id in locations_connecting_to_old:
        loc = world_design.find_location_by_id(loc_id)
        if not loc:
            continue
            
        # Check if this location is already connected to any new location
        already_connected = False
        for exit in loc.exits:
            if exit.destination_id in new_location_ids:
                already_connected = True
                break
        
        # If not already connected, connect to a random new location
        if not already_connected and new_location_ids:  # Make sure there are new locations
            random_new_loc_id = random.choice(new_location_ids)
            world_design.ensure_bidirectional_exits(loc_id, random_new_loc_id)
            print(f"  - Reconnected {loc_id} to new location {random_new_loc_id}")


async def improve_single_location_and_apply(
    world_design: WorldDesign,
    location_id: str
) -> bool:
    """
    Improve a single location and apply the changes directly to the WorldDesign.
    
    Args:
        world_design: The WorldDesign to modify in place
        location_id: The ID of the location to improve
        
    Returns:
        Boolean indicating if any improvements were made
    """
    # Get the improvement plan for this location
    location_plan = await improve_single_location(world_design, location_id)
    
    # If no improvements were suggested, return False
    if not location_plan.new_locations and not location_plan.updated_connections:
        print(f"No improvements could be made for location {location_id}")
        return False
    
    # Check if plan includes exactly two new locations
    if len(location_plan.new_locations) != 2:
        print(f"Error: Expected exactly 2 new locations in the improvement plan for {location_id}, but got {len(location_plan.new_locations)}. Skipping improvement.")
        return False
    
    # Check if we're splitting the starting location
    if world_design.starting_location_id == location_id:
        # Use the first new location as the starting location
        world_design.starting_location_id = location_plan.new_locations[0].id
        print(f"Starting location {location_id} is being split. New starting location: {world_design.starting_location_id}")
    
    # Remove old location and get list of locations that connected to it
    locations_connecting_to_old = world_design.remove_location(location_id)
    
    # Handle missing connections in the plan - this modifies location_plan.updated_connections in place
    handle_missing_connections(
        world_design,
        location_plan.new_locations, 
        location_plan.updated_connections, 
        location_id
    )
    
    # Add new locations with updated connections
    add_new_locations_and_connections(
        world_design,
        location_plan.new_locations, 
        location_plan.updated_connections, 
        locations_connecting_to_old
    )
    
    return True


async def improve_world_design(world_design: WorldDesign) -> None:
    """
    Improve a world design by ensuring no location has too many connections.
    This function processes locations one-by-one and applies improvements incrementally,
    modifying the provided WorldDesign object in place.
    
    Args:
        world_design: A WorldDesign object to improve
    """
    # Track all new locations created during the improvement process
    all_new_location_ids = set()
    
    # Process locations in iterations until no overcrowded locations remain
    iteration = 1
    max_iterations = 20  # Safety limit
    
    while iteration <= max_iterations:
        # Find all overcrowded locations
        overcrowded_locations = []
        for loc in world_design.locations:
            if len(loc.exits) > 4:
                overcrowded_locations.append((loc.id, len(loc.exits)))
        
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
        existing_location_ids = {loc.id for loc in world_design.locations}
        
        # Improve this single location and apply changes
        improvement_made = await improve_single_location_and_apply(world_design, location_id)
        
        if improvement_made:
            # Find new locations added in this iteration
            new_ids_this_iteration = {loc.id for loc in world_design.locations} - existing_location_ids
            all_new_location_ids.update(new_ids_this_iteration)
            
            if new_ids_this_iteration:
                # New locations were added
                new_location_count = len(new_ids_this_iteration)
                print(f"Added {new_location_count} new intermediate locations: {', '.join(new_ids_this_iteration)}")
                
                # Print old room and its connection count
                print(f"\nSplit room: {location_id} - {connection_count} connections")
                print("Into new rooms:")
                
                # Print new rooms and their connection counts
                for new_id in new_ids_this_iteration:
                    new_loc = world_design.find_location_by_id(new_id)
                    if new_loc:
                        print(f"  {new_id} ({new_loc.title}) - {len(new_loc.exits)} connections")
            
            # Get connection summary with the new locations highlighted
            summary = get_connection_summary(world_design, new_ids_this_iteration)
            
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
    final_summary = get_connection_summary(world_design)
    print(f"\nFinal world state:")
    print(f"Total rooms: {final_summary['total_rooms']}")
    print(f"Total connections: {final_summary['total_connections']}")


