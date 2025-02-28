import os
from pydantic_ai.models.openai import OpenAIModel

# Model configuration
creative_model = "anthropic/claude-3.5-sonnet"
char_agent_model = "anthropic/claude-3.5-sonnet"

# API configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

creative_model_instance = OpenAIModel(
    creative_model,
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)

char_agent_model_instance = OpenAIModel(
    char_agent_model,
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)
