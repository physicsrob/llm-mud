from pydantic import BaseModel
from ..networking.messages import MessageToCharacter


class Character(BaseModel):
    """Base class for all characters in the game."""

    id: str
    name: str

    async def tick(self) -> None:
        pass
        
    async def send_message(self, msg: MessageToCharacter) -> None:
        """
        Send a message to the character.
        
        Default implementation does nothing. Subclasses should override
        this method to implement their own message handling.
        """
        pass

    class Config:
        # Allow arbitrary types like Queue
        arbitrary_types_allowed = True
