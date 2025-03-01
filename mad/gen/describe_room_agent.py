from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from mad.gen.data_model import Edge, RoomDescription, WorldDescription

from ..config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY

prompt = """
You are a master environment designer for an immersive text adventure.
Create a captivating room that players will remember exploring.

You will be given the world description, a theme, a room ID, and a room title, and exit connections.

For the specified room, design a room with:

1. A striking first impression (2-3 sentences) that immediately establishes mood and key visual elements
2. A layered, detailed description that:
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

describe_room_agent = Agent(
    model=model,
    result_type=RoomDescription,
    retries=2,
    system_prompt=prompt,
    model_settings={
        "temperature": 0.7,
    },
)


async def describe_room(
    world: WorldDescription, edges: list[Edge], room_id: str
) -> RoomDescription:
    """Generate a room description that fits within the given world.

    Args:
        world: The WorldDescription containing context about the game world

    Returns:
        RoomDescription containing the generated room details
    """

    room_exits = [e for e in edges if e.source_id == room_id] + [
        e.get_reverse_edge() for e in edges if e.destination_id == room_id
    ]
    room_title = next(e.source_title for e in room_exits if e.source_id == room_id)
    user_prompt = f"""
    Generate a new room description that fits in this world.
    World Title: {world.title}
    World Description: {world.description}
    Room ID: {room_id}
    Room Title: {room_title}
    Room Exits: {room_exits}
    """

    result = await describe_room_agent.run(
        user_prompt,
    )
    return result.data
