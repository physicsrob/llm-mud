from pydantic import BaseModel, Field


class Room:
    """A location in the game world that characters can occupy."""

    def __init__(self, room_id: str, name: str, description: str):
        self.id: str = room_id
        self.name: str = name
        self.description: str = description
        self.exits: dict[str, "Room"] = {}

    def add_exit(self, direction: str, destination: "Room") -> None:
        """Add an exit from this room to another room."""
        self.exits[direction] = destination

    def remove_exit(self, direction: str) -> None:
        """Remove an exit from this room."""
        self.exits.pop(direction, None)

    def get_exit(self, direction: str) -> "Room | None":
        """Get the room that an exit leads to."""
        return self.exits.get(direction)

    def describe(self) -> str:
        """Get a full description of the room."""
        exit_list = ", ".join(self.exits.keys()) if self.exits else "none"
        return f"{self.name}\n\n{self.description}\n\nExits: {exit_list}"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Room(id='{self.id}', name='{self.name}')"
