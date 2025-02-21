from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from ..config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY
from .world import WorldDescription

prompt = """
You are a master worldbuilder for an interactive text adventure.

Create an immersive game world with:
1. An evocative title that captures the essence of the setting
2. A captivating hook (2-3 sentences) that immediately draws players in
3. A rich, detailed description that:
   - Engages all senses (sights, sounds, smells, textures)
   - Uses vivid, specific language and strong action verbs
   - Varies sentence structure for rhythmic flow
   - Incorporates mysterious elements that invite exploration
   - Hints at hidden dangers and treasures
   - Suggests a living world with hints of its history

The world should:
- Center on the user's theme
- Balance whimsy with a sense of wonder and light danger
- Feature at least one unusual characteristic that makes this world unique
- Leave open questions that spark curiosity

Avoid:
- Generic fantasy tropes without fresh twists
- Overly formal or academic language
- Information dumps without storytelling
- Telling rather than showing


Most of these fields will be immediately observable by the player, with the exception of other_details.

other_details can contain information about the world that will not be immediately observable by the player:
- history
- secrets
- locations that may be discovered later in the game
- potential character types who might inhabit this world

"""

model = OpenAIModel(
    creative_model,
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)

world_gen_agent = Agent(
    model=model,
    result_type=WorldDescription,
    retries=2,
    system_prompt=prompt,
    model_settings={
        "temperature": 0.7, 
    },
)

async def generate_world(theme: str) -> WorldDescription:
    """Generate a world description, optionally based on a theme.
    
    Args:
        theme: Optional theme to influence the world generation
        
    Returns:
        WorldDescription containing the generated world details
    """
    user_prompt = f"Generate a new world description with the theme: {theme}"
        
    result = await world_gen_agent.run(user_prompt)
    return result.data 
