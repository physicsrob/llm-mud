import os
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from .player import Player
from .messages import PlayerMessage, PlayerMessageType
from .world import World
from devtools import debug

@dataclass
class Deps:
    player: Player
    world: World

model = OpenAIModel(
    "anthropic/claude-3.5-haiku",
    base_url='https://openrouter.ai/api/v1',
    api_key=os.getenv('OPENROUTER_API_KEY'),
)

command_parser_agent = Agent(
    model=model,
    result_type=str,
    retries=2,
    system_prompt=(
        'You are a command parser for a text-based adventure game.'
        'You are given a command from a player.'
        'You need to parse the command and execute it.'
        'Tools take care of sending messages to the player.'
        'If no tool makes sense, use the error tool to send an appropriate error message to the player.'
        'Always call EXACTLY one tool, and then stop.'
        'Always respond with the string "done" when you are finished.'
    ),
)

@command_parser_agent.system_prompt
async def system_prompt(ctx: RunContext[Deps]) -> str:
    world, player = ctx.deps.world, ctx.deps.player

    room = player.get_current_room()

    return f"""
    The following directions are available:
    {", ".join(room.exits.keys())}
    """

@command_parser_agent.tool
async def move(ctx: RunContext[Deps], direction: str) -> None:
    """
    Move the player in the given direction.
    
    Args:
        direction: The direction to move the player
    """
    world, player = ctx.deps.world, ctx.deps.player
    room = world.move_character(player.id, direction)
    if room is None:
        await player.send_message(PlayerMessageType.ERROR, f"You can't move {direction}")
    else:
        description = room.describe()
        await player.send_message(PlayerMessageType.SERVER, f"You move {direction}")
        await player.send_message(PlayerMessageType.ROOM, description, msg_src=room.name)


@command_parser_agent.tool
async def look(ctx: RunContext[Deps], ignore:bool = False) -> None:
    """
    Look around the current room.

    Always call with ignore=True.
    
    """
    world, player = ctx.deps.world, ctx.deps.player
    room = player.get_current_room()
    description = room.describe()
    await player.send_message(PlayerMessageType.ROOM, message=description)

@command_parser_agent.tool
async def error(ctx: RunContext[Deps], message: str):
    """
    Send an error message to the player.
    
    Args:
        message: The error message to send to the player
    """
    world, player = ctx.deps.world, ctx.deps.player
    await player.send_message(PlayerMessageType.ERROR, message)


async def parse(world: World, player: Player, command: str) -> None:
    """Parse and execute a player command.
    
    Args:
        world: The game world instance
        player: The player issuing the command
        command: The command string to parse
    """
    result = await command_parser_agent.run(command, deps=Deps(world=world, player=player))
    # if result is not None:
    #     debug(result.all_messages())

