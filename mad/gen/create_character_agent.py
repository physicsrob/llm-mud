from pydantic import BaseModel, Field
import random

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from mad.core.room import Room
from mad.core.char_agent import CharAgent
from mad.gen.data_model import WorldDescription
from mad.config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY


class CharacterDescription(BaseModel):
    """Detailed character description for creating an NPC."""
    name: str = Field(description="The character's name")
    brief_description: str = Field(
        description="A brief one-line description of the character's appearance"
    )
    personality: str = Field(
        description="A paragraph describing the character's personality traits and behaviors"
    )
    goals: str = Field(
        description="The character's goals and motivations in a few sentences"
    )


class CharacterGenerationContext(BaseModel):
    """Context information for generating a character."""
    world_title: str = Field(description="The title of the game world")
    world_description: str = Field(description="Brief description of the game world")
    room_title: str = Field(description="The title of the room where character lives")
    room_description: str = Field(description="Description of the room where character lives")


# The prompt that guides character generation
character_gen_prompt = """
You are designing a unique non-player character (NPC) for a text adventure game. 
Create a character that would logically inhabit the given location and fit well within this fictional world.

Consider the following when designing the character:
1. Choose a name appropriate to the setting and world theme
2. Create a brief physical description that highlights their most notable features
3. Develop a personality with specific traits, quirks, and behaviors
4. Define what motivates this character and what goals they might have

The character should:
- Be interesting and memorable
- Have clear, understandable motivations and goals
- Be appropriate for the room and world they inhabit
- Have a personality that drives interesting interactions
- Avoid generic or clichéd characterizations
- Have some depth or complexity to them

Design a character that players would enjoy interacting with and who adds to the richness of the game world.
"""


async def create_character_agent(
    world_desc: WorldDescription, room: Room, world: "World"
) -> CharAgent:
    """
    Create a character agent based on the world and room descriptions.
    
    Args:
        world_desc: Description of the game world
        room: The room where the character will be placed
        world: The game world object
        
    Returns:
        A fully initialized character agent
    """
    # Initialize the agent for character generation
    model = OpenAIModel(
        creative_model,
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    
    generation_agent = Agent(
        model=model,
        result_type=CharacterDescription,
        system_prompt=character_gen_prompt,
        retries=2,
        model_settings={"temperature": 0.8},
    )
    
    # Create generation context
    context = CharacterGenerationContext(
        world_title=world_desc.title,
        world_description=world_desc.brief_description,
        room_title=room.title,
        room_description=room.brief_description
    )
    
    # Run the agent to generate character description
    result = await generation_agent.run(
        f"Create a unique character that fits in this location and world.\n\nContext: {context.model_dump_json()}"
    )
    
    char_desc = result.data
    
    # Create and return the character agent
    char_agent = CharAgent(
        name=char_desc.name,
        world=world,
        brief_description=char_desc.brief_description,
        personality=char_desc.personality,
        goals=char_desc.goals
    )
    
    return char_agent