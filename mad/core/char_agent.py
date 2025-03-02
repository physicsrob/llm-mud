from __future__ import annotations
from devtools import debug
from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from .character import Character
from .character_action import CharacterAction
from ..networking.messages import BaseMessage, DialogMessage, EmoteMessage, MovementMessage
from ..config import char_agent_model_instance
from pydantic_ai.models.openai import OpenAIModel

if TYPE_CHECKING:
    from .world import World


# Configure global idle times
empty_location_extra_idle = 60  # Extra idle time when no players are in the location

class ActionDecision(CharacterAction):
    """The agent's decision about what action to take"""
    idle_duration: int = Field(
        description="How long to wait before next action in seconds",
        ge=0,
        le=90,
        default=10
    )

@dataclass
class CharEvent:
    """Something that happened"""
    timestamp: float = field(default_factory=lambda: time.time())
    action: ActionDecision | None = None
    message: BaseMessage | None = None
    idle_until_timestamp: float = field(default_factory=lambda: time.time() + 10.0)
    
    def format_message_event(self, current_time: float) -> str:
        """Format a message event for display in the agent prompt."""
        if not self.message:
            return ""
        
        seconds_ago = int(current_time - self.timestamp)
        
        if isinstance(self.message, DialogMessage):
            return f"[{seconds_ago} seconds ago] {self.message.from_character_name} said to you: \"{self.message.content}\""
        elif isinstance(self.message, EmoteMessage):
            return f"[{seconds_ago} seconds ago] {self.message.from_character_name} {self.message.action}"
        elif isinstance(self.message, MovementMessage):
            direction_text = f" {self.message.direction}" if self.message.direction else ""
            if self.message.action == "arrives":
                return f"[{seconds_ago} seconds ago] {self.message.character_name} arrives{' from' + direction_text if direction_text else ''}"
            elif self.message.action == "leaves":
                return f"[{seconds_ago} seconds ago] {self.message.character_name} leaves{' to' + direction_text if direction_text else ''}"
        return ""
    
    def format_action_event(self, current_time: float) -> str:
        """Format an action event for display in the agent prompt."""
        if not self.action:
            return ""
            
        seconds_ago = int(current_time - self.timestamp)
        action_type = self.action.action_type
        
        if action_type == "say":
            return f"[{seconds_ago} seconds ago] You said: \"{self.action.message}\""
        elif action_type == "emote":
            return f"[{seconds_ago} seconds ago] You {self.action.message}"
        elif action_type == "move":
            return f"[{seconds_ago} seconds ago] You moved to {self.action.direction}"
        elif action_type == "idle":
            return f"[{seconds_ago} seconds ago] You waited quietly"
        return ""
    
    def format_event(self, current_time: float) -> str:
        """Format the event for display in the agent prompt."""
        if self.message:
            return self.format_message_event(current_time)
        elif self.action:
            return self.format_action_event(current_time)
        return ""


@dataclass
class CharAgentState:
    """State for the character agent."""
    events: list[CharEvent] = field(default_factory=list)
    location_id: str = ""
    location_title: str = ""
    location_description: str = ""
    location_exits: list[str] = field(default_factory=list)
    location_characters: list[str] = field(default_factory=list)
    last_processed_timestamp: float = field(default_factory=time.time)
    
    def get_new_events(self) -> list[CharEvent]:
        """Get events that have occurred since the last processing."""
        return [e for e in self.events if e.timestamp >= self.last_processed_timestamp]
        
    def get_old_events(self, max_events: int = 10) -> list[CharEvent]:
        """Get the most recent previously processed events up to max_events."""
        old_events = [e for e in self.events if e.timestamp < self.last_processed_timestamp]
        return old_events[-max_events:] if old_events else []
        
    def should_idle(self) -> bool:
        """
        Determine if the agent should continue idling based on all events.
        
        Returns:
            bool: True if agent should remain idle, False if agent should process events
        """
        current_time = time.time()
        events = self.get_new_events()
        assert len(events), "There should always be new events yet to be processed"
        
        for event in events:
            if current_time >= event.idle_until_timestamp:
                return False
            
        return True


class CharAgent(Character):
    """An agent-based character that can interact with the world autonomously."""
    
    type: Literal["CharAgent"] = Field(default="CharAgent")
    
    appearance: str = Field(
        description="A brief description of the character's appearance. Told in the third person.",
        default=""
    )
    description: str = Field(
        description="A detailed character description told in the second person. Includes personality, goals, and motivations.",
        default=""
    )
    preferred_location_ids: list[str] = Field(
        description="A list of location ids you prefer to stay in.",
        default=""
    )


    def init(self, world: "World"):
        # Initialize attributes with underscore prefix to exclude from serialization
        self._world = world
        self._state = CharAgentState()
        current_time = time.time()
        self._state.events.append(CharEvent(idle_until_timestamp=current_time+5))
        self._state.last_processed_timestamp = current_time
        
        # Initialize location info
        self._update_location_info()

    def _update_location_info(self) -> None:
        """Update the agent's knowledge about the current location."""
        location = self._world.get_character_location(self.id)
        if not location:
            return
            
        # Update location information
        self._state.location_id = location.id
        self._state.location_title = location.title
        self._state.location_description = location.brief_description
        self._state.location_exits = list(location.exits.keys())
        
        # Get characters in the location excluding self
        characters_in_location = []
        if location.id in self._world.location_characters:
            for char_id in self._world.location_characters[location.id]:
                if char_id != self.id and char_id in self._world.characters:
                    characters_in_location.append(self._world.characters[char_id].name)
        
        self._state.location_characters = characters_in_location
        
    async def tick(self) -> None:
        """
        Process the agent's behavior for one tick.
        
        This performs one action based on current state.
        """
        # Use our should_idle method to determine if we should process events
        tick_start_time = time.time()
        if self._state.should_idle():
            return  # Still in idle period

        # We have new events or idle period is complete - decide next action
        print(f"[DEBUG] {self.name}: Deciding next action")
        
        # Get new events for debugging
        new_events = self._state.get_new_events()
        
        # Create the prompt based on the trigger reason
        prompt = "Decide what to do next."

        # Run the agent
        result = await char_agent_actor.run(prompt, deps=self)
        decision:ActionDecision = result.data
        
        # Debug the response from the agent
        print(f"[DEBUG] {self.name}: Agent response: {decision}")
        
        if decision.action_type != "idle":
            await self._world.process_character_action(self, decision)
            # Update location info after the action (especially important for movement)
            self._update_location_info()

        # Check if location has any players, if not add extra idle time
        idle_time = decision.idle_duration
        location = self._world.get_character_location(self.id)
        if location and not self._world.location_has_players(location.id):
            print(f"[DEBUG] {self.name}: No players in location, adding extra {empty_location_extra_idle} seconds")
            idle_time += empty_location_extra_idle


        # Create a new event with the agent's decision and new idle time
        event = CharEvent(
            timestamp=time.time(),
            action=decision,
            message=None,
            idle_until_timestamp=time.time() + idle_time 
        )
        self._state.events.append(event)
        
        # Update the time that we last processed new events 
        self._state.last_processed_timestamp = tick_start_time 

    
    async def send_message(self, msg: BaseMessage) -> None:
        """
        Send a message to the agent to be processed on the next tick.
        """
        # Debug incoming messages
        print(f"[DEBUG] {self.name}.send_message called: {msg.model_dump()}")
        
        
        if ((isinstance(msg, DialogMessage) or isinstance(msg, EmoteMessage)) and msg.from_character_name != self.name) or isinstance(msg, MovementMessage):
            current_time = time.time()
            self._state.events.append(
                CharEvent(
                    timestamp=current_time,
                    action=None,
                    message=msg,
                    idle_until_timestamp=current_time
                )
            )

# Global agent instance that all character agents will share
char_agent_actor = Agent(
    model=char_agent_model_instance,
    result_type=ActionDecision,
    deps_type=CharAgent,
    retries=2,
    model_settings={"temperature": 0.7},
)

@char_agent_actor.system_prompt
def main_prompt(ctx) -> str:
    char_agent:CharAgent = ctx.deps
    return f"""\
{char_agent.description}

You prefer to stay in the following locations: {char_agent.preferred_location_ids}

You must choose an action based on your current situation:
1. Say something to others in the location using the Say action
2. Perform an emote (like "waves" or "looks around") using the Emote action
3. Move to a connected location using the Move action
4. Idle for a period of time when appropriate

IMPORTANT: Do NOT include actions within your Say messages. For example:
- INCORRECT: Say "Hello there! *scratches his chin* How are you doing today?"
- CORRECT: First use Emote "scratches his chin", then use Say "Hello there! How are you doing today?"

Always separate physical actions (emotes) from spoken dialogue (say). Continue conversations over
multiple say actions spread out in time, to make a natural conversational pattern.

When deciding what to do:
- Consider your current location and who else is present
- Respond appropriately to messages from other characters, but before doing so consider if they are directed at you.
If a message is not directed at you, feel free to ignore it (by for instance making an idle action).
- Engage and explore
- Be yourself

Every action should include an idle duration (how long to pause before the next action):
- Short duration (5-20 seconds) for quick responses or when actively engaged
- Medium duration (20-45 seconds) for normal activities
- Long duration (45-90 seconds) for when less active or when little is happening

Return your decision as a structured action object with the following properties:
- action_type: "move", "say", "emote", or "idle"
- direction: (for move actions) The direction to move in
- message: (for say/emote actions) What to say or the emote to perform
- idle_duration: How long to wait before the next action (in seconds)

Be thoughtful about your choices based on the context provided.
        """


@char_agent_actor.system_prompt
def context_prompt(ctx) -> str:
    char_agent:CharAgent = ctx.deps
    state:CharAgentState = char_agent._state

    result = f"""\
You are currently located at "{state.location_title}": {state.location_description}

You can see the following exits: {", ".join(state.location_exits)}

You can see the following people, characters, or entities: {", ".join(state.location_characters)}
"""

    # Get new and old events using the helper methods
    new_events = state.get_new_events()
    old_events = state.get_old_events(max_events=10)
    current_time = time.time()
    
    # Add the old events section
    result += "\n\nRecent history:"
    for event in old_events:
        formatted_event = event.format_event(current_time)
        if formatted_event:
            result += f"\n{formatted_event}"

    # Add the new events section
    result += "\n\nNew events since you last acted:"
    for event in new_events:
        formatted_event = event.format_event(current_time)
        if formatted_event:
            result += f"\n{formatted_event}"
   
    print(result)
    return result


