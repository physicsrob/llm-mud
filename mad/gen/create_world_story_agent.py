from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from mad.gen.data_model import WorldDescription
from mad.config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY


class WorldStory(BaseModel):
    """A story set in a game world."""
    title: str = Field(description="The title of the story")
    content: str = Field(description="The full text of the story")


# The prompt that guides story generation
story_gen_prompt = """
You are a master storyteller creating engaging tales.

Use the provided world description and story title to craft a compelling story that:
1. Is approximately 500 - 1000 words.
2. Features vivid characters and memorable situations
3. Includes conflict, tension, and resolution
4. Illuminates the world's culture, history, or values
5. Leaves readers wanting to know more about this world

Your story should:
- Feel like it genuinely belongs in the described world
- Have a clear beginning, middle, and end
- Show rather than tell through vivid details and dialogue
- Maintain a consistent tone appropriate to the title and world
- Avoid generic fantasy tropes without fresh twists
"""


async def create_world_story(world_desc: WorldDescription, story_title: str) -> WorldStory:
    """
    Create a story set in the given world with the specified title.
    
    Args:
        world_desc: Description of the game world
        story_title: The title for the story to be generated
        
    Returns:
        A fully crafted story set in the world
    """
    # Initialize the agent for story generation
    model = OpenAIModel(
        creative_model,
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    
    generation_agent = Agent(
        model=model,
        result_type=WorldStory,
        system_prompt=story_gen_prompt,
        retries=2,
        model_settings={"temperature": 0.8},
    )
    
    # Run the agent to generate the story
    user_prompt = f"""
    Create a compelling story with this title: "{story_title}"
    
    World context:
    Title: {world_desc.title}
    Description: {world_desc.description}
    """
    
    result = await generation_agent.run(user_prompt)
    return result.data
