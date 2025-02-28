from pydantic import BaseModel, Field
from typing import Dict, List, Optional


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

    # Runtime state (mutable during gameplay)
    exits: Dict[str, str] = Field(default_factory=dict)  # direction -> room_id

    # Additional properties can be added as needed

    def describe(self) -> str:
        """Get a full description of the room."""
        return self.long_description

    def brief_describe(self) -> str:
        """Get a brief description of the room."""
        return self.brief_description
