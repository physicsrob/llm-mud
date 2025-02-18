from .room import Room
import uuid

class Character:
    """Base class for all characters in the game."""
    
    def __init__(self, name: str, world: "World"):
        self.name = name
        self.id = str(uuid.uuid4())
        self.world: "World" = world
    
    async def tick(self) -> None:
        pass

    def get_current_room(self) -> Room:
        """Get the current room the character is in."""
        return self.world.get_character_room(self.id)
