from pydantic import BaseModel, Field
from pathlib import Path


class LocationDescription(BaseModel):
    id: str = Field(
        description="Typically the title, but with spaces replaced with underscores, all lowercase, etc"
    )
    title: str = Field(description="The name/title of the location")
    brief_description: str = Field(
        description="A short description shown when entering the location"
    )
    long_description: str = Field(
        description="A detailed description shown when examining the location"
    )


class LocationExit(BaseModel):
    destination_id: str = Field(
        description="The location id for the destination"
    )
    exit_description: str = Field(
        description="A short, one line or less, description of the exit as viewed from the current location."
    )
    exit_name: str = Field(
        description="A descriptive name for the exit, to be used by the player when navigating"
    )


class LocationExits(BaseModel):
    exits: list[LocationExit] = Field(
        description="A list of exits that connect this location to other locations."
    )

class LocationDescriptionWithExits(LocationDescription):
    exits: list[LocationExit] = Field(
        description="A list of exits that connect this location to other locations."
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
    locations: list[LocationDescription] = Field(
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
    
    new_locations: list[LocationDescription] = Field(
        description="List of new locations useful for merging the many stories together",
        default_factory=list
    )
    
    new_connections: dict[str, list[str]] = Field(
        description="New connections to add between locations to ensure all stories are connected. For each location id, a list of location ids which are new connections.",
        default_factory=dict
    )
    starting_location_id: str = Field(
        description="The ID of the location that should be the starting point for players"
    )


class LocationImprovementPlan(BaseModel):
    """Plan for improving a single location's design by preventing it from having too many connections."""
    
    new_locations: list[LocationDescription] = Field(
        description="Replacement locations to help distribute connections from this location",
        default_factory=list
    )
    updated_connections: dict[str, list[str]] = Field(
        description="Updated connections between locations. For each location id, a list of location ids it connects to.",
        default_factory=dict
    )


class WorldDesign(BaseModel):
    """
    A complete design for a world, representing the intermediate stage between
    the initial world description and the final World object with Location instances.
    """
    world_description: WorldDescription = Field(
        description="The overall description of the game world"
    )
    locations: list[LocationDescriptionWithExits] = Field(
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
    starting_location_id: str = Field(
        description="The ID of the location that should be the starting point for players"
    )
    
    def find_location_by_id(self, location_id: str) -> LocationDescriptionWithExits | None:
        """
        Find a location in this world by its ID.
        
        Args:
            location_id: The ID of the location to find
            
        Returns:
            LocationDescriptionWithExits object if found, None otherwise
        """
        for location in self.locations:
            if location.id == location_id:
                return location
        return None
        
    def ensure_bidirectional_exits(self, source_id: str, dest_id: str) -> None:
        """
        Ensures that a bidirectional exit exists between two locations.
        
        Args:
            source_id: The first location ID
            dest_id: The second location ID
        """
        source_location = self.find_location_by_id(source_id)
        dest_location = self.find_location_by_id(dest_id)
        
        if not source_location or not dest_location:
            return
        
        # Check if source has exit to dest
        source_to_dest_exists = any(exit.destination_id == dest_id for exit in source_location.exits)
        if not source_to_dest_exists:
            source_location.exits.append(LocationExit(
                destination_id=dest_id,
                exit_name=dest_location.title.lower(),
                exit_description=f"There is a path to {dest_location.title}"
            ))
        
        # Check if dest has exit to source
        dest_to_source_exists = any(exit.destination_id == source_id for exit in dest_location.exits)
        if not dest_to_source_exists:
            dest_location.exits.append(LocationExit(
                destination_id=source_id,
                exit_name=source_location.title.lower(),
                exit_description=f"There is a path to {source_location.title}"
            ))
            
    def remove_location(self, location_id: str) -> list[str]:
        """
        Remove a location and all its connections from the world design.
        
        This method removes the specified location and also removes all exits 
        to/from that location, maintaining world consistency.
        
        Args:
            location_id: ID of the location to remove
            
        Returns:
            List of IDs of locations that previously had exits to the removed location
        """
        # Find locations that connect to the location being removed
        locations_connecting_to_location = []
        for loc in self.locations:
            for exit in list(loc.exits):  # Use list to allow modification during iteration
                if exit.destination_id == location_id:
                    loc.exits.remove(exit)
                    locations_connecting_to_location.append(loc.id)
        
        # Delete the location
        self.locations = [loc for loc in self.locations if loc.id != location_id]
        
        return locations_connecting_to_location
        
    def add_location(self, location: LocationDescription) -> LocationDescriptionWithExits:
        """
        Add a single location to the world design.
        
        Args:
            location: The LocationDescription to add
            
        Returns:
            The newly added LocationDescriptionWithExits object
        
        Raises:
            ValueError: If a location with the same ID already exists
        """
        # Check if location with this ID already exists
        if any(loc.id == location.id for loc in self.locations):
            raise ValueError(f"Location with ID '{location.id}' already exists in the world")
        
        # Create a new LocationDescriptionWithExits
        location_with_exits = LocationDescriptionWithExits(
            id=location.id,
            title=location.title,
            brief_description=location.brief_description,
            long_description=location.long_description,
            exits=[]
        )
        
        # Add to locations list
        self.locations.append(location_with_exits)
        
        return location_with_exits
