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
) -> StoryWorldComponents:
    """
    Improve a single location and apply the changes immediately.
    
    Args:
        story_components: The current state of the world
        location_id: The ID of the location to improve
        
    Returns:
        Updated StoryWorldComponents with the improvements applied
    """
    # Get the improvement plan for this location
    location_plan = await improve_single_location(story_components, location_id)
    
    # If no improvements were suggested, return the original components
    if not location_plan.new_locations and not location_plan.updated_connections:
        print(f"No improvements could be made for location {location_id}")
        return story_components
    
    # Check if plan includes exactly two new locations
    if len(location_plan.new_locations) != 2:
        print(f"Error: Expected exactly 2 new locations in the improvement plan for {location_id}, but got {len(location_plan.new_locations)}. Skipping improvement.")
        return story_components
    
    # Create a copy to modify
    improved_components = deepcopy(story_components)
    
    # Print out the old location/exits
    print(f"\nStarting Location: {location_id}")
    start_location_details = next((loc for loc in story_components.locations if loc.id == location_id), None)
    if start_location_details:
        print(f"Title: {start_location_details.title}")
        print(f"Original connections: {story_components.location_connections.get(location_id, [])}")
    
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
    
    # Reconnect locations that previously connected to the old location
    # Choose the most appropriate new location to connect to based on updated_connections
    for loc_id in locations_connecting_to_old:
        # Find which new location is most appropriate to connect to this location
        connected_to_new = False
        
        # If this location is in the updated connections, use that information
        for new_loc_id in new_location_ids:
            if new_loc_id in location_plan.updated_connections and loc_id in location_plan.updated_connections[new_loc_id]:
                connected_to_new = True
                break
        
        # If not already connected in the plan, connect to a random new location
        if not connected_to_new:
            import random
            # Pick one of the two new locations randomly
            random_loc = random.choice(new_location_ids)
            
            # Create bidirectional connection
            if loc_id not in improved_components.location_connections[random_loc]:
                improved_components.location_connections[random_loc].append(loc_id)
            
            if random_loc not in improved_components.location_connections[loc_id]:
                improved_components.location_connections[loc_id].append(random_loc)
            
            print(f"  - Reconnected {loc_id} to new location {random_loc}")

    # Make sure that every connection in the map is bidirectional
    for source_id, destinations in list(improved_components.location_connections.items()):
        for dest_id in destinations:
            if dest_id not in improved_components.location_connections:
                improved_components.location_connections[dest_id] = []
            
            if source_id not in improved_components.location_connections[dest_id]:
                improved_components.location_connections[dest_id].append(source_id)
    
    # Print out the new two locations, each with their exits
    for new_location in location_plan.new_locations:
        print(f"New Location: {new_location.id}")
        print(f"Title: {new_location.title}")
        print(f"Brief Description: {new_location.brief_description}")
        print(f"Connections: {improved_components.location_connections.get(new_location.id, [])}")
    
    return improved_components

async def improve_world_design(story_components: StoryWorldComponents) -> StoryWorldComponents:
    """
    Improve a world design by ensuring no location has too many connections.
    This function processes locations one-by-one and applies improvements incrementally.
    
    Args:
        story_components: A StoryWorldComponents object containing locations and their connections
        
    Returns:
        An improved StoryWorldComponents object with balanced connections
    """
    # Create working copy of the world components
    working_components = deepcopy(story_components)
    
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
        
        # Improve this single location and apply changes
        improved_components = await improve_single_location_and_apply(
            working_components, 
            location_id,
        )
        
        # Check if any improvements were made
        if len(improved_components.locations) > len(working_components.locations):
            # New locations were added
            new_location_count = len(improved_components.locations) - len(working_components.locations)
            print(f"Added {new_location_count} new intermediate locations")
        
        # Update our working copy
        working_components = improved_components
        
        # Show current state
        current_connection_counts = {
            loc_id: len(connections) 
            for loc_id, connections in working_components.location_connections.items()
            if len(connections) > 4  # Only show overcrowded locations
        }
        
        if current_connection_counts:
            print(f"Locations still overcrowded: {current_connection_counts}")
        
        iteration += 1
    
    if iteration > max_iterations:
        print("Reached maximum iteration count. Some locations may still be overcrowded.")
    
    return working_components


