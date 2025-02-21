import os

# Model configuration for command parser
command_parser_model = "anthropic/claude-3.5-haiku"
#command_parser_model = "mistralai/mistral-nemo"
# command_parser_model = "deepseek/deepseek-chat"
# command_parser_model = "microsoft/phi-4" # DOESNT WORK
#creative_model = "gryphe/mythomax-l2-13b" # DOESNT SUPPORT TOOL
creative_model = "anthropic/claude-3.5-sonnet"


# API configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
