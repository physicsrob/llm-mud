from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from ..config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY
from .room import RoomDescription
from .world import WorldDescription

prompt = """
You are a master environment designer for an immersive text adventure. Create a captivating room that players will remember exploring.

Given the world description and theme, design a room with:

1. An evocative, specific title that suggests its function or atmosphere
2. A striking first impression (2-3 sentences) that immediately establishes mood and key visual elements
3. A layered, detailed description that:
   - Engages multiple senses (what players see, hear, smell, feel)
   - Uses concrete, specific details rather than generalizations
   - Emphasizes one dominant mood or emotion
   - Places 3-4 interactive elements that invite player investigation
   - Suggests how this space is/was used by inhabitants
   - Includes subtle environmental storytelling elements

The room should:
- Feel like an organic extension of the established world
- Balance aesthetic description with functional gameplay elements
- Include at least one unexpected or surprising feature
- Contain subtle clues about the broader world/story
- Suggest possible interactions beyond simple observation
- Have its own micro-history within the larger setting

Technical considerations:
- Clear indication of exits/connections to other areas
- At least one distinctive object that could be examined further
- Variation in scale and composition (high/low elements, light/shadow)
- Environmental factors that might affect gameplay (sounds that mask movement, scents that reveal hidden aspects)

Avoid:
- Generic descriptors like "beautiful," "amazing," or "interesting"
- Static descriptions that feel like empty stage sets
- Listing features without integrating them into the space
- Describing everything with equal emphasis

Write as if you're crafting a space that will intrigue players and make them think: "I wonder what would happen if I..."
"""

model = OpenAIModel(
    creative_model,
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)

room_gen_agent = Agent(
    model=model,
    result_type=RoomDescription,
    retries=2,
    system_prompt=prompt,
    model_settings={
        "temperature": 0.7,
    },
)

async def generate_starting_room(world: WorldDescription) -> RoomDescription:
    """Generate a room description that fits within the given world.
    
    Args:
        world: The WorldDescription containing context about the game world
        
    Returns:
        RoomDescription containing the generated room details
    """
    
    user_prompt = f"""
    This is the starting room for the owrld.
    When a user first logs in to this world, they will be in this room.
    This room should be a good representation of the world and its theme.

    Generate a new room description that fits in this world.
    World Title: {world.title}
    World Description: {world.long_description}
    Other World Details: {world.other_details}
    """
        
    result = await room_gen_agent.run(
        user_prompt,
    )
    return result.data 


async def generate_room(world: WorldDescription) -> RoomDescription:
    """Generate a room description that fits within the given world.
    
    Args:
        world: The WorldDescription containing context about the game world
        
    Returns:
        RoomDescription containing the generated room details
    """
    
    user_prompt = f"""
    Generate a new room description that fits in this world.
    World Title: {world.title}
    World Description: {world.long_description}
    """
        
    result = await room_gen_agent.run(
        user_prompt,
    )
    return result.data 
