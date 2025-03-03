from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from mad.config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY
from mad.gen.data_model import LocationDescription, LocationExit

class LocationExits(BaseModel):
    exits: list[LocationExit] = Field(
        description="A list of exits connecting the source location to destination locations",
    )

# Prompt to guide the location exit creation
location_exit_prompt = """
You are a master world builder with expertise in creating immersive, interconnected environments.

Your task is to generate compelling exit descriptions for locations in an interactive fiction world.
Given a location and information about connected locations, you will create natural, descriptive exits.

For each exit, you need to:
1. Create a short but vivid exit description as viewed from the source location
2. Provide a descriptive name for the exit that players will use to navigate
3. Ensure the exit description clearly suggests the nature of the destination

Guidelines:
- Exit descriptions should be one line or less
- Exit names should be intuitive physical objects or features (like "archway", "door", "gate", "pathway", "bridge", "stairs", "tunnel")
- Prefer one word exit names. Two or three words are acceptable for exit names, but they MUST be hyphenated.
- Rarely use cardinal directions (north, south, east, west) as exit names
- The description should hint at what lies beyond without revealing everything
- Match the tone and style of the location descriptions
- Consider the physical and thematic relationship between the connected locations
- IMPORTANT: Each exit_name MUST be unique within a location - no duplicate exit names allowed
- IMPORTANT: No spaces allow in exit names.
"""

async def create_all_location_exits(source_location: LocationDescription, destination_locations: list[tuple[str, LocationDescription]]) -> list[LocationExit]:
    """
    Create LocationExit objects for all connections from source_location to destination_locations in a single LLM call.
    
    Args:
        source_location: The location where the exits are located
        destination_locations: List of tuples with (destination_id, destination_location) for all connected locations
        
    Returns:
        A list of LocationExit objects with destination_id, exit_description, and exit_name
    """
    if not destination_locations:
        return []
    
    model = OpenAIModel(
        creative_model,
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    
    exit_agent = Agent(
        model=model,
        result_type=LocationExits,
        system_prompt=location_exit_prompt,
        retries=3,
        model_settings={"temperature": 0.7},  # Higher temperature for more creative descriptions
    )
    
    # Build destination descriptions for the prompt
    destinations_text = ""
    for i, (dest_id, dest_location) in enumerate(destination_locations, 1):
        destinations_text += f"""
    DESTINATION LOCATION {i}:
    Destination ID: {dest_id}
    Title: {dest_location.title}
    Brief Description: {dest_location.brief_description}
    Long Description: {dest_location.long_description}
    """
    
    user_prompt = f"""
    Please create unique exits that connect the following source location to each destination location:
    
    SOURCE LOCATION:
    Title: {source_location.title}
    Brief Description: {source_location.brief_description}
    Long Description: {source_location.long_description}
    
    {destinations_text}
    
    Create a list of LocationExit objects, one for each destination location. Each exit should contain:
    1. The correct destination_id for the location it connects to
    2. A vivid but concise exit_description visible from the source location
    3. A descriptive exit_name that players will use to navigate (like "archway", "door", "gate", "pathway", etc.)
    
    IMPORTANT:
    - Do NOT use cardinal directions as exit names - use physical objects or features instead
    - Each exit_name MUST be unique and clearly distinguishable from other exits in this location
    - No two exits can have the same or similar names
    """
    
    result = await exit_agent.run(user_prompt)
    return result.data.exits

async def get_location_exits(location: LocationDescription, all_locations: list[LocationDescription], connected_location_ids: list[str]) -> list[LocationExit]:
    """
    Generate exits for a location based on its connections to other locations.
    
    Args:
        location: The location to generate exits for
        all_locations: List of all locations in the world
        connected_location_ids: List of location IDs that are connected to this location
    """
    # Create a mapping of location IDs to location objects for easy lookup
    location_map = {r.id: r for r in all_locations}
    
    # Gather all destination locations
    destination_locations = []
    for connected_id in connected_location_ids:
        if connected_id in location_map:
            destination_locations.append((connected_id, location_map[connected_id]))
    
    # Generate all exits in a single call
    exits = await create_all_location_exits(location, destination_locations)
    
    return exits
