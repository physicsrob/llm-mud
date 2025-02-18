from character import Character
from asyncio import Queue

class Player(Character):
    """Represents a player character in the game."""

    def __init__(self, name: str, world: "World"):
        super().__init__(name, world)
        self.queue: Queue[str] = Queue()

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
                await self.send_message(f"You can't move {input}")  
            else:
                description = room.describe()
                await self.send_message(f"You move {input}")
                await self.send_message(description)
        else:
            await self.send_message(f"Unknown command: {input}")

    async def send_message(self, message: str) -> None:
        """Send a message to the player."""
        await self.queue.put(message)
