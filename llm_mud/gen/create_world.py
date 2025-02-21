import json
from .world_gen import generate_world
from .room_gen import generate_starting_room
from devtools import debug

async def create_world(theme: str) -> None:
    """Create a new world with the specified theme."""
    world_desc = await generate_world(theme)
    print("\nGenerated World:")
    debug(world_desc)
    
    room_desc = await generate_starting_room(world_desc)
    print("\nGenerated Room:")
    debug(room_desc)