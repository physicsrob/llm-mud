from .character import Character
from asyncio import Queue
from enum import Enum
from pydantic import BaseModel

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
    msg_src: str | None = None

    def __str__(self) -> str:
        color = {
            PlayerMessageType.SERVER: BLUE,
            PlayerMessageType.ROOM: GREEN,
            PlayerMessageType.ERROR: RED
        }[self.msg_type]
        
        src = f" {self.msg_src}" if self.msg_src else ""
        return f"{color}[{self.msg_type.value}]{src}{RESET}: {self.message}\n"

class Player(Character):
    """Represents a player character in the game."""

    def __init__(self, name: str, world: "World"):
        super().__init__(name, world)
        self.queue: Queue[PlayerMessage] = Queue()

    def __aiter__(self):
        return self
    
    async def __anext__(self):
        """Get the next message for the player."""
        return await self.queue.get()

    async def handle_input(self, input: str) -> None:
        input = input.strip()

        if input in ("north", "south", "east", "west"):
            room = self.world.move_character(self.id, input)
            if room is None:
                await self.send_message(PlayerMessageType.ERROR, f"You can't move {input}")  
            else:
                description = room.describe()
                await self.send_message(PlayerMessageType.SERVER, f"You move {input}")
                await self.send_message(PlayerMessageType.ROOM, description, room.name)
        else:
            await self.send_message(PlayerMessageType.ERROR, f"Unknown command: {input}")

    async def send_message(self, msg_type: PlayerMessageType, message: str, msg_src: str | None = None) -> None:
        """Send a message to the player."""
        await self.queue.put(PlayerMessage(msg_type=msg_type, message=message, msg_src=msg_src))

    async def tick(self) -> None:
        pass
        #await self.send_message(PlayerMessageType.SERVER, "Tick")
