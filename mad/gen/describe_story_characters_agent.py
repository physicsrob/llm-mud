from pydantic import BaseModel, Field
from devtools import debug
from typing import List
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from mad.gen.create_world_story_agent import WorldStory
from mad.config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY


class StoryCharacter(BaseModel):
    """A character that appears in a world story."""
    name: str = Field(description="The character's full name")
    description: str = Field(description="A detailed character description told in the second person")
    appearance: str = Field(description="A brief description of the characters appearance. Told in the third person.")

class StoryCharacters(BaseModel):
    """Characters extracted from a story."""
    characters: List[StoryCharacter] = Field(
        description="List of characters that appear in the story",
        default_factory=list
    )


# The prompt that guides character extraction and description
character_extract_prompt = """
You are a master literary analyst with expertise in character identification and description.

We are making an improvized play version of a story.

Given the story, your task is to:
1. Identify all characters that appear in the story
2. For each character, provide:
   - Their complete name as presented in the story
   - A character description to give to the actor who will improvize this character. The description should:
     * Who "you" are
     * Personality traits shown through actions and dialogue
     * Relationship to other characters
     * Motivations and goals (explicit or implied)
     * Should describe the character at the beginning of the story
     * Should include sufficient detail for the character to improv major plot points in the story
   - A brief yet detailed description of the characters appearance, told in the third person.
     should start with the characters name, e.g. "<Name> is a ... She has ... "

Our hope is that if we give these character briefs to skilled improve actors,
and place them on stage, they have a reasonable chance of improvizing a story
similar to the one told.

Your analysis should:
- Focus only on characters who play a role in the narrative
- Include both protagonists and antagonists
- Capture the essence of each character
- Use specific details from the text to support your descriptions
- Avoid inventing details not supported by the text

Remember that the method actors want to stay in character completely. So
write the description in the second person, so that they can read and become
the character.
"""


async def describe_story_characters(story: WorldStory) -> StoryCharacters:
    """
    Extract and describe characters from a world story.
    
    Args:
        story: The story to analyze for characters
        
    Returns:
        A collection of character descriptions extracted from the story
    """
    # Initialize the agent for character extraction
    model = OpenAIModel(
        creative_model,
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    
    extraction_agent = Agent(
        model=model,
        result_type=StoryCharacters,
        system_prompt=character_extract_prompt,
        retries=4,
        model_settings={"temperature": 0.3},  # Lower temperature for more consistent analysis
    )
    
    # Run the agent to extract character descriptions
    user_prompt = f"""
    Analyze this story and identify the key characters with detailed descriptions:
    
    Title: {story.title}
    
    Story:
    {story.content}
    """
    
    result = await extraction_agent.run(user_prompt)
    return result.data
