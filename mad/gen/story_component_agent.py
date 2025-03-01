from pydantic import BaseModel, Field
from devtools import debug
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from mad.gen.create_world_story_agent import WorldStory
from mad.config import creative_model_instance 
from mad.core.char_agent import CharAgent
from mad.gen.data_model import RoomDescription, StoryWorldComponents


# The prompt that guides character and location extraction and description
component_extract_prompt = """
You are a master literary analyst with expertise in character identification, location analysis, and description.

We are making an improvized play version of a story.

Given the story, your task is to:

PART 1: CHARACTER ANALYSIS
1. Identify all characters that appear in the story
2. For each character, provide:
   - Their complete name as presented in the story
   - A detailed character description to give to the actor who will improvize this character. The description should include:
     * Who "you" are
     * Personality traits shown through actions and dialogue
     * Relationship to other characters
     * Motivations and goals (explicit or implied)
     * Should describe the character at the beginning of the story
     * Should include sufficient detail for the character to improv major plot points in the story
   - A brief description of the character's appearance, told in the third person.
     This should start with the character's name, e.g. "<n> is a... He/She has..."

PART 2: LOCATION ANALYSIS
1. Identify all locations where important plot points or scenes take place in the story
2. For each location, provide:
   - A title/name for the location (e.g., "The Old Mill", "Central Park Bench", "Castle Dungeon")
   - A unique ID derived from the title (lowercase with underscores, e.g., "the_old_mill")
   - A brief description (1-2 sentences) that captures the essential feel of the place
   - A longer, more detailed description (3-5 sentences) that includes atmospheric details, notable features, and why this location is significant to the story
3. Additionally, identify and invent if necessary, 1-5 locations which connect the key locations together.

Your character analysis should:
- Focus only on characters who play a role in the narrative
- Include both protagonists and antagonists
- Capture the essence of each character
- Use specific details from the text to support your descriptions
- Avoid inventing details not supported by the text
- Remember that the method actors want to stay in character completely, so write the description in the second person

Your location analysis should:
- Focus on places where key narrative events occur
- Include a mix of locations that represent different aspects of the story world
- Emphasize sensory details and atmosphere
- Highlight how each location contributes to the story or characters
- Create memorable, distinct locations that would make for compelling stage settings
"""


async def extract_story_components(story: WorldStory) -> StoryWorldComponents:
    """
    Extract and describe characters and key locations from a world story.
    
    Args:
        story: The story to analyze for characters and locations
        
    Returns:
        A StoryWorldComponents object containing the story, characters and locations
    """
    extraction_agent = Agent(
        model=creative_model_instance,
        result_type=StoryWorldComponents,
        system_prompt=component_extract_prompt,
        retries=3,
        model_settings={"temperature": 0.3},  # Lower temperature for more consistent analysis
    )
    
    # Run the agent to extract character and location descriptions
    user_prompt = f"""
    Analyze this story and identify the key characters and important locations with detailed descriptions:
    
    Title: {story.title}
    
    Story:
    {story.content}
    """
    
    result = await extraction_agent.run(user_prompt)
    # Add the story to the result
    components = result.data
    if result._state.retries>1:
        debug(result)
    return components
