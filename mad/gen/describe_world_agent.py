from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from mad.gen.data_model import WorldDescription

from ..config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY

prompt = """
You are a master worldbuilder for an interactive text adventure.

Create an immersive game world with:
1. An evocative title that captures the essence of the setting
2. A rich description that:
   - Engages all senses (sights, sounds, smells, textures)
   - Uses vivid, specific language and strong action verbs
   - Varies sentence structure for rhythmic flow
   - Incorporates mysterious elements that invite exploration
   - Hints at hidden dangers and treasures
   - Suggests a living world with hints of its history
3. Ten engaging story titles for tales set in this world that:
   - Showcase different aspects of the world and its inhabitants
   - Hint at interesting conflicts, mysteries, or adventures
   - Each have a different tone or focus (heroic, mysterious, humorous)
   - Intrigue players and make them curious about the stories

The world should:
- Center on the user's theme
- Feature at least one unusual characteristic that makes this world unique
- Leave open questions that spark curiosity
- Set the stage for a rich, engaging story
- Not be focused on a single location or location, but rather a theme or setting that can be explored in a series of locations

Important:
- The description should set the stage for storytelling
- Do not include any elements in the description that would constrain stories from unfolding
- The story titles should feel like they genuinely belong in this world
- Each title should suggest a different aspect of the world or type of tale

Avoid:
- Generic fantasy tropes without fresh twists
- Overly formal or academic language
- Information dumps without storytelling
- Telling rather than showing
"""

model = OpenAIModel(
    creative_model,
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)

world_gen_agent = Agent(
    model=model,
    result_type=WorldDescription,
    retries=10,
    system_prompt=prompt,
    model_settings={
        "temperature": 0.7,
    },
)


async def describe_world(theme: str) -> WorldDescription:
    """Generate a world description, optionally based on a theme.

    Args:
        theme: Optional theme to influence the world generation

    Returns:
        WorldDescription containing the generated world details
    """
    user_prompt = f"Generate a new world description with the theme: {theme}"

    result = await world_gen_agent.run(user_prompt)
    from devtools import debug
    debug(result)

    return result.data
