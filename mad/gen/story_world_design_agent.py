import asyncio
from pydantic import BaseModel, Field
from devtools import debug
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
import json

from mad.config import creative_model_instance, story_model_instance, powerful_model_instance
from mad.core.char_agent import CharAgent
from mad.gen.write_story_agent import write_story 
from mad.gen.data_model import LocationDescription, CharacterDescription

# The prompt that guides basic character and location extraction
character_extract_prompt = """
You are a master literary analyst with expertise in character identification.

Given the story, your task is to ientify all characters that appear in the story:
- For each character, provide the characters name
- If the character is not named, use a brief description that uniquely identifies the character.
- In no case should a character name be more than 4 words

Example: ["John", "John's Grandma", "The Evil Witch"]

Your result should include at least 3 characters
"""

location_extract_prompt = """
You are a master literary analyst.

Given the story, your task is to identify a list of locations where important plot points or scenes take place:
- If locations are not clear from the story, invent locations that would create a good scene locations for telling the story.
- For each location generate a short location name which uniquely identifies the location.
- Location name should be up to 4 words long
- It is acceptable to invent new locations to help tell the story.

Example: ["Village Center", "Old Tree", "Grandma's Cottage"]

Your result should include at least 3 locations.
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

# The prompt specifically for analyzing location connections
location_connections_prompt = """
You are a master literary analyst specializing in spatial relationships and narrative geography.

Your task is to analyze the story and identify all connections between locations. For each location:

1. Determine which other locations it directly connects to based on the story
2. These connections should:
   - Reflect explicit paths or routes mentioned in the story
   - Include logical connections between adjacent locations
   - Ensure that all locations are connected to at least one other location
   - Create a network where all locations can be reached from any other location

You must return a single dictionary where:
- Every location id appears exactly once as a key
- Every value is a list of location IDs that the key locations connects to

IMPORTANT: Every location must have at least one connection to ensure the world is fully navigable.

"""

# The prompt specifically for analyzing character locations
character_locations_prompt = """
You are a master literary analyst specializing in character geography and spatial positioning.

Your task is to analyze the story and identify the locations where each character is typically found or would likely visit. For each character:

1. Determine which locations they are associated with or where they would likely be encountered
2. This should be based on:
   - Explicit mentions of where characters are located in the story
   - Implied locations based on character activities and scenes
   - Logical deductions about where characters spend their time or would visit

You must return a dictionary where:
- Every character name appears exactly once as a key
- Every value is a list of location IDs where that character might be found, with their primary location listed first
- Characters should have 1-3 associated locations, depending on their mobility in the story

IMPORTANT: Every character must be assigned to at least one valid location ID.
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



class _LocationConnections(BaseModel):
    location_connections: dict[str, list[str]] = Field(
        description="For each location id, a list of location ids which are connected",
        default_factory=dict
    )

class _CharacterLocations(BaseModel):
    character_locations: dict[str, list[str]] = Field(
        description="For each character name, a list of location ids where they are likely to be found",
        default_factory=dict
    )


async def identify_location_connections(story_content: str, locations: list[LocationDescription]) -> dict[str, list[str]]:
    """
    Identify connections between locations in a story.
    
    Args:
        story_content: The full story text
        locations: List of locations extracted from the story
        
    Returns:
        A dictionary mapping location IDs to lists of connected location IDs
    """
    print("  Identifying location connections...")
    
    # Create a string representation of all locations for the prompt
    location_text = json.dumps([{"id": loc.id, "title": loc.title, "description": loc.brief_description} for loc in locations], indent=4)
    
    # Create the connection identification agent
    connection_agent = Agent(
        model=powerful_model_instance,
        result_type=_LocationConnections,
        system_prompt=location_connections_prompt,
        retries=2,
        model_settings={"temperature": 0.3},  # Lower temperature for more consistent analysis
    )
    
    user_prompt = f"""
    Analyze this story and identify all connections between the following locations:
    
    STORY:
    {story_content}

    LOCATIONS:
    {location_text}
    """
    
    result = await connection_agent.run(user_prompt)
    connections = result.data.location_connections

    # Verify that every location ID appears in the output
    location_ids = [loc.id for loc in locations]
    missing_ids = [loc_id for loc_id in location_ids if loc_id not in connections]
    
    if missing_ids:
        error_message = f"ERROR: The following location IDs are missing from the connections output: {', '.join(missing_ids)}"
        print(error_message)
        # Add the missing locations with empty connections lists
        for missing_id in missing_ids:
            connections[missing_id] = []
    
    print(f"  ✓ Identified {sum(len(dests) for dests in connections.values())} location connections")
    return connections

async def identify_character_locations(story_content: str, characters: list[CharacterDescription], locations: list[LocationDescription]) -> dict[str, list[str]]:
    """
    Identify the locations where each character is likely to be found in a story.
    
    Args:
        story_content: The full story text
        characters: List of characters extracted from the story
        locations: List of locations extracted from the story
        
    Returns:
        A dictionary mapping character names to lists of location IDs where they might be found
    """
    print("  Identifying character locations...")
    
    # Create a string representation of all characters and locations for the prompt
    character_text = json.dumps([{"name": char.name, "description": char.description} for char in characters], indent=4)
    location_text = json.dumps([{"id": loc.id, "title": loc.title, "description": loc.brief_description} for loc in locations], indent=4)
    
    # Create the character location identification agent
    char_location_agent = Agent(
        model=powerful_model_instance,
        result_type=_CharacterLocations,
        system_prompt=character_locations_prompt,
        retries=2,
        model_settings={"temperature": 0.3},  # Lower temperature for more consistent analysis
    )
    
    user_prompt = f"""
    Analyze this story and identify all likely locations for each character:
    
    STORY:
    {story_content}

    CHARACTERS:
    {character_text}
    
    LOCATIONS:
    {location_text}
    """
    
    result = await char_location_agent.run(user_prompt)
    char_locations = result.data.character_locations

    total_locations = sum(len(locs) for locs in char_locations.values())
    print(f"  ✓ Identified {total_locations} potential locations for {len(char_locations)} characters")
    return char_locations


async def get_story_characters(story_title: str, story_content: str) -> list[CharacterDescription]:
    """
    Extract and describe characters from the story.
    """
    # Step 1: Extract basic components with placeholder descriptions
    character_name_agent = Agent(
        model=powerful_model_instance,
        result_type=list[str],
        system_prompt=character_extract_prompt,
        retries=3,
        model_settings={"temperature": 0.3},
    )
    
    user_prompt = f"""
    Analyze this story and identify the characters:
    
    Title: {story_title}
    
    Story:
    {story_content}
    """
    
    result = await character_name_agent.run(user_prompt)
    names:list[str]= result.data
    if result._state.retries > 1:
        debug(result)
    print("characters: ", names)
    
    # Create all tasks
    character_desc_tasks = []
    character_appear_tasks = []
    
    # Character description tasks
    for character in names:
        character_desc_tasks.append(character_description_agent(story_content, character))
        character_appear_tasks.append(character_appearance_agent(story_content, character))
    
    # Execute all tasks concurrently
    character_descriptions = await asyncio.gather(*character_desc_tasks)
    character_appearances = await asyncio.gather(*character_appear_tasks)
    
    # Assign results to the components
    characters = []
    for i, character_name in enumerate(names):
        characters.append(CharacterDescription(
            id = character_name.replace(' ', '_').lower(),
            name = character_name,
            appearance = character_appearances[i],
            description = character_descriptions[i]
        ))
    return characters

async def get_story_locations(story_title: str, story_content: str) -> list[LocationDescription]:
    """
    Extract and describe locations from a story.
    """
    # Step 1: Extract basic components with placeholder descriptions
    location_title_agent = Agent(
        model=powerful_model_instance,
        result_type=list[str],
        system_prompt=location_extract_prompt,
        retries=3,
        model_settings={"temperature": 0.3},  # Lower temperature for more consistent analysis
    )
    
    user_prompt = f"""
    Analyze this story and identify the locations:
    
    Title: {story_title}
    
    Story:
    {story_content}
    """
    
    result = await location_title_agent.run(user_prompt)
    titles:list[str] = result.data
    if result._state.retries > 1:
        debug(result)
    print("locations: ", titles)
    
    # Create all tasks
    location_brief_tasks = []
    location_long_tasks = []
    
    # Location description tasks
    for location in titles:
        location_brief_tasks.append(location_brief_description_agent(story_content, location))
        location_long_tasks.append(location_description_agent(story_content, location))
    
    # Execute all tasks concurrently
    location_brief_descs = await asyncio.gather(*location_brief_tasks)
    location_long_descs = await asyncio.gather(*location_long_tasks)
    
    locations = []
    for i, location_title in enumerate(titles):
        locations.append(LocationDescription(
            id = location_title.replace(' ', '_').lower(),
            title = location_title,
            is_key = True,
            brief_description = location_brief_descs[i],
            long_description = location_long_descs[i],
        ))

    return locations
    


async def create_world_design(world_desc, story_title: str, theme: str) -> object:
    # Import here to avoid circular imports
    from mad.gen.data_model import WorldDesign
    
    # Generate a story based on the world description
    story_content = await write_story(world_desc, story_title, theme)
    
    # Extract characters and locations from the story
    print(f"Extracting story components from '{story_title}'...")
    locations = await get_story_locations(story_title, story_content)
    characters = await get_story_characters(story_title, story_content)

    print(f"Extracted {len(locations)=} {len(characters)=}")

    # Identify character locations 
    character_locations = await identify_character_locations(story_content, characters, locations)
   
    # Create a WorldDesign from the components
    world_design = WorldDesign(
        world_description=world_desc,
        characters=characters,
        character_locations=character_locations,
        starting_location_id="" # We'll set this after adding locations
    )
    
    # Add all locations to the WorldDesign
    for location in locations:
        world_design.add_location(location)
    
    # Identify location connections 
    location_connections = await identify_location_connections(story_content, locations)

    # Add bidirectional exits based on location connections
    for location_id, connected_ids in location_connections.items():
        for connected_id in connected_ids:
            world_design.ensure_bidirectional_exits(location_id, connected_id)
    
    return world_design
