from devtools import debug
import json
import random
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from copy import deepcopy

from mad.config import location_model_instance 
from mad.gen.data_model import (
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


# Models for the three specialized agents
class _LocationProposal(BaseModel):
    """Proposal for 2-5 locations to replace an overcrowded location."""
    new_locations: list[LocationDescription] = Field(
        description="2-5 replacement locations that serve the narrative purpose of the original",
        min_items=2,
        max_items=5
    )

class _NewLocationConnections(BaseModel):
    """Connections between newly created locations."""
    internal_connections: dict[str, list[str]] = Field(
        description="Connections between the new locations. Maps location ID to list of connected location IDs."
    )

class _ConnectionDistribution(BaseModel):
    """Assignment of original connections to new locations."""
    connection_assignments: dict[str, str] = Field(
        description="Maps original connection IDs to new location IDs. Each original connection is assigned to exactly one new location."
    )

# Prompts for the three specialized agents
location_proposer_prompt = """
You are a master narrative world builder with expertise in game level design.

Your task is to analyze an overcrowded location in a game world and propose 2-5 new locations to replace it, focusing on narrative coherence and purpose.

Given a specific overcrowded location, you will:
1. Analyze its narrative purpose, connections, and context
2. Create 2-5 new locations that collectively serve the same purpose
3. Ensure each location has a distinct identity but fits within the overall theme
4. Consider how these locations could logically connect (though you won't define connections)

Produce locations that are interesting, varied, and serve the narrative needs.
"""

connection_manager_prompt = """
You are a master game level designer with expertise in spatial layout and navigation flows.

Your task is to create meaningful connections between a set of newly created locations that collectively replace an overcrowded location.

Given a set of new locations, you will:
1. Analyze each location's purpose and theme
2. Create a sensible connection graph between ONLY these new locations
3. Ensure no dead ends or isolated locations
4. Design a navigation flow that feels natural and intuitive

Focus ONLY on connections between the new locations, not to external locations.
"""

connection_distributor_prompt = """
You are a master game level designer with expertise in connectivity and navigation.

Your task is to assign external connections to newly created locations, ensuring logical flow and narrative sense.

Given a set of new locations and original connections, you will:
1. Analyze each original connection and new location
2. Assign each original connection to exactly ONE of the new locations
3. Ensure connections are distributed in a balanced way
4. Maintain logical spatial relationships and thematic coherence

For each original connection, choose the most appropriate new location to connect it to.
"""

async def propose_replacement_locations(
    world_design: WorldDesign, 
    location_id: str
) -> _LocationProposal:
    """
    Create 2-5 new locations to replace an overcrowded location.
    
    Args:
        world_design: A WorldDesign object containing locations and their exits
        location_id: The ID of the location to improve
        
    Returns:
        A _LocationProposal object containing 2-5 new locations
    """
    location_proposer_agent = Agent(
        model=location_model_instance,
        result_type=_LocationProposal,
        system_prompt=location_proposer_prompt,
        retries=3,
        model_settings={"temperature": 0.2},
    )
    
    # Get the location
    location = world_design.find_location_by_id(location_id)
    if not location:
        raise ValueError(f"Location with ID {location_id} not found in world design")
    
    # Get connections for this location
    connection_count = len(location.exits)
    
    # If the location doesn't have too many connections, return an empty proposal
    if connection_count <= 4:
        return _LocationProposal(new_locations=[])
    
    # Get all room names for context
    all_room_names = [loc.title for loc in world_design.locations]
    
    # Build a prompt focused on this specific location
    user_prompt = f"""\
I need to analyze an overcrowded location (more than 4 connections) and propose 2-5 new locations to replace it.

The overcrowded location is:
ID: {location_id}
Title: {location.title}
Brief Description: {location.brief_description}
Long Description: {location.long_description}
Connection Count: {connection_count}

Here are the details of the connected locations:
"""

    # Include details of all connected locations
    for exit in location.exits:
        connected_loc = world_design.find_location_by_id(exit.destination_id)
        if connected_loc:
            user_prompt += f"ID: {connected_loc.id}\nTitle: {connected_loc.title}\nBrief: {connected_loc.brief_description}\n\n"
    
    # Add context about all room names in the world
    user_prompt += f"\nAll location names in the world for context:\n{', '.join(all_room_names)}\n\n"
    user_prompt += "Please create 2-5 replacement locations that collectively fulfill the same purpose as the original location."
    
    result = await location_proposer_agent.run(user_prompt)
    return result.data

async def propose_replacement_location_interconnections(
    world_design: WorldDesign,
    new_locations: list[LocationDescription],
    original_location_id: str
) -> _NewLocationConnections:
    """
    Create connections between newly created locations.
    
    Args:
        world_design: A WorldDesign object containing locations and their exits
        new_locations: List of new locations to connect
        original_location_id: The ID of the original location being replaced
        
    Returns:
        A _NewLocationConnections object with internal connection mapping
    """
    # If there are only 2 locations, we connect them automatically
    if len(new_locations) == 2:
        internal_connections = {
            new_locations[0].id: [new_locations[1].id],
            new_locations[1].id: [new_locations[0].id]
        }
        return _NewLocationConnections(internal_connections=internal_connections)
    
    # For 3+ locations, use the agent to create a more complex connection graph
    connection_manager_agent = Agent(
        model=location_model_instance,
        result_type=_NewLocationConnections,
        system_prompt=connection_manager_prompt,
        retries=3,
        model_settings={"temperature": 0.2},
    )
    
    # Build a prompt for connecting the new locations
    user_prompt = f"""\
I need to create meaningful connections between a set of newly created locations that will replace a location with ID: {original_location_id}

Here are the new locations that need to be interconnected:

"""
    # Add details about each new location
    for i, loc in enumerate(new_locations):
        user_prompt += f"Location {i+1}:\nID: {loc.id}\nTitle: {loc.title}\nBrief Description: {loc.brief_description}\n\n"
    
    user_prompt += """
Please create a connection graph between ONLY these new locations. Each location should connect to at least one other location, and there should be no isolated locations. The connections should feel natural and intuitive based on the locations' themes and purposes.
"""

    result = await connection_manager_agent.run(user_prompt)
    
    # Validate that all locations have at least one connection
    connections = result.data.internal_connections
    location_ids = [loc.id for loc in new_locations]
    
    # Ensure all locations are in the connections dictionary
    for loc_id in location_ids:
        if loc_id not in connections:
            connections[loc_id] = []
    
    # Check if any location has no connections
    disconnected = [loc_id for loc_id in location_ids if not connections.get(loc_id, [])]
    
    # If there are disconnected locations, connect them to a random other location
    if disconnected:
        for loc_id in disconnected:
            # Find a random location to connect to
            other_locations = [other_id for other_id in location_ids if other_id != loc_id]
            if other_locations:
                random_loc_id = random.choice(other_locations)
                
                # Add bidirectional connection
                if loc_id not in connections:
                    connections[loc_id] = []
                if random_loc_id not in connections:
                    connections[random_loc_id] = []
                
                connections[loc_id].append(random_loc_id)
                connections[random_loc_id].append(loc_id)
    
    return _NewLocationConnections(internal_connections=connections)

async def redistribute_connections(
    world_design: WorldDesign,
    new_locations: list[LocationDescription],
    original_location_id: str
) -> _ConnectionDistribution:
    """
    Assign each original connection to one of the new locations.
    
    Args:
        world_design: A WorldDesign object containing locations and their exits
        new_locations: List of new locations to distribute connections to
        original_location_id: The ID of the original location being replaced
        
    Returns:
        A _ConnectionDistribution object mapping original connections to new locations
    """
    connection_distributor_agent = Agent(
        model=location_model_instance,
        result_type=_ConnectionDistribution,
        system_prompt=connection_distributor_prompt,
        retries=3,
        model_settings={"temperature": 0.2},
    )
    
    # Since the original location has been removed, we'll use the locations_connecting_to_old
    # that was returned from world_design.remove_location() and passed to this function
    original_connections = []
    
    # Use the locations that were connecting to the old location
    for loc in world_design.locations:
        original_connections.append({
            "id": loc.id,
            "title": loc.title,
            "brief_description": loc.brief_description
        })
    
    if not original_connections:
        # If no connections, return empty assignment
        return _ConnectionDistribution(connection_assignments={})
    
    # Build a prompt for distributing the connections
    user_prompt = f"""\
I need to assign original connections to newly created locations that replace an overcrowded location.

Original Location ID: {original_location_id} (this location has been removed)

Here are the new locations that will replace the original location:
"""
    # Add details about each new location
    for i, loc in enumerate(new_locations):
        user_prompt += f"New Location {i+1}:\nID: {loc.id}\nTitle: {loc.title}\nBrief Description: {loc.brief_description}\n\n"
    
    user_prompt += "\nHere are the original connections that need to be assigned to the new locations:\n"
    
    # Add details about each original connection
    for i, conn in enumerate(original_connections):
        user_prompt += f"Connection {i+1}:\nID: {conn['id']}\nTitle: {conn['title']}\nBrief Description: {conn['brief_description']}\n\n"
    
    user_prompt += """
Please assign each original connection to exactly ONE of the new locations. The assignments should make logical sense based on the themes and purposes of both the connections and the new locations. Each original connection ID should map to exactly one new location ID.
"""

    result = await connection_distributor_agent.run(user_prompt)
    
    # Validate that all original connections are assigned
    assignments = result.data.connection_assignments
    original_connection_ids = [conn["id"] for conn in original_connections]
    
    # Check if all original connections are assigned
    for conn_id in original_connection_ids:
        if conn_id not in assignments:
            # Assign to random new location if missing
            random_new_loc = random.choice(new_locations)
            assignments[conn_id] = random_new_loc.id
            print(f"Warning: Connection {conn_id} was not assigned. Randomly assigned to {random_new_loc.id}")
    
    # Check if any assignments are to invalid location IDs
    new_location_ids = [loc.id for loc in new_locations]
    for conn_id, loc_id in assignments.items():
        if loc_id not in new_location_ids:
            # Reassign to valid location
            valid_loc_id = random.choice(new_location_ids)
            assignments[conn_id] = valid_loc_id
            print(f"Warning: Connection {conn_id} was assigned to invalid location {loc_id}. Reassigned to {valid_loc_id}")
    
    return _ConnectionDistribution(connection_assignments=assignments)

async def improve_single_location_and_apply(
    world_design: WorldDesign,
    location_id: str
) -> bool:
    """
    Improve a single location and apply the changes directly to the WorldDesign using the three specialized agents.
    
    Args:
        world_design: The WorldDesign to modify in place
        location_id: The ID of the location to improve
        
    Returns:
        Boolean indicating if any improvements were made
    """
    # Verify the location exists before starting
    location = world_design.find_location_by_id(location_id)
    if not location:
        return False
        
    # STEP 1: Propose replacement locations
    location_proposal = await propose_replacement_locations(world_design, location_id)
    
    # If no new locations were proposed, return False
    if not location_proposal.new_locations:
        print(f"No improvements could be made for location {location_id}")
        return False
    
    # Check if we're splitting the starting location
    if world_design.starting_location_id == location_id:
        # Use the first new location as the starting location
        world_design.starting_location_id = location_proposal.new_locations[0].id
        print(f"Starting location {location_id} is being split. New starting location: {world_design.starting_location_id}")
    
    # Get list of locations connected to this one BEFORE removing it
    original_connections = []
    for exit in location.exits:
        connected_loc = world_design.find_location_by_id(exit.destination_id)
        if connected_loc:
            original_connections.append({
                "id": connected_loc.id,
                "title": connected_loc.title,
                "brief_description": connected_loc.brief_description
            })
    
    # Remove old location and get list of locations that connected to it
    locations_connecting_to_old = world_design.remove_location(location_id)
    
    # Add the new locations to the world design
    new_location_ids = []
    for new_location in location_proposal.new_locations:
        try:
            world_design.add_location(new_location)
            new_location_ids.append(new_location.id)
        except ValueError as e:
            print(f"Warning: {e}")
    
    # STEP 2: Propose interconnections between the new locations
    new_location_connections = await propose_replacement_location_interconnections(
        world_design,
        location_proposal.new_locations,
        location_id
    )
    
    # Add internal connections between the new locations
    for source_id, destinations in new_location_connections.internal_connections.items():
        source_loc = world_design.find_location_by_id(source_id)
        if not source_loc:
            continue
            
        # Clear existing exits for the new locations
        if source_id in new_location_ids:
            source_loc.exits = []
        
        # Add the internal connections
        for dest_id in destinations:
            if world_design.find_location_by_id(dest_id):
                world_design.ensure_bidirectional_exits(source_id, dest_id)
            
    
    # STEP 3: Connect the new locations to original connections
    
    # If we have original connections, distribute them among the new locations
    if original_connections:
        # Distribute original connections evenly across new locations
        for i, conn in enumerate(original_connections):
            # Pick a new location in a round-robin fashion
            new_loc_id = new_location_ids[i % len(new_location_ids)]
            
            if world_design.find_location_by_id(conn["id"]) and world_design.find_location_by_id(new_loc_id):
                world_design.ensure_bidirectional_exits(conn["id"], new_loc_id)
    
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

