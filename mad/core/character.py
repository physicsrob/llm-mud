from typing import Literal
from pydantic import BaseModel, Field
from ..networking.messages import BaseMessage


class Character(BaseModel):
    """Base class for all characters in the game."""

    id: str
    name: str
    type: Literal["Character"]  # Discriminator field for character type
    previous_room_id: str | None = None
    previous_room_title: str | None = None

    async def tick(self) -> None:
        pass
        
    async def send_message(self, msg: BaseMessage) -> None:
        """
        Send a message to the character.
        
        Default implementation does nothing. Subclasses should override
        this method to implement their own message handling.
        """
        pass

    class Config:
        # Allow arbitrary types like Queue
        arbitrary_types_allowed = True
