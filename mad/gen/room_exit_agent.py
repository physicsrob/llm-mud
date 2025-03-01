from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from mad.config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY
from mad.gen.data_model import RoomDescription, RoomExit, RoomDescriptionWithExits

class RoomExits(BaseModel):
    exits: list[RoomExit] = Field(
        description="A list of exits connecting the source room to destination rooms",
    )

# Prompt to guide the room exit creation
room_exit_prompt = """
You are a master world builder with expertise in creating immersive, interconnected environments.

Your task is to generate compelling exit descriptions for rooms in an interactive fiction world.
Given a room and information about connected rooms, you will create natural, descriptive exits.

For each exit, you need to:
1. Create a short but vivid exit description as viewed from the source room
2. Provide a descriptive name for the exit that players will use to navigate
3. Ensure the exit description clearly suggests the nature of the destination

Guidelines:
- Exit descriptions should be one line or less
- Exit names should be intuitive physical objects or features (like "archway", "door", "gate", "pathway", "bridge", "stairs", "tunnel")
- Prefer one word exit names. Two or three words are acceptable for exit names, but they MUST be hyphenated.
- Rarely use cardinal directions (north, south, east, west) as exit names
- The description should hint at what lies beyond without revealing everything
- Match the tone and style of the room descriptions
- Consider the physical and thematic relationship between the connected rooms
- IMPORTANT: Each exit_name MUST be unique within a room - no duplicate exit names allowed
- IMPORTANT: No spaces allow in exit names.
"""

async def create_all_room_exits(source_room: RoomDescription, destination_rooms: list[tuple[str, RoomDescription]]) -> list[RoomExit]:
    """
    Create RoomExit objects for all connections from source_room to destination_rooms in a single LLM call.
    
    Args:
        source_room: The room where the exits are located
        destination_rooms: List of tuples with (destination_id, destination_room) for all connected rooms
        
    Returns:
        A list of RoomExit objects with destination_id, exit_description, and exit_name
    """
    if not destination_rooms:
        return []
    
    model = OpenAIModel(
        creative_model,
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    
    exit_agent = Agent(
        model=model,
        result_type=RoomExits,
        system_prompt=room_exit_prompt,
        retries=3,
        model_settings={"temperature": 0.7},  # Higher temperature for more creative descriptions
    )
    
    # Build destination descriptions for the prompt
    destinations_text = ""
    for i, (dest_id, dest_room) in enumerate(destination_rooms, 1):
        destinations_text += f"""
    DESTINATION ROOM {i}:
    Destination ID: {dest_id}
    Title: {dest_room.title}
    Brief Description: {dest_room.brief_description}
    Long Description: {dest_room.long_description}
    """
    
    user_prompt = f"""
    Please create unique exits that connect the following source room to each destination room:
    
    SOURCE ROOM:
    Title: {source_room.title}
    Brief Description: {source_room.brief_description}
    Long Description: {source_room.long_description}
    
    {destinations_text}
    
    Create a list of RoomExit objects, one for each destination room. Each exit should contain:
    1. The correct destination_id for the room it connects to
    2. A vivid but concise exit_description visible from the source room
    3. A descriptive exit_name that players will use to navigate (like "archway", "door", "gate", "pathway", etc.)
    
    IMPORTANT:
    - Do NOT use cardinal directions as exit names - use physical objects or features instead
    - Each exit_name MUST be unique and clearly distinguishable from other exits in this room
    - No two exits can have the same or similar names
    """
    
    result = await exit_agent.run(user_prompt)
    return result.data.exits

async def get_room_exits(room: RoomDescription, all_rooms: list[RoomDescription], connected_room_ids: list[str]) -> RoomDescriptionWithExits:
    """
    Generate exits for a room based on its connections to other rooms.
    
    Args:
        room: The room to generate exits for
        all_rooms: List of all rooms in the world
        connected_room_ids: List of room IDs that are connected to this room
        
    Returns:
        RoomDescriptionWithExits containing the original room data plus exits
    """
    # Create a mapping of room IDs to room objects for easy lookup
    room_map = {r.id: r for r in all_rooms}
    
    # Gather all destination rooms
    destination_rooms = []
    for connected_id in connected_room_ids:
        if connected_id in room_map:
            destination_rooms.append((connected_id, room_map[connected_id]))
    
    # Generate all exits in a single call
    exits = await create_all_room_exits(room, destination_rooms)
    
    # Create the room with exits
    return RoomDescriptionWithExits(
        id=room.id,
        title=room.title,
        brief_description=room.brief_description,
        long_description=room.long_description,
        exits=exits
    )
