from pydantic import BaseModel, Field
from pathlib import Path


class RoomDescription(BaseModel):
    id: str = Field(
        description="Typically the title, but with spaces replaced with underscores, all lowercase, etc"
    )
    title: str = Field(description="The name/title of the room")
    brief_description: str = Field(
        description="A short description shown when entering the room"
    )
    long_description: str = Field(
        description="A detailed description shown when examining the room"
    )


class RoomExit(BaseModel):
    destination_id: str = Field(
        description="The room id for the destination"
    )
    exit_description: str = Field(
        description="A short, one line or less, description of the exit as viewed from the current location."
    )
    exit_name: str = Field(
        description="A descriptive name for the exit, to be used by the player when navigating"
    )


class RoomExits(BaseModel):
    exits: list[RoomExit] = Field(
        description="A list of exits that connect this room to other rooms."
    )

class RoomDescriptionWithExits(RoomDescription):
    exits: list[RoomExit] = Field(
        description="A list of exits that connect this room to other rooms."
    )


class WorldDescription(BaseModel):
    title: str = Field(description="The title of the game world")
    description: str = Field(description="The description of the game world. Should be approximately one brief paragraph.")
    story_titles: list[str] = Field(
        description="A list of engaging story titles set in this world, each fitting the world's theme",
        default_factory=list
    )


class CharacterDescription(BaseModel):
    """An agent-based character that can interact with the world autonomously."""
    id: str
    name: str
    appearance: str = Field(
        description="A brief description of the character's appearance. Told in the third person.",
        default=""
    )
    description: str = Field(
        description="A detailed character description told in the second person. Includes personality, goals, and motivations.",
        default=""
    )


class StoryWorldComponents(BaseModel):
    """Characters and key locations extracted from a story."""
    characters: list[CharacterDescription] = Field(
        description="List of characters that appear in the story",
        default_factory=list
    )
    locations: list[RoomDescription] = Field(
        description="List of important locations where major plot points take place in the story",
        default_factory=list
    )
    character_locations: dict[str, list[str]] = Field(
        description="For each character id, a list of location ids you will likely find the character",
        default_factory=dict
    )
    location_connections: dict[str, list[str]] = Field(
        description="For each location id, a list of location ids which are connected",
        default_factory=dict
    )


class WorldMergeMapping(BaseModel):
    """Mapping instructions for merging multiple story worlds into one cohesive world."""
    
    duplicate_locations: dict[str, str] = Field(
        description="Mapping of duplicate location IDs to their canonical ID. Key: old_location_id, Value: new_location_id to be used",
        default_factory=dict
    )
    
    new_locations: list[RoomDescription] = Field(
        description="List of new locations useful for merging the many stories together",
        default_factory=list
    )
    
    new_connections: dict[str, list[str]] = Field(
        description="New connections to add between locations to ensure all stories are connected. For each location id, a list of location ids which are new connections.",
        default_factory=dict
    )
    starting_room_id: str = Field(
        description="The ID of the room that should be the starting point for players"
    )


class WorldImprovementPlan(BaseModel):
    """Plan for improving a world's design by preventing locations from having too many connections."""
    
    new_locations: list[RoomDescription] = Field(
        description="New intermediate locations to help distribute connections more evenly",
        default_factory=list
    )
    
    updated_connections: dict[str, list[str]] = Field(
        description="Updated connections between locations. For each location id, a list of location ids it connects to.",
        default_factory=dict
    )


class WorldDesign(BaseModel):
    """
    A complete design for a world, representing the intermediate stage between
    the initial world description and the final World object with Room instances.
    """
    world_description: WorldDescription = Field(
        description="The overall description of the game world"
    )
    locations: list[RoomDescriptionWithExits] = Field(
        description="List of all locations in the world with their exits",
        default_factory=list
    )
    characters: list[CharacterDescription] = Field(
        description="List of all characters in the world",
        default_factory=list
    )
    character_locations: dict[str, list[str]] = Field(
        description="For each character id, a list of location ids you will likely find the character",
        default_factory=dict
    )
    starting_room_id: str = Field(
        description="The ID of the room that should be the starting point for players"
    )
