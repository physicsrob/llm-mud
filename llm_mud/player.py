from .character import Character
from asyncio import Queue
from .messages import MessageToPlayer, MessageToPlayerType
from .command_parser import parse
from .character_action import CharacterAction


class Player(Character):
    """Represents a player character in the game."""

    def __init__(self, name: str, world: "World"):
        super().__init__(name, world)
        self.queue: Queue[MessageToPlayer] = Queue()

    def __aiter__(self):
        return self

    async def __anext__(self):
        """Get the next message for the player."""
        return await self.queue.get()

    async def send_message(
        self, msg_type: MessageToPlayerType, message: str, msg_src: str | None = None
    ) -> None:
        """Send a message to the player."""
        await self.queue.put(
            MessageToPlayer(msg_type=msg_type, message=message, msg_src=msg_src)
        )

    async def process_command(self, command: str) -> None:
        """Process a command from the player."""
        parse_result = await parse(self.world, self, command)
        if parse_result.error_msg:
            await self.send_message("error", parse_result.error_msg)
            return

        action = parse_result.action
        await self.world.process_character_action(self, action)

    async def tick(self) -> None:
        pass
        # await self.send_message(PlayerMessageType.SERVER, "Tick")
