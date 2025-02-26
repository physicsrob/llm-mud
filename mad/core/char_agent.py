from dataclasses import dataclass
import random
from typing import TYPE_CHECKING

from pydantic import BaseModel

from .character import Character
from .character_action import CharacterAction
from .char_agent_tools import RoomInfo
from ..networking.messages import MessageToCharacter

if TYPE_CHECKING:
    from .world import World


@dataclass
class CharAgentDeps:
    """Dependencies for CharAgent tools."""
    character: Character
    world: "World"
    state: "CharAgentState"


@dataclass
class CharAgentState:
    """State for the character agent."""
    last_message: MessageToCharacter | None = None


class CharAgent(Character):
    """An agent-based character that can interact with the world autonomously."""
    
    def __init__(self, name: str, world: "World"):
        super().__init__(name=name, id=f"agent_{name}")
        
        # Initialize attributes with underscore prefix to exclude from serialization
        self._state = CharAgentState()
        self._world = world
        
    async def tick(self) -> None:
        """
        Process the agent's behavior for one tick.
        
        This performs one action based on current state.
        """
        # If there's a message to respond to, handle it first
        if self._state.last_message:
            await self._handle_message(self._state.last_message)
            self._state.last_message = None
            return
        
        
        # Sometimes emote something about the room
        if random.random() < 0.1:
            emote_messages = [
                "looks around curiously",
                "examines the surroundings",
                "takes a moment to rest",
                "stretches leisurely"
            ]
            emote_action = CharacterAction(
                action_type="emote", 
                message=random.choice(emote_messages)
            )
            await self._world.process_character_action(self, emote_action)
        
        # 3. Sometimes move in a random direction
        if random.random() < 0.05:
            # Use the room_info we just got
            room = self._world.get_character_room(self.id)
            exits=list(room.exits.keys())
            direction = random.choice(exits)
            move_action = CharacterAction(action_type="move", direction=direction)
            await self._world.process_character_action(self, move_action)
        
    
    async def _handle_message(self, message: MessageToCharacter) -> None:
        """Handle incoming messages with simple rule-based responses."""
        if message.msg_src and message.message:
            if "hello" in message.message.lower():
                action = CharacterAction(action_type="say", message=f"Hello, {message.msg_src}!")
                await self._world.process_character_action(self, action)
            elif "how are you" in message.message.lower():
                action = CharacterAction(action_type="say", message="I'm doing well, thank you for asking!")
                await self._world.process_character_action(self, action)
    
    
    async def send_message(self, msg: MessageToCharacter) -> None:
        """
        Send a message to the agent to be processed on the next tick.
        """
        # Store the message in the state to be handled on next tick
        self._state.last_message = msg
