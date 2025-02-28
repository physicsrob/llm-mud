from __future__ import annotations
from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from .character import Character
from .character_action import CharacterAction
from ..networking.messages import MessageToCharacter
from ..config import char_agent_model_instance
from pydantic_ai.models.openai import OpenAIModel

if TYPE_CHECKING:
    from .world import World


# Configure global idle times
empty_room_extra_idle = 60  # Extra idle time when no players are in the room

class ActionDecision(BaseModel):
    """The agent's decision about what action to take"""
    action: CharacterAction | None = Field(
        description="The action to perform, or None for idle"
    )
    idle_duration: int = Field(
        description="How long to wait before next action in seconds",
        ge=5,
        le=90,
        default=10
    )

@dataclass
class CharEvent:
    """Something that happened"""
    timestamp: int = field(default_factory=lambda: int(time.time()))
    action: ActionDecision | None = None
    message: MessageToCharacter | None = None
    idle_until_timestamp: int = field(default_factory=lambda: int(time.time() + 10))


@dataclass
class CharAgentState:
    """State for the character agent."""
    events: list[CharEvent] = field(default_factory=list)
    room_id: str = ""
    room_title: str = ""
    room_description: str = ""
    room_exits: list[str] = field(default_factory=list)
    room_characters: list[str] = field(default_factory=list)


class CharAgent(Character):
    """An agent-based character that can interact with the world autonomously."""
    
    type: Literal["CharAgent"] = Field(default="CharAgent")
    
    brief_description: str = Field(
        description="A brief description of what a player might see if they looked at the character. This should be in the third person.",
        default=""
    )
    internal_description: str = Field(
        description="A short description of the character. This should be in the second person. 'You are ...'",
        default=""
    )
    internal_personality: str = Field(
        description="A paragraph describing the character's personality. This should be in the second person. 'You are ...'",
        default=""
    )
    internal_goals: str = Field(
        description="The character's goals and motivations. This should be in the second person, e.g. 'You are trying ...'. Only the character knows their own goals.",
        default=""
    )
   
    def init(self, world: "World"):
        # Initialize attributes with underscore prefix to exclude from serialization
        self._world = world
        self._state = CharAgentState()
        self._state.events.append(CharEvent(idle_until_timestamp=time.time()+5))
        
        # Initialize room info
        self._update_room_info()

    def _update_room_info(self) -> None:
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

        last_event = self._state.events[-1]
        current_time = time.time()
        
        # Check if we're still in idle period
        if current_time < last_event.idle_until_timestamp:
            time_left = last_event.idle_until_timestamp - current_time
            print(f"[DEBUG] {self.name}: Still idling for {time_left:.1f} more seconds")
            return  # Do nothing during idle time

        # Idle period complete, run the agent to decide next action
        print(f"[DEBUG] {self.name}: Deciding next action")
   
        # Debug the incoming message
        if last_event.message:
            print(f"[DEBUG] {self.name}: Received message: {last_event.message.model_dump()}")
        
        # Create the prompt based on the trigger reason
        prompt = "Decide what to do next."

        # Run the agent
        result = await char_agent_actor.run(prompt, deps=self)
        decision:ActionDecision = result.data
        
        # Debug the response from the agent
        print(f"[DEBUG] {self.name}: Agent response: {decision}")
        
        if decision.action:
            await self._world.process_character_action(self, decision.action)
            # Update room info after the action (especially important for movement)
            self._update_room_info()

        # Check if room has any players, if not add extra idle time
        idle_time = decision.idle_duration
        room = self._world.get_character_room(self.id)
        if room and not self._world.room_has_players(room.id):
            print(f"[DEBUG] {self.name}: No players in room, adding extra {empty_room_extra_idle} seconds")
            idle_time += empty_room_extra_idle

        event = CharEvent(
            timestamp=time.time(),
            action=decision.action,
            message=None,
            idle_until_timestamp=time.time() + idle_time 
        )
        self._state.events.append(event)

    
    async def send_message(self, msg: MessageToCharacter) -> None:
        """
        Send a message to the agent to be processed on the next tick.
        """
        # Debug incoming messages
        print(f"[DEBUG] {self.name}.send_message called: {msg.model_dump()}")
        
        # Store the message in the state to be handled on next tick
        # Only process messages if they come from a different user and not the server
        if msg.msg_src and msg.msg_src != self.name:
            self._state.events.append(
                    CharEvent(
                        timestamp=time.time(),
                        action=None,
                        message=msg,
                        idle_until_timestamp=time.time()  # Process immediately
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
You are {char_agent.name}. {char_agent.internal_description}

{char_agent.internal_personality}

{char_agent.internal_goals}

You must choose an action based on your current situation:
1. Say something to others in the room using the Say action
2. Perform an emote (like "waves" or "looks around") using the Emote action
3. Move to a connected room using the Move action
4. Idle for a period of time when appropriate

When deciding what to do:
- Consider your current location and who else is present
- Respond appropriately to messages from other characters
- Engage and explore
- Be yourself

Every action should include an idle duration (how long to pause before the next action):
- Short duration (5-20 seconds) for quick responses or when actively engaged
- Medium duration (20-45 seconds) for normal activities
- Long duration (45-90 seconds) for when less active or when little is happening

Return your decision as a structured action object, either:
- A CharacterAction (for say, emote, or move) plus an idle duration
- An IdleAction (to wait quietly for a while)

Be thoughtful about your choices based on the context provided.
        """


@char_agent_actor.system_prompt
def context_prompt(ctx) -> str:
    char_agent:CharAgent = ctx.deps
    state:CharAgentState = char_agent._state

    result = f"""\
You are currently located at "{state.room_title}": {state.room_description}

You can see the following exits: {", ".join(state.room_exits)}

You can see the following people, characters, or entities: {", ".join(state.room_characters)}

This is the recent history:
"""
    
    # Include the last 5 events (or fewer if there aren't that many)
    # Start from most recent and work backwards
    recent_events = state.events[-10:] 
    formatted_events = []
    current_time = time.time()
    
    for event in recent_events:
        seconds_ago = int(current_time - event.timestamp)
        
        if event.message:
            # Format message events
            formatted_events.append(f"[{seconds_ago} seconds ago] {event.message.msg_src} said to you: \"{event.message.message}\"")
        elif event.action:
            # Format action events
            if hasattr(event.action, 'action_type'):
                if event.action.action_type == "say":
                    formatted_events.append(f"[{seconds_ago} seconds ago] You said: \"{event.action.message}\"")
                elif event.action.action_type == "emote":
                    formatted_events.append(f"[{seconds_ago} seconds ago] You {event.action.message}")
                elif event.action.action_type == "move":
                    formatted_events.append(f"[{seconds_ago} seconds ago] You moved to {event.action.direction}")
    
    # Reverse the events so most recent is last
    formatted_events.reverse()
    
    # Add the formatted events to the result
    if formatted_events:
        result += "\n" + "\n".join(formatted_events)
    else:
        result += "\nNo recent activity."
   
    print(result)
    return result


