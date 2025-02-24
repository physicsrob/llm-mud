from pydantic import BaseModel


class Character(BaseModel):
    """Base class for all characters in the game."""

    id: str
    name: str

    async def tick(self) -> None:
        pass

    class Config:
        # Allow arbitrary types like Queue
        arbitrary_types_allowed = True
