from devtools import debug
import json
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from copy import deepcopy

from mad.config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY
from mad.gen.data_model import StoryWorldComponents, WorldMergeMapping, LocationDescription


# The prompt that guides world merging
world_merger_prompt = """
You are a master world builder with expertise in narrative design and world architecture.

Your task is to examine multiple story worlds extracted from different stories and merge them 
into a single, cohesive game world where all the stories could plausibly take place.

Given multiple StoryWorldComponents (each containing characters, locations, and connections between locations), 
you will:

1. IDENTIFY DUPLICATE LOCATIONS:
   - Find locations across different stories that are the same place
   - Create a mapping of old_location_id -> new_location_id to designate which ID should be used going forward
   - When identifying duplicates, consider:
     * Similar names/titles
     * Locations that would be confusing if they were duplicated must be merged
     * Locations which could live distinctly should not be merged
     * In general, less-important connection locations should not be merged. They can help keep an interesting map
     * If the same ID is used in multiple worlds, it will automatically be merged and does not need to be considered

2. CREATE NEW CONNECTOR LOCATIONS (1-5):
   - Design 1-5 new locations that can serve as connective tissue between the different story worlds
   - Each new location should:
     * Have a unique ID, title, brief description, and long description
     * Make narrative sense as a connection point between story elements
     * Fit the themes and atmosphere of the locations it connects

3. DESIGN NEW CONNECTIONS:
   - Create new connections between locations to ensure all stories are interconnected
   - New connections is a dictionary mapping location to list of new connections
   - Each connection is a mapping from source location id to a list of locations ids which are new connections
   - Ensure that by following these connections, a player could reach any location from any other location

4. SELECT A STARTING LOCATION:
   - Choose one location ID that would serve as an ideal starting point for players
   - This should be a location that:
     * Provides a good introduction to the merged world
     * Has narrative significance
     * Offers clear paths to multiple story elements

Your solution should create a unified world that feels coherent and natural, where the different 
stories can coexist without feeling artificially forced together. Consider the geographic and 
thematic relationships between locations when designing how they connect.
"""


async def merge_story_worlds(story_components: list[StoryWorldComponents]) -> WorldMergeMapping:
    """
    Merge multiple story world components into a single cohesive world.
    
    Args:
        story_components: List of StoryWorldComponents objects each containing locations, characters, 
                          and connections from different stories
        
    Returns:
        A WorldMergeMapping object containing instructions for how to merge the worlds
    """
    # Initialize the agent for world merging
    model = OpenAIModel(
        creative_model,
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    
    merger_agent = Agent(
        model=model,
        result_type=WorldMergeMapping,
        system_prompt=world_merger_prompt,
        retries=2,
        model_settings={"temperature": 0.2},
    )
    
    # Run the agent to merge the worlds
    user_prompt = """\
I need to merge story worlds into a single cohesive game world.

Here are the details of all story locations we need to merge:"""
    all_connections = {}
    for story in story_components:
        for loc in story.locations:
            user_prompt += f"{loc.id}: {loc.title}\n"
            user_prompt += f"{loc.brief_description}\n"
            user_prompt += "Connections: " + ", ".join(story.location_connections.get(loc.id,[]))
            user_prompt += "\n----------------\n\n"
            all_connections[loc.id] = story.location_connections.get(loc.id, [])

    user_prompt += f"""\
All Connections:
{json.dumps(all_connections, indent=4)}

Please identify duplicate locations, create new connector locations, design new connections, 
and select a starting location according to your instructions.
"""
    
    result = await merger_agent.run(user_prompt)
    
    return result.data


def apply_merge_plan(plan: WorldMergeMapping, story_components: list[StoryWorldComponents]) -> StoryWorldComponents:
    """
    Apply a merge plan to combine multiple story components into a single unified story world.
    
    Args:
        plan: The WorldMergeMapping containing instructions for merging worlds
        story_components: List of StoryWorldComponents to be merged
        
    Returns:
        A single StoryWorldComponents object representing the merged world
    """
    # Create a new StoryWorldComponents to hold the merged world
    merged_world = StoryWorldComponents(
        characters=[],
        locations=[],
        character_locations={},
        location_connections={}
    )
    
    # Create a mapping of location IDs for easy lookup
    location_map = {}
    
    # Step 1: Collect all locations, applying the duplication mapping
    for component in story_components:
        for location in component.locations:
            # Check if this location should be mapped to a different ID
            new_id = plan.duplicate_locations.get(location.id, location.id)
            
            # If we haven't seen this location ID (or its mapped version) before, add it
            if new_id not in location_map:
                new_location = deepcopy(location)
                new_location.id = new_id
                merged_world.locations.append(new_location)
                location_map[new_id] = new_location
    
    # Step 2: Add the new connector locations from the plan
    for new_location in plan.new_locations:
        if new_location.id not in location_map:
            merged_world.locations.append(deepcopy(new_location))
            location_map[new_location.id] = new_location
    
    # Step 3: Merge all characters
    # We don't need to deduplicate characters as they're assumed to be unique across stories
    for component in story_components:
        merged_world.characters.extend(deepcopy(component.characters))
    
    # Step 4: Update character locations, applying the location ID mapping
    for component in story_components:
        for char_id, loc_ids in component.character_locations.items():
            if char_id not in merged_world.character_locations:
                merged_world.character_locations[char_id] = []
            
            # Map old location IDs to new ones if needed
            mapped_loc_ids = [plan.duplicate_locations.get(loc_id, loc_id) for loc_id in loc_ids]
            
            # Add to existing character locations without duplicates
            for loc_id in mapped_loc_ids:
                if loc_id not in merged_world.character_locations[char_id]:
                    merged_world.character_locations[char_id].append(loc_id)
    
    # Step 5: Merge existing location connections, applying the location ID mapping
    for component in story_components:
        for source_id, dest_ids in component.location_connections.items():
            # Map the source ID if needed
            new_source_id = plan.duplicate_locations.get(source_id, source_id)
            
            # Initialize if not already present
            if new_source_id not in merged_world.location_connections:
                merged_world.location_connections[new_source_id] = []
            
            # Add each mapped destination ID if not already present
            for dest_id in dest_ids:
                new_dest_id = plan.duplicate_locations.get(dest_id, dest_id)
                if new_dest_id not in merged_world.location_connections[new_source_id]:
                    merged_world.location_connections[new_source_id].append(new_dest_id)
    
    # Step 6: Add new connections from the plan
    for source_id, dest_ids in plan.new_connections.items():
        # Initialize if not already present
        if source_id not in merged_world.location_connections:
            merged_world.location_connections[source_id] = []
        
        # Add each destination if not already present
        for dest_id in dest_ids:
            if dest_id not in merged_world.location_connections[source_id]:
                merged_world.location_connections[source_id].append(dest_id)
            
            # Also add the reverse connection for bidirectional movement
            if dest_id not in merged_world.location_connections:
                merged_world.location_connections[dest_id] = []
            if source_id not in merged_world.location_connections[dest_id]:
                merged_world.location_connections[dest_id].append(source_id)
    
    return merged_world
