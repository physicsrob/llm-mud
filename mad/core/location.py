from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class LocationExit(BaseModel):
    """
    An exit leading from one location to another.
    """
    destination_id: str
    exit_description: str
    exit_name: str


class Location(BaseModel):
    """
    Location in the game world.

    Contains both descriptive properties and
    runtime state that changes during gameplay.
    """

    # ID
    id: str

    # Descriptive properties (generally immutable after creation)
    title: str
    brief_description: str
    long_description: str

    # Location exits
    exits: Dict[str, str] = Field(default_factory=dict)  # direction -> location_id
    exit_objects: List[LocationExit] = Field(default_factory=list)

    def describe(self) -> str:
        """Get a full description of the location."""
        return self.long_description

    def brief_describe(self) -> str:
        """Get a brief description of the location."""
        return self.brief_description
