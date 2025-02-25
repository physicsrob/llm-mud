from dataclasses import dataclass
import os
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from ..config import command_parser_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY
from .character_action import CharacterAction
from devtools import debug

prompt = """
You are a command parser for a text-based adventure game.
You will parse the players command and return a command result object

Follow these instructions precisely. 
1. See if the command seems to be asking to move. 
    If so see if the direction is one of the available exits in the current location.
    If the direction is one of the available exits:
        - return an action with type "move" and the direction
        - use the correct direction name
        - Allow reasonable abbreviations, e.g. "n" for "north", "s" for "south", etc.
    If the direction is not valid:
        - return an error message explaining they can't go that way
2. See if the command is a look command. Only look if explicitly asked, e.g. "look around", or "describe the room", etc.
    If so return an action with type "look"
3. See if the command is a say command (e.g., "say hello", "say I'm looking for treasure", etc.)
    If so return an action with type "say" and the message (everything after the word "say")
4. See if the command is an emote command (e.g., "emote smiles", "emote looks around nervously", etc.)
    Also recognize the shorthand "/me" format (e.g., "/me smiles", "/me looks around nervously")
    If so return an action with type "emote" and the message (everything after the word "emote" or "/me")
5. If none of the above, return an error message with a user friendly explanation
"""


class ParseResult(BaseModel):
    """Result of parsing a player's command input"""

    action: CharacterAction | None = Field(
        default=None, description="The parsed player action if command was valid"
    )
    error_msg: str | None = Field(
        default=None,
        description="Error message if command could not be parsed or was invalid",
    )


@dataclass
class Deps:
    world: "World"
    player: "Player"


model = OpenAIModel(
    command_parser_model,
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
)

command_parser_agent = Agent(
    model=model,
    result_type=ParseResult,
    retries=2,
    system_prompt=prompt,
    model_settings={
        "temperature": 0.0,
    },
)


@command_parser_agent.system_prompt
async def system_prompt(ctx: RunContext[Deps]) -> str:
    world, player = ctx.deps.world, ctx.deps.player

    room = world.get_character_room(player.id)

    return f"""The following exits are available: {", ".join(room.exits.keys())}\n"""


async def parse(world: "World", player: "Player", command_input: str) -> ParseResult:
    """Parse and execute a player command.

    Args:
        world: The game world instance
        player: The player issuing the command
        command_input: The command string to parse

    Returns:
        ParseResult containing either a PlayerAction or error message
    """
    room = world.get_character_room(player.id)
    
    # Direct movement command
    if command_input in room.exits:
        return ParseResult(
            action=CharacterAction(action_type="move", direction=command_input)
        )
    # Look command shortcuts
    elif command_input in ("l", "look", "describe"):
        return ParseResult(action=CharacterAction(action_type="look"))
    # Say command
    elif command_input.startswith("say "):
        message = command_input[4:].strip()
        if message:
            return ParseResult(action=CharacterAction(action_type="say", message=message))
        else:
            return ParseResult(error_msg="What do you want to say?")
    # Emote command
    elif command_input.startswith("emote "):
        message = command_input[6:].strip()
        if message:
            return ParseResult(action=CharacterAction(action_type="emote", message=message))
        else:
            return ParseResult(error_msg="What do you want to emote?")
    # Alternative emote command with /me
    elif command_input.startswith("/me "):
        message = command_input[4:].strip()
        if message:
            return ParseResult(action=CharacterAction(action_type="emote", message=message))
        else:
            return ParseResult(error_msg="What do you want to emote?")
    # Use LLM parser for more complex commands
    else:
        result = await command_parser_agent.run(
            command_input, deps=Deps(world=world, player=player)
        )
        return result.data
