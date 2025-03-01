from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class RoomExit(BaseModel):
    """
    An exit leading from one room to another.
    """
    destination_id: str
    exit_description: str
    exit_name: str


class Room(BaseModel):
    """
    Room in the game world.

    Contains both descriptive properties and
    runtime state that changes during gameplay.
    """

    # ID
    id: str

    # Descriptive properties (generally immutable after creation)
    title: str
    brief_description: str
    long_description: str

    # Room exits
    exits: Dict[str, str] = Field(default_factory=dict)  # direction -> room_id
    exit_objects: List[RoomExit] = Field(default_factory=list)

    def describe(self) -> str:
        """Get a full description of the room."""
        return self.long_description

    def brief_describe(self) -> str:
        """Get a brief description of the room."""
        return self.brief_description
