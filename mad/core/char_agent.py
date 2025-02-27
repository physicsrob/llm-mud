from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING, Literal, Union, List

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from .character import Character
from .character_action import CharacterAction
from ..networking.messages import MessageToCharacter
from ..config import creative_model, OPENROUTER_BASE_URL, OPENROUTER_API_KEY
from pydantic_ai.models.openai import OpenAIModel

if TYPE_CHECKING:
    from .world import World


# Configure global idle times
empty_room_extra_idle = 60  # Extra idle time when no players are in the room


# Agent prompt that guides character behavior
agent_prompt = """
You are a non-player character in a text adventure game. Your role is to behave like a realistic inhabitant 
of this world, making decisions about what actions to take based on your surroundings and events.

You must choose an action based on your current situation:
1. Say something to others in the room using the Say action
2. Perform an emote (like "waves" or "looks around") using the Emote action
3. Move to a connected room using the Move action
4. Idle for a period of time when appropriate

When deciding what to do:
- Consider your current location and who else is present
- Respond appropriately to messages from other characters
- Be somewhat unpredictable but believable in your behaviors
- Don't just repeat the same actions over and over
- Perform actions that make sense for your character and the setting
- Act in accordance with your personality and goals

Every action should include an idle duration (how long to pause before the next action):
- Short duration (5-20 seconds) for quick responses or when actively engaged
- Medium duration (20-45 seconds) for normal activities
- Long duration (45-90 seconds) for when less active or when little is happening

Return your decision as a structured action object, either:
- A CharacterAction (for say, emote, or move) plus an idle duration
- An IdleAction (to wait quietly for a while)

Be thoughtful about your choices based on the context provided.
"""


class TriggerType(BaseModel):
    """The reason the agent is being called"""
    reason: Literal["idle_complete", "message_received"]


class AgentContext(BaseModel):
    """Context provided to the agent for decision making"""
    character_name: str = Field(description="The name of this character")
    brief_description: str = Field(description="Brief description of this character")
    personality: str = Field(description="The character's personality")
    goals: str = Field(description="The character's goals")
    room_id: str = Field(description="ID of the current room")
    room_title: str = Field(description="Title of the current room")
    room_description: str = Field(description="Description of the current room")
    room_exits: list[str] = Field(description="List of available exit directions")
    room_characters: list[str] = Field(description="Other characters in the room")
    trigger: TriggerType = Field(description="What triggered this agent run")
    message: MessageToCharacter | None = Field(
        description="The message received, if trigger was message_received",
        default=None
    )


class IdleAction(BaseModel):
    """Action to idle for a period of time"""
    duration: int = Field(
        description="How long to idle for in seconds",
        ge=5,
        le=90
    )


class ActionDecision(BaseModel):
    """The agent's decision about what action to take"""
    action: Union[CharacterAction, IdleAction] = Field(
        description="The action to perform"
    )
    idle_duration: int = Field(
        description="How long to wait before next action in seconds",
        ge=5,
        le=90,
        default=10
    )


@dataclass
class CharAgentState:
    """State for the character agent."""
    last_message: MessageToCharacter | None = None
    room_id: str = ""
    room_title: str = ""
    room_description: str = ""
    room_exits: List[str] = field(default_factory=list)
    room_characters: List[str] = field(default_factory=list)


class CharAgent(Character):
    """An agent-based character that can interact with the world autonomously."""
    
    brief_description: str = Field(
        description="A brief description of the character",
        default=""
    )
    personality: str = Field(
        description="A paragraph describing the character's personality",
        default=""
    )
    goals: str = Field(
        description="Character's goals and motivations",
        default=""
    )
    
    def __init__(self, name: str, world: "World", brief_description: str = "", 
                 personality: str = "", goals: str = ""):
        super().__init__(name=name, id=f"agent_{name}")
        
        # Set character traits
        self.brief_description = brief_description
        self.personality = personality
        self.goals = goals
        
        # Initialize attributes with underscore prefix to exclude from serialization
        self._state = CharAgentState()
        self._world = world
        self._idle_until = time.time() + 10
        
        # Initialize the agent
        model = OpenAIModel(
            creative_model,
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
        self._agent = Agent(
            model=model,
            result_type=ActionDecision,
            system_prompt=agent_prompt,
            retries=2,
            model_settings={"temperature": 0.7},
        )
        
    async def _update_room_info(self) -> None:
        """Update the agent's knowledge about the current room."""
        room = self._world.get_character_room(self.id)
        if not room:
            return
            
        # Update room information
        self._state.room_id = room.id
        self._state.room_title = room.title
        self._state.room_description = room.brief_description
        self._state.room_exits = list(room.exits.keys())
        
        # Get characters in the room excluding self
        characters_in_room = []
        if room.id in self._world.room_characters:
            for char_id in self._world.room_characters[room.id]:
                if char_id != self.id and char_id in self._world.characters:
                    characters_in_room.append(self._world.characters[char_id].name)
        
        self._state.room_characters = characters_in_room
        
    async def tick(self) -> None:
        """
        Process the agent's behavior for one tick.
        
        This performs one action based on current state.
        """
        # Update room info at the start of each tick
        await self._update_room_info()
        
        # If there's a message to respond to, handle it first
        if self._state.last_message:
            message = self._state.last_message
            self._state.last_message = None
            await self._run_agent_for_message(message)
            return
            
        # Check if we're still in idle period
        if time.time() < self._idle_until:
            return  # Do nothing during idle time
        
        # Idle period complete, run the agent to decide next action
        await self._run_agent_for_idle()
    
    async def _run_agent_for_idle(self) -> None:
        """Run the agent when idle timer completes"""
        # Prepare context for the agent
        context = AgentContext(
            character_name=self.name,
            brief_description=self.brief_description,
            personality=self.personality,
            goals=self.goals,
            room_id=self._state.room_id,
            room_title=self._state.room_title,
            room_description=self._state.room_description,
            room_exits=self._state.room_exits,
            room_characters=self._state.room_characters,
            trigger=TriggerType(reason="idle_complete")
        )
        
        # Run the agent
        result = await self._agent.run(
            f"Decide what to do next. Choose an appropriate action for the current situation.\n\nContext: {context.model_dump_json()}"
        )
        
        # Process the result
        await self._process_action_decision(result.data)
    
    async def _run_agent_for_message(self, message: MessageToCharacter) -> None:
        """Run the agent when a message is received"""
        # Prepare context for the agent
        context = AgentContext(
            character_name=self.name,
            brief_description=self.brief_description,
            personality=self.personality,
            goals=self.goals,
            room_id=self._state.room_id,
            room_title=self._state.room_title,
            room_description=self._state.room_description,
            room_exits=self._state.room_exits,
            room_characters=self._state.room_characters,
            trigger=TriggerType(reason="message_received"),
            message=message
        )
        
        # Run the agent
        result = await self._agent.run(
            f"Decide how to respond to this message. Choose an appropriate action based on the message content.\n\nContext: {context.model_dump_json()}"
        )
        
        # Process the result
        await self._process_action_decision(result.data)
    
    async def _process_action_decision(self, decision: ActionDecision) -> None:
        """Process the action decision from the agent"""
        action = decision.action
        
        # Check if it's an idle action
        if isinstance(action, IdleAction):
            self._idle_until = time.time() + action.duration
            return
        
        # Otherwise, it's a character action
        await self._world.process_character_action(self, action)
        
        # Apply idle time specified by the agent
        idle_time = decision.idle_duration
        
        # Check if room has any players, if not add extra idle time
        room = self._world.get_character_room(self.id)
        if room and room.id in self._world.room_characters:
            has_player = False
            for char_id in self._world.room_characters[room.id]:
                if char_id.startswith("player_"):  # Player IDs start with "player_"
                    has_player = True
                    break
            
            if not has_player:
                idle_time += empty_room_extra_idle
                
        # Set idle time for next action
        self._idle_until = time.time() + idle_time
    
    async def send_message(self, msg: MessageToCharacter) -> None:
        """
        Send a message to the agent to be processed on the next tick.
        """
        # Store the message in the state to be handled on next tick
        self._state.last_message = msg
