from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from mad.gen.data_model import LocationDescription, LocationDescriptionWithExits
from mad.gen.data_model import WorldDescription
from ..config import creative_model_instance


starting_location_prompt = """
You are a master environment designer for an immersive text adventure.
Create a captivating location that players will remember exploring.

This is the starting location for the entire world.
When a player first logs in to this world, they will be in this location.
This location should be a good representation of the world and its theme.

Given the world description and theme, design a location with:

1. An evocative, specific title that suggests its function or atmosphere
2. A striking first impression (2-3 sentences) that immediately establishes mood and key visual elements

The location should have 2 - 4 exits.
"""


starting_location_agent = Agent(
    model=creative_model_instance,
    result_type=LocationDescriptionWithExits,
    retries=2,
    system_prompt=starting_location_prompt,
    model_settings={
        "temperature": 0.7,
    },
)


async def generate_starting_location(world: WorldDescription) -> LocationDescriptionWithExits:
    """Generate a location description that fits within the given world.

    Args:
        world: The WorldDescription containing context about the game world

    Returns:
        LocationDescriptionWithExits containing the generated location details
    """

    user_prompt = f"""
    Generate a starting location that perfectly fits this world.
    World Title: {world.title}
    World Description: {world.description}
    """

    result = await starting_location_agent.run(
        user_prompt,
    )
    return result.data
