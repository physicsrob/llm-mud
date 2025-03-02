from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal, Any

class BaseMessage(BaseModel):
    """Base class for all messages to characters."""
    message_type: str = Field(description="Discriminator field for message type")

class ExitDescription(BaseModel):
    """Exit description for location messages."""
    name: str
    description: str
    destination_id: str

class LocationMessage(BaseMessage):
    """Location description message."""
    message_type: Literal["location"] = "location"
    title: str  # Location name
    description: str  # Location description
    characters_present: list[str] = Field(default_factory=list)
    exits: list[ExitDescription] = Field(default_factory=list)  # Detailed exit information

class DialogMessage(BaseMessage):
    """Character speech."""
    message_type: Literal["dialog"] = "dialog"
    content: str  # What was said
    from_character_name: str  # Who said it
    
class EmoteMessage(BaseMessage):
    """Character action/emote."""
    message_type: Literal["emote"] = "emote"
    action: str  # The action performed
    from_character_name: str  # Who performed it
    
class SystemMessage(BaseMessage):
    """System notification or information."""
    message_type: Literal["system"] = "system"
    content: str  # The system message
    title: str | None = None  # Optional title
    severity: Literal["info", "warning", "error"] = "info"

class MovementMessage(BaseMessage):
    """Character movement notification."""
    message_type: Literal["movement"] = "movement"
    character_name: str  # Character that moved
    direction: str | None = None  # Direction of movement if relevant
    action: str  # "arrives", "leaves", etc.
