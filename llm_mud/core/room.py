from pydantic import BaseModel, Field

class RoomDescription(BaseModel):
    title: str = Field(
        description="The name/title of the room"
    )
    brief_description: str = Field(
        description="A short description shown when entering the room"
    )
    long_description: str = Field(
        description="A detailed description shown when examining the room"
    )

class Room:
    """A location in the game world that characters can occupy."""

    def __init__(self, room_id: str, description: RoomDescription):
        self.id: str = room_id
        self.description: RoomDescription = description
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
        return f"{self.description.title}\n\n{self.description.long_description}\n\nExits: {exit_list}"

    def __str__(self) -> str:
        return self.description.title

    def __repr__(self) -> str:
        return f"Room(id='{self.id}', title='{self.description.title}')"
