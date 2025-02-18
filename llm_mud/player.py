from .character import Character
from asyncio import Queue
from .messages import PlayerMessage, PlayerMessageType

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

    async def send_message(self, msg_type: PlayerMessageType, message: str, msg_src: str | None = None) -> None:
        """Send a message to the player."""
        await self.queue.put(PlayerMessage(msg_type=msg_type, message=message, msg_src=msg_src))

    async def tick(self) -> None:
        pass
        #await self.send_message(PlayerMessageType.SERVER, "Tick")
