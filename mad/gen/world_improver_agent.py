from devtools import debug
import json
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from copy import deepcopy

from mad.config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY
from mad.gen.data_model import StoryWorldComponents, WorldImprovementPlan, RoomDescription


# The prompt that guides world improvement
world_improver_prompt = """
You are a master world builder with expertise in game level design and world architecture.

Your task is to analyze a game world and improve its design by ensuring no location has too many 
connections (no more than 4 connections per location). When a location has more than 4 connections,
you'll create new intermediate locations to better distribute these connections.

Given a StoryWorldComponents object (containing locations and connections between locations), 
you will:

1. IDENTIFY OVERCROWDED LOCATIONS:
   - Find locations that have more than 4 connections to other locations
   - For each overcrowded location, determine which connections should be redistributed

2. CREATE NEW INTERMEDIATE LOCATIONS:
   - Design new locations that can serve as intermediaries to reduce direct connections
   - Each new location should:
     * Have a unique ID (using the format "intermediate_[descriptive_name]")
     * Have a meaningful title, brief description, and long description
     * Make narrative sense as a connection point between locations
     * Fit the themes and atmosphere of the locations it connects

3. REDESIGN CONNECTIONS:
   - Create a new connection map that:
     * Moves some connections from overcrowded locations to the new intermediate locations
     * Ensures the world remains fully connected (can reach any location from any other)
     * Maintains the logical flow and narrative sense of movement between locations
     * Includes ALL locations in the updated connections list

Your solution should create a more balanced world design where no location has more than 4 connections,
while maintaining the narrative coherence and accessibility of the original design.
"""


async def improve_world_design(story_components: StoryWorldComponents) -> WorldImprovementPlan:
    """
    Improve a world design by ensuring no location has too many connections.
    
    Args:
        story_components: A StoryWorldComponents object containing locations and their connections
        
    Returns:
        A WorldImprovementPlan object containing new locations and updated connections
    """
    # Initialize the agent for world improvement
    model = OpenAIModel(
        creative_model,
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    
    improver_agent = Agent(
        model=model,
        result_type=WorldImprovementPlan,
        system_prompt=world_improver_prompt,
        retries=3,
        model_settings={"temperature": 0.2},
    )
    
    # Count connections for each location
    connection_counts = {}
    for source_id, dest_ids in story_components.location_connections.items():
        connection_counts[source_id] = len(dest_ids)
    
    # Find locations with too many connections
    overcrowded_locations = [loc_id for loc_id, count in connection_counts.items() if count > 4]
    
    # Run the agent to improve the world design
    user_prompt = f"""\
I need to improve a world design by ensuring no location has more than 4 connections.

The current world has {len(story_components.locations)} locations and {len(overcrowded_locations)} 
locations with more than 4 connections.

Here are the details of all the locations:"""
    all_connections = {}
    for loc in story_components.locations:
        user_prompt += f"{loc.id}: {loc.title}\n"
        user_prompt += f"{loc.brief_description}\n"
        user_prompt += "Connections: " + ", ".join(story_components.location_connections.get(loc.id,[]))
        user_prompt += "\n----------------\n\n"
        all_connections[loc.id] = story_components.location_connections.get(loc.id, [])

    user_prompt += f"""\
All Connections:
{json.dumps(all_connections, indent=4)}
Locations:

Specifically, these locations have too many connections:
{[(loc_id, len(story_components.location_connections[loc_id])) for loc_id in overcrowded_locations]}

Please create a plan to improve this world design by adding intermediate locations
and redistributing connections so no location has more than 4 connections.
    """
    
    result = await improver_agent.run(user_prompt)
    return result.data


def apply_improvement_plan(plan: WorldImprovementPlan, world: StoryWorldComponents) -> StoryWorldComponents:
    """
    Apply an improvement plan to a world to better distribute connections.
    
    Args:
        plan: The WorldImprovementPlan containing new locations and updated connections
        world: The original StoryWorldComponents to be improved
        
    Returns:
        A new StoryWorldComponents object with the improvements applied
    """
    # Create a new StoryWorldComponents to hold the improved world
    improved_world = deepcopy(world)
    
    # Add the new intermediate locations
    for new_location in plan.new_locations:
        improved_world.locations.append(deepcopy(new_location))
    
    # Replace the old connections with the improved connections
    improved_world.location_connections = deepcopy(plan.updated_connections)
    
    return improved_world
