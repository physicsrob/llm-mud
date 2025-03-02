import os
from pydantic_ai.models.openai import OpenAIModel

# Model configuration
#creative_model = "anthropic/claude-3.7-sonnet"
creative_model = "openai/gpt-4o-mini"
char_agent_model = "anthropic/claude-3.7-sonnet"
story_model = "google/gemini-2.0-flash-001" # Cheap and fast

# API configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

creative_model_instance = OpenAIModel(
    creative_model,
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)

story_model_instance = OpenAIModel(
    story_model,
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)

char_agent_model_instance = OpenAIModel(
    char_agent_model,
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)
