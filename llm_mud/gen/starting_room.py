from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from llm_mud.gen.data_model import RoomDescription
from llm_mud.gen.data_model import WorldDescription
from ..config import creative_model_instance


starting_room_prompt = """
You are a master environment designer for an immersive text adventure.
Create a captivating room that players will remember exploring.

This is the starting room for the entire world.
When a player first logs in to this world, they will be in this room.
This room should be a good representation of the world and its theme.

Given the world description and theme, design a room with:

1. An evocative, specific title that suggests its function or atmosphere
2. A striking first impression (2-3 sentences) that immediately establishes mood and key visual elements

The room should have 2 - 4 exits.
"""


starting_room_agent = Agent(
    model=creative_model_instance,
    result_type=RoomDescription,
    retries=2,
    system_prompt=starting_room_prompt,
    model_settings={
        "temperature": 0.7,
    },
)


async def generate_starting_room(world: WorldDescription) -> RoomDescription:
    """Generate a room description that fits within the given world.

    Args:
        world: The WorldDescription containing context about the game world

    Returns:
        StartingRoomDescription containing the generated room details
    """

    user_prompt = f"""
    Generate a starting room that perfectly fits this world.
    World Title: {world.title}
    World Description: {world.long_description}
    Other World Details: {world.other_details}
    """

    result = await starting_room_agent.run(
        user_prompt,
    )
    return result.data
