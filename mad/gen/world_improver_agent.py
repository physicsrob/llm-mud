from devtools import debug
import json
from pydantic_ai import Agent
from copy import deepcopy

from mad.config import location_model_instance 
from mad.gen.data_model import StoryWorldComponents, LocationImprovementPlan, LocationDescription


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
    location_details = None
    for location in story_components.locations:
        if location.id == location_id:
            location_details = location
            break
    
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
    
    # Skip printing old location details
    
    # Delete the old location
    improved_components.locations = [loc for loc in improved_components.locations if loc.id != location_id]
    
    # Delete all connections to/from the old location
    if location_id in improved_components.location_connections:
        del improved_components.location_connections[location_id]
    
    # Store locations that had connections to the removed location
    # We'll need to reconnect these to the new locations later
    locations_connecting_to_old = []
    for loc_id, connections in list(improved_components.location_connections.items()):
        if location_id in connections:
            improved_components.location_connections[loc_id].remove(location_id)
            locations_connecting_to_old.append(loc_id)
    
    # Check for unique location IDs before adding new locations
    existing_ids = {loc.id for loc in improved_components.locations}
    for new_location in location_plan.new_locations:
        if new_location.id in existing_ids:
            print(f"Warning: New location ID '{new_location.id}' already exists in the world!")
            
        # Add the new location
        improved_components.locations.append(deepcopy(new_location))
        existing_ids.add(new_location.id)
    
    # Get all the original connections from the location being improved
    original_connections = story_components.location_connections.get(location_id, [])
    
    # Track all connections to ensure all original ones are accounted for
    # We need to check if all original connections are now linked to at least one of the new locations
    planned_connections = set()
    new_location_ids = [loc.id for loc in location_plan.new_locations]
    
    # Check all planned outgoing connections from the new locations
    for source_id in new_location_ids:
        if source_id in location_plan.updated_connections:
            for dest_id in location_plan.updated_connections[source_id]:
                planned_connections.add(dest_id)
    
    # Check all planned incoming connections to the new locations
    for source_id, destinations in location_plan.updated_connections.items():
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
        for loc_id in [loc.id for loc in location_plan.new_locations]:
            if loc_id not in location_plan.updated_connections:
                location_plan.updated_connections[loc_id] = []
        
        # Get the two new location IDs
        new_loc_ids = [loc.id for loc in location_plan.new_locations]
        
        # Assign each missing connection to a random new location
        import random
        for conn in missing_connections:
            # Pick one of the two new locations randomly
            random_loc = random.choice(new_loc_ids)
            if random_loc not in location_plan.updated_connections:
                location_plan.updated_connections[random_loc] = []
            
            if conn not in location_plan.updated_connections[random_loc]:
                location_plan.updated_connections[random_loc].append(conn)
                print(f"  - Assigned missing connection {conn} to {random_loc}")
    
    # Add the new connections from the plan
    for source_id, destinations in location_plan.updated_connections.items():
        if source_id not in improved_components.location_connections:
            improved_components.location_connections[source_id] = []
        
        # Set the outgoing connections
        improved_components.location_connections[source_id] = destinations.copy()
    
    # Make sure the two new locations are connected to each other
    new_location_ids = [loc.id for loc in location_plan.new_locations]
    # Add bidirectional connection between the two new locations if not already present
    if new_location_ids[0] not in improved_components.location_connections:
        improved_components.location_connections[new_location_ids[0]] = []
    if new_location_ids[1] not in improved_components.location_connections[new_location_ids[0]]:
        improved_components.location_connections[new_location_ids[0]].append(new_location_ids[1])
        
    if new_location_ids[1] not in improved_components.location_connections:
        improved_components.location_connections[new_location_ids[1]] = []
    if new_location_ids[0] not in improved_components.location_connections[new_location_ids[1]]:
        improved_components.location_connections[new_location_ids[1]].append(new_location_ids[0])
    
    # Reconnect locations that previously connected to the old location to exactly ONE of the new locations
    # This prevents duplicate connections that would defeat the purpose of splitting locations
    for loc_id in locations_connecting_to_old:
        # First check if this location is already connected to either new location in the plan
        connected_to_new_loc_id = None
        
        # Check if this location already has a planned connection to either new location
        for new_loc_id in new_location_ids:
            if new_loc_id in location_plan.updated_connections and loc_id in location_plan.updated_connections[new_loc_id]:
                connected_to_new_loc_id = new_loc_id
                break
            
            # Also check the reverse direction
            if loc_id in location_plan.updated_connections and new_loc_id in location_plan.updated_connections[loc_id]:
                connected_to_new_loc_id = new_loc_id
                break
        
        # If not already connected in the plan, connect to a random new location
        if not connected_to_new_loc_id:
            import random
            # Pick one of the two new locations randomly
            connected_to_new_loc_id = random.choice(new_location_ids)
            print(f"  - Reconnected {loc_id} to new location {connected_to_new_loc_id}")
        
        # Create bidirectional connection - but only to ONE of the new locations
        if loc_id not in improved_components.location_connections[connected_to_new_loc_id]:
            improved_components.location_connections[connected_to_new_loc_id].append(loc_id)
        
        if connected_to_new_loc_id not in improved_components.location_connections[loc_id]:
            improved_components.location_connections[loc_id].append(connected_to_new_loc_id)

    # Make sure that every connection in the map is bidirectional
    for source_id, destinations in list(improved_components.location_connections.items()):
        for dest_id in destinations:
            if dest_id not in improved_components.location_connections:
                improved_components.location_connections[dest_id] = []
            
            if source_id not in improved_components.location_connections[dest_id]:
                improved_components.location_connections[dest_id].append(source_id)
    
    # Skip printing details of new locations
    
    return improved_components, updated_starting_id

async def improve_world_design(
    story_components: StoryWorldComponents, 
    starting_location_id: str | None = None
) -> tuple[StoryWorldComponents, str | None]:
    """
    Improve a world design by ensuring no location has too many connections.
    This function processes locations one-by-one and applies improvements incrementally.
    
    Args:
        story_components: A StoryWorldComponents object containing locations and their connections
        starting_location_id: The current starting location ID
        
    Returns:
        Tuple of (Improved StoryWorldComponents object with balanced connections, potentially updated starting location ID)
    """
    # Create working copy of the world components
    working_components = deepcopy(story_components)
    updated_starting_id = starting_location_id
    
    # Track all new locations created during the improvement process
    all_new_location_ids = set()
    
    # Process locations in iterations until no overcrowded locations remain
    iteration = 1
    max_iterations = 20  # Safety limit
    
    while iteration <= max_iterations:
        # Find all overcrowded locations
        overcrowded_locations = []
        for source_id, dest_ids in working_components.location_connections.items():
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
        existing_location_ids = {loc.id for loc in working_components.locations}
        
        # Improve this single location and apply changes
        improved_components, updated_starting_id = await improve_single_location_and_apply(
            working_components, 
            location_id,
            updated_starting_id
        )
        
        # Find new locations added in this iteration
        new_ids_this_iteration = {loc.id for loc in improved_components.locations} - existing_location_ids
        all_new_location_ids.update(new_ids_this_iteration)
        
        # Check if any improvements were made
        if len(improved_components.locations) > len(working_components.locations):
            # New locations were added
            new_location_count = len(improved_components.locations) - len(working_components.locations)
            print(f"Added {new_location_count} new intermediate locations: {', '.join(new_ids_this_iteration)}")
            
            # Get connection counts for old and new rooms
            old_room_connection_count = len(working_components.location_connections.get(location_id, []))
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
        working_components = improved_components
        
        # Show all locations sorted by id
        all_connection_counts = {
            loc_id: len(connections) 
            for loc_id, connections in working_components.location_connections.items()
        }
        
        # Get all location IDs
        all_location_ids = set(all_connection_counts.keys())
        
        # Use the tracked new location IDs for highlighting
        
        # Calculate total connections and rooms
        total_rooms = len(working_components.locations)
        total_connections = sum(len(connections) for connections in working_components.location_connections.values()) // 2  # Divide by 2 since connections are bidirectional
        
        # Sort locations by ID
        sorted_locations = sorted(all_connection_counts.items(), key=lambda x: x[0])
        
        print("\nCurrent connection counts:")
        for loc_id, count in sorted_locations:
            loc_name = next((loc.title for loc in working_components.locations if loc.id == loc_id), "Unknown")
            if loc_id in new_ids_this_iteration:  # Only mark locations from current iteration
                print(f"  {loc_id} ({loc_name}): {count} connections [NEW]")
            else:
                print(f"  {loc_id} ({loc_name}): {count} connections")
        
        # Display summary statistics
        print(f"\nTotal rooms: {total_rooms}")
        print(f"Total connections: {total_connections}")
        
        # Display overcrowded locations separately
        overcrowded = {k: v for k, v in all_connection_counts.items() if v > 4}
        if overcrowded:
            print(f"Locations still overcrowded: {len(overcrowded)}")
        
        iteration += 1
    
    if iteration > max_iterations:
        print("Reached maximum iteration count. Some locations may still be overcrowded.")
    
    # Print final summary
    total_rooms = len(working_components.locations)
    total_connections = sum(len(connections) for connections in working_components.location_connections.values()) // 2
    print(f"\nFinal world state:")
    print(f"Total rooms: {total_rooms}")
    print(f"Total connections: {total_connections}")
    
    return working_components, updated_starting_id


