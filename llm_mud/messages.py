from enum import Enum
from pydantic import BaseModel, Field

class PlayerMessageType(Enum):
    SERVER = "server"
    ROOM = "room"
    ERROR = "error"

# ANSI color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

class PlayerMessage(BaseModel):
    msg_type: PlayerMessageType
    message: str
    msg_src: str | None = Field(description='The player or character who sent the message, otherwise None.', default=None)

    def __str__(self) -> str:
        color = {
            PlayerMessageType.SERVER: BLUE,
            PlayerMessageType.ROOM: GREEN,
            PlayerMessageType.ERROR: RED
        }[self.msg_type]
        
        src = f" {self.msg_src}" if self.msg_src else ""
        return f"{color}[{self.msg_type.value}]{src}{RESET}: {self.message}\n" 