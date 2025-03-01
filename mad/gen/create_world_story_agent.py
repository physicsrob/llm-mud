import asyncio
from devtools import debug
from pydantic_ai import Agent

from mad.gen.data_model import WorldDescription, StoryWorldComponents
from mad.config import story_model_instance


# The prompt that guides story generation
story_gen_prompt = """
You are a master storyteller creating engaging tales.

Use the provided world description and story title to craft a compelling story that:
1. Is approximately 500 words.
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


async def create_story_world(world_desc: WorldDescription, story_title: str) -> StoryWorldComponents:
    """
    Generate a story set in the given world with the specified title, and extract its components.
    
    Args:
        world_desc: Description of the game world
        story_title: The title for the story to be generated
        
    Returns:
        A StoryWorldComponents object containing the story characters and locations
    """
    # Initialize the agent for story generation
    generation_agent = Agent(
        model=story_model_instance,
        result_type=str,
        system_prompt=story_gen_prompt,
        retries=1,
        model_settings={"temperature": 0.8},
    )
    
    # Run the agent to generate the story
    user_prompt = f"""
    Create a compelling story with this title: "{story_title}"
    
    World context:
    Title: {world_desc.title}
    Description: {world_desc.description}
    """
    
    print(f"\nGenerating story: '{story_title}'...")
    result = await generation_agent.run(user_prompt)
    if result._state.retries > 1:
        debug(result)
    story_content = result.data
    
    # Extract characters and locations from the story
    print(f"Extracting story components from '{story_title}'...")
    # Import here to avoid circular imports
    from mad.gen.story_component_agent import extract_story_components
    components = await extract_story_components(story_title, story_content)
    debug(components)
    
    # Return the StoryWorldComponents object
    return components
