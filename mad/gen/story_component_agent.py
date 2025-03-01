import asyncio
from pydantic import BaseModel, Field
from devtools import debug
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from mad.config import creative_model_instance, story_model_instance
from mad.core.char_agent import CharAgent
from mad.gen.data_model import RoomDescription, StoryWorldComponents, CharacterDescription


# The prompt that guides basic character and location extraction
component_extract_prompt = """
You are a master literary analyst with expertise in character identification and location analysis.

Given the story, your task is to:

PART 1: CHARACTER ANALYSIS
1. Identify all characters that appear in the story
2. For each character, provide:
   - Their complete name as presented in the story
   - A minimal placeholder description (just enough to identify who they are)
   - A minimal placeholder appearance (just enough to identify who they are)

PART 2: LOCATION ANALYSIS
1. Identify all locations where important plot points or scenes take place in the story
2. For each location, provide:
   - A title/name for the location (e.g., "The Old Mill", "Central Park Bench")
   - A unique ID derived from the title (lowercase with underscores, e.g., "the_old_mill")
   - A minimal placeholder brief description (just enough to identify the location)
   - A minimal placeholder long description (just enough to identify the location)
3. Additionally, identify and invent if necessary, 1-5 locations which connect the key locations together.

Focus only on extracting the essential information. Detailed descriptions will be generated separately.
"""

# The prompt for generating detailed character descriptions
character_description_prompt = """
You are a master character developer with expertise in creating vivid, detailed character descriptions.

Your task is to create a detailed character description for a character in a story. The description should:
- Be written in the second person ("you are...")
- Include personality traits shown through actions and dialogue
- Describe relationships to other characters
- Include motivations and goals (explicit or implied)
- Describe the character at the beginning of the story
- Provide hints at how the character would respond to different situations, as observed in the story
- Include sufficient detail for an actor to improvise this character in a play

Write a rich, detailed description that captures the essence of this character and would help an actor portray them convincingly.
"""

# The prompt for generating character appearance descriptions
character_appearance_prompt = """
You are a master character developer with expertise in creating vivid, detailed character descriptions.

Your task is to create a brief but vivid description of a character's appearance. The description should:
- Be written in the third person
- Start with the character's name (e.g., "John is a tall man with...")
- Include physical details like height, build, hair, eyes, distinguishing features
- Include clothing and accessories that reflect their personality and role
- Be approximately 2-3 sentences in length

Write a concise but descriptive appearance that helps visualize this character.
"""

# The prompt for generating location descriptions
location_description_prompt = """
You are a master setting designer with expertise in creating vivid, detailed location descriptions.

Your task is to create a detailed location description for a setting in a story. The long description should:
- Include atmospheric details and notable features
- Emphasize sensory details (sights, sounds, smells, textures)
- Highlight how this location contributes to the story or characters
- Be approximately 3-5 sentences in length

Write a rich, detailed description that captures the essence of this location and would help create a compelling stage setting.
"""

# The prompt for generating brief location descriptions
location_brief_description_prompt = """
You are a master setting designer with expertise in creating concise but evocative location descriptions.

Your task is to create a brief location description for a setting in a story. The description should:
- Capture the essential feel of the place
- Be approximately 1-2 sentences in length
- Provide enough information for someone to quickly understand the location's nature and purpose

Write a concise but evocative description that immediately gives a sense of this location.
"""


async def character_description_agent(story_content: str, character_name: str) -> str:
    """
    Generate a detailed character description in second person.
    
    Args:
        story_content: The full story text
        character_name: The name of the character to describe
        
    Returns:
        A detailed character description
    """
    agent = Agent(
        model=story_model_instance,
        result_type=str,
        system_prompt=character_description_prompt,
        retries=1,
        model_settings={"temperature": 0.7},
    )
    
    user_prompt = f"""
    Based on this story, create a detailed character description for {character_name}:
    
    Story:
    {story_content}
    
    Focus specifically on {character_name}'s character traits, motivations, and relationships.
    """
    
    result = await agent.run(user_prompt)
    return result.data


async def character_appearance_agent(story_content: str, character_name: str) -> str:
    """
    Generate a character appearance description in third person.
    
    Args:
        story_content: The full story text
        character_name: The name of the character to describe
        
    Returns:
        A character appearance description
    """
    agent = Agent(
        model=story_model_instance,
        result_type=str,
        system_prompt=character_appearance_prompt,
        retries=1,
        model_settings={"temperature": 0.7},
    )
    
    user_prompt = f"""
    Based on this story, create a brief appearance description for {character_name}:
    
    Story:
    {story_content}
    
    Describe how {character_name} looks, starting with their name.
    """
    
    result = await agent.run(user_prompt)
    return result.data


async def location_description_agent(story_content: str, location_title: str) -> str:
    """
    Generate a detailed location description.
    
    Args:
        story_content: The full story text
        location_title: The title of the location to describe
        
    Returns:
        A detailed location description
    """
    agent = Agent(
        model=story_model_instance,
        result_type=str,
        system_prompt=location_description_prompt,
        retries=1,
        model_settings={"temperature": 0.7},
    )
    
    user_prompt = f"""
    Based on this story, create a detailed description for the location "{location_title}":
    
    Story:
    {story_content}
    
    Focus on creating an atmospheric, detailed description of {location_title}.
    """
    
    result = await agent.run(user_prompt)
    return result.data


async def location_brief_description_agent(story_content: str, location_title: str) -> str:
    """
    Generate a brief location description.
    
    Args:
        story_content: The full story text
        location_title: The title of the location to describe
        
    Returns:
        A brief location description
    """
    agent = Agent(
        model=story_model_instance,
        result_type=str,
        system_prompt=location_brief_description_prompt,
        retries=1,
        model_settings={"temperature": 0.7},
    )
    
    user_prompt = f"""
    Based on this story, create a brief, 1-2 sentence description for the location "{location_title}":
    
    Story:
    {story_content}
    
    Provide a concise description that captures the essence of {location_title}.
    """
    
    result = await agent.run(user_prompt)
    return result.data


async def extract_story_components(story_title: str, story_content: str) -> StoryWorldComponents:
    """
    Extract and describe characters and key locations from a story.
    
    Args:
        story_title: The title of the story
        story_content: The content of the story to analyze
        
    Returns:
        A StoryWorldComponents object containing characters and locations
    """
    print(f"\n==== EXTRACTING COMPONENTS FROM STORY: '{story_title}' ====")
    print("Step 1: Identifying basic characters and locations...")
    
    # Step 1: Extract basic components with placeholder descriptions
    extraction_agent = Agent(
        model=creative_model_instance,
        result_type=StoryWorldComponents,
        system_prompt=component_extract_prompt,
        retries=3,
        model_settings={"temperature": 0.3},  # Lower temperature for more consistent analysis
    )
    
    user_prompt = f"""
    Analyze this story and identify the key characters and important locations:
    
    Title: {story_title}
    
    Story:
    {story_content}
    """
    
    result = await extraction_agent.run(user_prompt)
    components = result.data
    if result._state.retries > 1:
        debug(result)
    
    print(f"✓ Identified {len(components.characters)} characters and {len(components.locations)} locations")
    
    # Step 2: Generate detailed descriptions concurrently
    print("Step 2: Generating detailed descriptions concurrently...")
    
    # Create all tasks
    character_desc_tasks = []
    character_appear_tasks = []
    location_brief_tasks = []
    location_long_tasks = []
    
    # Character description tasks
    print("  Creating character description tasks...")
    for character in components.characters:
        character_desc_tasks.append(character_description_agent(story_content, character.name))
        character_appear_tasks.append(character_appearance_agent(story_content, character.name))
    
    # Location description tasks
    print("  Creating location description tasks...")
    for location in components.locations:
        location_brief_tasks.append(location_brief_description_agent(story_content, location.title))
        location_long_tasks.append(location_description_agent(story_content, location.title))
    
    # Execute all tasks concurrently
    print(f"  Executing {len(character_desc_tasks)} character description tasks concurrently...")
    character_descriptions = await asyncio.gather(*character_desc_tasks)
    print("  ✓ Character descriptions completed")
    
    print(f"  Executing {len(character_appear_tasks)} character appearance tasks concurrently...")
    character_appearances = await asyncio.gather(*character_appear_tasks)
    print("  ✓ Character appearances completed")
    
    print(f"  Executing {len(location_brief_tasks)} location brief description tasks concurrently...")
    location_brief_descs = await asyncio.gather(*location_brief_tasks)
    print("  ✓ Location brief descriptions completed")
    
    print(f"  Executing {len(location_long_tasks)} location long description tasks concurrently...")
    location_long_descs = await asyncio.gather(*location_long_tasks)
    print("  ✓ Location long descriptions completed")
    
    # Assign results to the components
    print("Step 3: Assigning generated descriptions to components...")
    for i, character in enumerate(components.characters):
        character.description = character_descriptions[i]
        character.appearance = character_appearances[i]
    
    for i, location in enumerate(components.locations):
        location.brief_description = location_brief_descs[i]
        location.long_description = location_long_descs[i]
    
    print("✓ Component extraction and description complete!")
    return components
