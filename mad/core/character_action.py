from pydantic import BaseModel, Field
from typing import Literal


class CharacterAction(BaseModel):
    """
    A character action.
    """

    action_type: Literal["move", "look", "say", "emote"]
    direction: str | None = Field(
        description="The direction to move to, if applicable.", default=None
    )
    message: str | None = Field(
        description="The message to say or emote action to perform.", default=None
    )
