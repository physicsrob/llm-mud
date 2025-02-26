from typing import List

from pydantic import BaseModel, Field
from pydantic_ai import RunContext, Tool

from .character_action import CharacterAction


class RoomInfo(BaseModel):
    """Information about a room in the game world."""
    
    room_id: str
    title: str
    description: str
    exits: list[str] = Field(description="List of available exit directions from this room")
    characters: list[str] = Field(default_factory=list, description="List of character names present in the room")



async def look(ctx: RunContext) -> RoomInfo:
    """Look around the current room to gather information about the surroundings.
    
    Performs a look action that returns detailed information about the
    character's current location, including the room's description,
    available exits, and other characters present in the room.
    
    Returns:
        RoomInfo object containing room id, title, description, exits, and characters
    """
    character = ctx.deps.character
    world = ctx.deps.world
    
    room = world.get_character_room(character.id)
    
    # Get characters in the room excluding the current character
    characters_in_room = []
    if room.id in world.room_characters:
        for char_id in world.room_characters[room.id]:
            if char_id != character.id and char_id in world.characters:
                characters_in_room.append(world.characters[char_id].name)
    
    return RoomInfo(
        room_id=room.id,
        title=room.title,
        description=room.description,
        exits=list(room.exits.keys()),
        characters=characters_in_room
    )

async def move(ctx: RunContext, direction: str) -> bool:
    """Move the character in the specified direction.
    
    Attempts to move the character to a connected room in the given direction.
    The movement will only succeed if there is an exit in that direction.
    
    Args:
        direction: The direction to move (north, south, east, west, up, down, etc.)
        
    Returns:
        True if the movement was successful, False otherwise
    """
    character = ctx.deps.character
    world = ctx.deps.world
    
    action = CharacterAction(action_type="move", direction=direction)
    success = await world.process_character_action(character, action)
    
    # Update character's current room in the state
    if success:
        new_room = world.get_character_room(character)
        ctx.deps.state.current_room_id = new_room.id
    
    return success

async def say(ctx: RunContext, message: str) -> bool:
    """Say something to everyone in the current room.
    
    Broadcasts a message that will be seen by all characters in the
    same room as this character.
    
    Args:
        message: The message to say
        
    Returns:
        True if the message was sent successfully
    """
    character = ctx.deps.character
    world = ctx.deps.world
    
    action = CharacterAction(action_type="say", message=message)
    success = await world.process_character_action(character, action)
    
    return success

async def emote(ctx: RunContext, action_text: str) -> bool:
    """Perform an emote action visible to everyone in the current room.
    
    Performs a physical action or expression that will be narrated to
    all characters in the same room.
    
    Args:
        action_text: The emote action to perform (e.g., "waves", "smiles", etc.)
        
    Returns:
        True if the emote was performed successfully
    """
    character = ctx.deps.character
    world = ctx.deps.world
    
    action = CharacterAction(action_type="emote", message=action_text)
    success = await world.process_character_action(character, action)
    
    return success
    
tools = [
    Tool(look),
    Tool(move),
    Tool(say),
    Tool(emote)
]


