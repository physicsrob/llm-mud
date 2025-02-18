from .room import Room
import uuid

class Character:
    """Base class for all characters in the game."""
    
    def __init__(self, name: str, world: "World"):
        self.name = name
        self.id = str(uuid.uuid4())
        self.world: "World" = world
    