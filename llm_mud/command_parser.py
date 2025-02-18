from dataclasses import dataclass
import os
from enum import Enum
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from .player import Player
from .messages import PlayerMessage, PlayerMessageType
from .world import World
from devtools import debug

class CommandResultType(Enum):
    MOVE = "move"
    LOOK = "look"
    ERROR_MSG = "error_msg"

class CommandResult(BaseModel):
    type: CommandResultType
    args: list[str] = Field(description='Arguments for the command')

@dataclass
class Deps:
    world: World
    player: Player

model = OpenAIModel(
    "anthropic/claude-3.5-haiku",
    base_url='https://openrouter.ai/api/v1',
    api_key=os.getenv('OPENROUTER_API_KEY'),
)

command_parser_agent = Agent(
    model=model,
    result_type=CommandResult,
    retries=2,
    system_prompt=(
        'You are a command parser for a text-based adventure game.'
        'You are given a command from a player.'
        'You need to parse the command.'
        'If no result makes sense, return an error.'
        'If the command is a move, return the direction as an argument.'
        'If the command is a look, return an empty list.'
        'If the command results in an error_msg, return the error message as an argument.'
    ),
)

@command_parser_agent.system_prompt
async def system_prompt(ctx: RunContext[Deps]) -> str:
    world, player = ctx.deps.world, ctx.deps.player

    room = player.get_current_room()

    return f"""
    The following directions are available: {", ".join(room.exits.keys())}
    """

async def parse(world: World, player: Player, command: str) -> None:
    """Parse and execute a player command.
    
    Args:
        world: The game world instance
        player: The player issuing the command
        command: The command string to parse
    """
    result = (await command_parser_agent.run(command, deps=Deps(world=world, player=player))).data
    print(result)
    if result.type == CommandResultType.ERROR_MSG:
        await player.send_message(PlayerMessageType.ERROR, result.args[0])
    elif result.type == CommandResultType.MOVE:
        room=world.move_character(player.id, result.args[0])
        if room is None:
            await player.send_message(PlayerMessageType.ERROR, "You can't go that way.")
        else:
            await player.send_message(PlayerMessageType.ROOM, room.describe())
    elif result.type == CommandResultType.LOOK:
        room=player.get_current_room()
        await player.send_message(PlayerMessageType.ROOM, room.describe())

