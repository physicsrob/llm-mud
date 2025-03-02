from devtools import debug
import json
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from copy import deepcopy

from mad.config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY
from mad.gen.data_model import StoryWorldComponents, RoomImprovementPlan, RoomDescription


# The prompt that guides world improvement for a single room
single_room_improver_prompt = """
You are a master world builder with expertise in game level design and world architecture.

Your task is to analyze a specific location in a game world and improve its design by ensuring it doesn't have too many 
connections (no more than 4 connections per location). When a location has more than 4 connections,
you'll create new intermediate locations to better distribute these connections.

Given a specific overcrowded location, you will:

1. ANALYZE THE OVERCROWDED LOCATION:
   - Examine the location that has more than 4 connections to other locations
   - Determine which connections should be redistributed
   - Consider the theme and narrative purpose of these connections

2. CREATE NEW INTERMEDIATE LOCATIONS:
   - Design new locations that can serve as intermediaries to reduce direct connections
   - Each new location should:
     * Have a unique ID (using the format "intermediate_[descriptive_name]_[number]")
     * Have a meaningful title, brief description, and long description
     * Make narrative sense as a connection point between locations
     * Fit the themes and atmosphere of the locations it connects

3. REDESIGN CONNECTIONS:
   - Create a new connection map that:
     * Moves some connections from the overcrowded location to the new intermediate locations
     * Ensures the world remains fully connected (can reach any location from any other)
     * Maintains the logical flow and narrative sense of movement between locations
     * Updates only the necessary connections, leaving others unchanged

Your solution should improve the specific overcrowded location while maintaining 
the narrative coherence and accessibility of the original design.
"""


async def improve_single_room(
    story_components: StoryWorldComponents, 
    room_id: str,
    model: OpenAIModel = None
) -> RoomImprovementPlan:
    """
    Improve a single room in the world design by ensuring it has no more than 4 connections.
    
    Args:
        story_components: A StoryWorldComponents object containing locations and their connections
        room_id: The ID of the room to improve
        model: Optional OpenAI model to use, will create one if not provided
        
    Returns:
        A RoomImprovementPlan object containing new locations and updated connections
    """
    # Initialize the agent for room improvement if not provided
    if model is None:
        model = OpenAIModel(
            creative_model,
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
    
    improver_agent = Agent(
        model=model,
        result_type=RoomImprovementPlan,
        system_prompt=single_room_improver_prompt,
        retries=3,
        model_settings={"temperature": 0.2},
    )
    
    # Get the connections for this room
    room_connections = story_components.location_connections.get(room_id, [])
    connection_count = len(room_connections)
    
    # If the room doesn't have too many connections, return an empty improvement plan
    if connection_count <= 4:
        return RoomImprovementPlan(
            new_locations=[],
            updated_connections={}
        )
    
    # Find the room details
    room_details = None
    for location in story_components.locations:
        if location.id == room_id:
            room_details = location
            break
    
    if not room_details:
        raise ValueError(f"Room with ID {room_id} not found in world components")
    
    # Count all connections to provide context
    all_connection_counts = {
        loc_id: len(connections) 
        for loc_id, connections in story_components.location_connections.items()
        if len(connections) > 0
    }
    
    # Build a prompt focused on this specific room
    user_prompt = f"""\
I need to improve a specific location in a world design that has too many connections (more than 4).

The location to improve is:
ID: {room_id}
Title: {room_details.title}
Brief Description: {room_details.brief_description}
Long Description: {room_details.long_description}

This location currently has {connection_count} connections to other locations:
{", ".join(room_connections)}

Here are the details of the connected locations:"""

    # Include details of all connected locations
    for loc in story_components.locations:
        if loc.id in room_connections:
            user_prompt += f"\n\nID: {loc.id}\nTitle: {loc.title}\nBrief: {loc.brief_description}"
            # Add number of connections to provide context
            loc_connections = story_components.location_connections.get(loc.id, [])
            user_prompt += f"\nConnections count: {len(loc_connections)}"
    
    user_prompt += f"""

Current connections map (partial, showing only relevant connections):
{json.dumps({room_id: room_connections}, indent=4)}

Please create a plan to improve this location by adding intermediate locations
and redistributing connections so it has no more than 4 connections.
Your plan should:
1. Only create connections FROM the new intermediate locations TO other locations
2. Create logical intermediate locations that make narrative sense
3. Consider the existing connections of other rooms when redistributing
4. DO NOT worry about making bidirectional connections; the system will handle that automatically

Focus on making the minimal necessary changes to fix this overcrowded room.
"""
    
    result = await improver_agent.run(user_prompt)
    return result.data


async def improve_single_room_and_apply(
    story_components: StoryWorldComponents,
    room_id: str,
    model: OpenAIModel = None
) -> StoryWorldComponents:
    """
    Improve a single room and apply the changes immediately.
    
    Args:
        story_components: The current state of the world
        room_id: The ID of the room to improve
        model: Optional OpenAI model to use
        
    Returns:
        Updated StoryWorldComponents with the improvements applied
    """
    # Get the improvement plan for this room
    room_plan = await improve_single_room(story_components, room_id, model)
    
    # If no improvements were suggested, return the original components
    if not room_plan.new_locations and not room_plan.updated_connections:
        print(f"No improvements could be made for room {room_id}")
        return story_components
    
    # Create a copy to modify
    improved_components = deepcopy(story_components)
    
    # Add the new intermediate locations
    for new_location in room_plan.new_locations:
        improved_components.locations.append(deepcopy(new_location))
    
    # Remove all connections to/from the overcrowded room
    if room_id in improved_components.location_connections:
        # Save the original connections for reference
        original_destinations = improved_components.location_connections[room_id]
        improved_components.location_connections[room_id] = []
        
        # Remove incoming connections
        for loc_id, connections in improved_components.location_connections.items():
            if room_id in connections:
                connections.remove(room_id)
    
    # Print starting room and its connections
    print(f"\nStarting Room: {room_id}")
    start_room_details = next((loc for loc in story_components.locations if loc.id == room_id), None)
    if start_room_details:
        print(f"Title: {start_room_details.title}")
        print(f"Original connections: {story_components.location_connections.get(room_id, [])}")
    
    # Apply all new connections with bidirectional handling
    for source_id, destinations in room_plan.updated_connections.items():
        # Set the outgoing connections
        improved_components.location_connections[source_id] = destinations.copy()
        
        # Set all incoming connections
        for dest_id in destinations:
            if dest_id not in improved_components.location_connections:
                improved_components.location_connections[dest_id] = []
            
            # Add bidirectional connection
            if source_id not in improved_components.location_connections[dest_id]:
                improved_components.location_connections[dest_id].append(source_id)
    
    # Print improved room connections
    print(f"Improved Room: {room_id}")
    print(f"Improved connections: {improved_components.location_connections.get(room_id, [])}")
    
    # Print any new intermediate rooms and their connections
    for new_location in room_plan.new_locations:
        print(f"New Room: {new_location.id}")
        print(f"Title: {new_location.title}")
        print(f"Connections: {improved_components.location_connections.get(new_location.id, [])}")
    
    return improved_components

async def improve_world_design(story_components: StoryWorldComponents) -> StoryWorldComponents:
    """
    Improve a world design by ensuring no location has too many connections.
    This function processes rooms one-by-one and applies improvements incrementally.
    
    Args:
        story_components: A StoryWorldComponents object containing locations and their connections
        
    Returns:
        An improved StoryWorldComponents object with balanced connections
    """
    # Create a shared model instance for efficiency
    model = OpenAIModel(
        creative_model,
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    
    # Create working copy of the world components
    working_components = deepcopy(story_components)
    
    # Process rooms in iterations until no overcrowded rooms remain
    iteration = 1
    max_iterations = 20  # Safety limit
    
    while iteration <= max_iterations:
        # Find all overcrowded locations
        overcrowded_rooms = []
        for source_id, dest_ids in working_components.location_connections.items():
            if len(dest_ids) > 4:
                overcrowded_rooms.append((source_id, len(dest_ids)))
        
        # If no rooms are overcrowded, we're done
        if not overcrowded_rooms:
            print("No more overcrowded rooms. World improvement complete.")
            break
        
        # Sort rooms by number of connections (most crowded first)
        overcrowded_rooms.sort(key=lambda x: x[1], reverse=True)
        print(f"\nIteration {iteration}: Found {len(overcrowded_rooms)} overcrowded rooms")
        
        # Take the most overcrowded room
        room_id, connection_count = overcrowded_rooms[0]
        print(f"Improving room {room_id} with {connection_count} connections")
        
        # Improve this single room and apply changes
        improved_components = await improve_single_room_and_apply(
            working_components, 
            room_id,
            model
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
            if len(connections) > 4  # Only show overcrowded rooms
        }
        
        if current_connection_counts:
            print(f"Rooms still overcrowded: {current_connection_counts}")
        
        iteration += 1
    
    if iteration > max_iterations:
        print("Reached maximum iteration count. Some rooms may still be overcrowded.")
    
    return working_components


