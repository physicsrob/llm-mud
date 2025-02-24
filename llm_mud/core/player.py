from .character import Character
from asyncio import Queue
from ..networking.messages import MessageToPlayer, MessageToPlayerType
from .command_parser import parse
from .character_action import CharacterAction


class Player(Character):
    """Represents a player character in the game."""

    def __init__(self, name: str):
        super().__init__(name=name, id=name)
        self._queue: Queue[MessageToPlayer] = Queue()

    def __aiter__(self):
        """Return self as an async iterator."""
        return self

    async def __anext__(self):
        """Get the next message for the player.

        This will wait indefinitely for new messages to be added to the queue.
        The iterator should never terminate on its own unless the queue is explicitly
        closed or an exception is raised.
        """
        # This blocks until a message is available - will never naturally end
        # the async iterator unless the queue is closed elsewhere
        return await self._queue.get()

    async def send_message(
        self, msg_type: MessageToPlayerType, message: str, msg_src: str | None = None
    ) -> None:
        """Send a message to the player."""
        await self._queue.put(
            MessageToPlayer(msg_type=msg_type, message=message, msg_src=msg_src)
        )

    async def process_command(self, world: "World", command: str) -> None:
        """Process a command from the player."""
        parse_result = await parse(world, self, command)
        if parse_result.error_msg:
            await self.send_message("error", parse_result.error_msg)
            return

        action = parse_result.action
        await world.process_character_action(self, action)

    async def tick(self) -> None:
        # await self.send_message("server", "Tick")
        pass
