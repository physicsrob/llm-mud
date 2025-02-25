from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal

class MessageToCharacter(BaseModel):
    """
    A message to a character. Typically for display purposes.
    
    Instead of using message types with prefixes, we now use titles and colors
    to clearly differentiate different types of messages.
    """

    message: str
    title: str | None = None
    title_color: str | None = None  # Can be hex color like "#FF0000" or named color
    message_color: str | None = None  # Can be hex color like "#FF0000" or named color
    msg_src: str | None = Field(
        description="The player or character who sent the message, otherwise None.",
        default=None,
    )
    scroll: bool = Field(
        description="Whether the client should scroll the terminal for this message.",
        default=False,
    )
