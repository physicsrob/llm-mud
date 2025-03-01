from pydantic import BaseModel, Field


class Edge(BaseModel):
    source_id: str = Field(description="The unique identifier of the source room")
    source_title: str = Field(description="The name/title of the source room")
    destination_id: str = Field(
        description="The unique identifier of the destination room"
    )
    destination_title: str = Field(description="The name/title of the destination room")
    direction: str = Field(
        description="The direction to travel from source to destination (e.g. 'north', 'up')"
    )
    return_direction: str = Field(
        description="The direction to travel from destination back to source (e.g. 'south', 'down')"
    )

    def get_reverse_edge(self) -> "Edge":
        return Edge(
            source_id=self.destination_id,
            source_title=self.destination_title,
            destination_id=self.source_id,
            destination_title=self.source_title,
            direction=self.return_direction,
            return_direction=self.direction,
        )


class RoomDescription(BaseModel):
    id: str = Field(
        description="Typically the title, but with spaces replaced with underscores, all lowercase, etc"
    )
    title: str = Field(description="The name/title of the room")
    brief_description: str = Field(
        description="A short description shown when entering the room"
    )

    long_description: str = Field(
        description="A detailed description shown when examining the room"
    )
    exits: list[Edge] = Field(
        description="A list of exits that connect this room to other rooms."
    )


class WorldDescription(BaseModel):
    title: str = Field(description="The title of the game world")
    description: str = Field(description="The description of the game world. Should be approximately one brief paragraph.")
    story_titles: list[str] = Field(
        description="A list of engaging story titles set in this world, each fitting the world's theme",
        default_factory=list
    )
