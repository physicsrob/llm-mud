from pydantic import BaseModel, Field
from .save import RoomData


class Room:
    """Represents a room in the game world with its properties and available exits."""

    def __init__(self, id: str, room_data: RoomData):
        self.id: str = id
        self.name: str = room_data.name
        self.description: str = room_data.description
        self.exits: dict[str, "Room"] = {}  # Will be populated after room creation

    def describe(self) -> str:
        """Get a full description of the room, including its name, description, and available exits.

        Returns:
            A formatted string containing the room's description
        """
        exit_list = ", ".join(self.exits.keys()) if self.exits else "none"
        return f"{self.name}\n\n{self.description}\n\nExits: {exit_list}"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Room(id='{self.id}', name='{self.name}')"
