from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal

# ANSI color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

MessageToCharacterType = Literal["server", "room", "error", "say", "emote"]


class MessageToCharacter(BaseModel):
    """
    A message to a character. Typically for display purposes.
    """

    msg_type: MessageToCharacterType
    message: str
    msg_src: str | None = Field(
        description="The player or character who sent the message, otherwise None.",
        default=None,
    )
    scroll: bool = Field(
        description="Whether the client should scroll the terminal for this message.",
        default=False,
    )

    def __str__(self) -> str:
        color = {
            "server": BLUE, 
            "room": GREEN, 
            "error": RED,
            "say": YELLOW,
            "emote": CYAN
        }[self.msg_type]

        # Format based on message type
        if self.msg_type == "say" and self.msg_src:
            return f"{color}{self.msg_src} says: {RESET}{self.message}\n"
        elif self.msg_type == "emote" and self.msg_src:
            return f"{color}{self.msg_src} {self.message}{RESET}\n"
        else:
            src = f" {self.msg_src}" if self.msg_src else ""
            return f"{color}[{self.msg_type}]{src}{RESET}: {self.message}\n"
