from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal

# ANSI color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

MessageToPlayerType = Literal["server", "room", "error"]


class MessageToPlayer(BaseModel):
    """
    A message to the player. Typically for display purposes.
    """

    msg_type: MessageToPlayerType
    message: str
    msg_src: str | None = Field(
        description="The player or character who sent the message, otherwise None.",
        default=None,
    )

    def __str__(self) -> str:
        color = {"server": BLUE, "room": GREEN, "error": RED}[self.msg_type]

        src = f" {self.msg_src}" if self.msg_src else ""
        return f"{color}[{self.msg_type}]{src}{RESET}: {self.message}\n"
