from typing import Literal
from pydantic import Field
from .character import Character
from asyncio import Queue
from ..networking.messages import MessageToCharacter
from .command_parser import parse
from .character_action import CharacterAction


class Player(Character):
    """Represents a player character in the game."""
    
    type: Literal["Player"] = Field(default="Player")

    def __init__(self, name: str):
        super().__init__(name=name, id=name)
        self._queue: Queue[MessageToCharacter] = Queue()

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

    async def send_message(self, msg: MessageToCharacter) -> None:
        """Send a message to the player by adding it to the message queue."""
        await self._queue.put(msg)

    async def process_command(self, world: "World", command: str) -> None:
        """Process a command from the player."""
        parse_result = await parse(world, self, command)
        if parse_result.error_msg:
            await self.send_message(
                MessageToCharacter(
                    title="Error",
                    title_color="red",
                    message=parse_result.error_msg,
                    message_color="red"
                )
            )
            return

        action = parse_result.action
        await world.process_character_action(self, action)

    async def tick(self) -> None:
        # Message creation moved out of this method
        pass
