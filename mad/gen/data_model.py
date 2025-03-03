from pydantic import BaseModel, Field
from pathlib import Path


class LocationDescription(BaseModel):
    id: str = Field(
        description="Typically the title, but with spaces replaced with underscores, all lowercase, etc"
    )
    is_key: bool = Field(description="Is this a key location in the story, and not just a connector location")
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


class WorldDesign(BaseModel):
    """
    A complete design for a world, representing the intermediate stage between
    the initial world description and the final World object with Location instances.
    """
    world_description: WorldDescription = Field(
        description="The overall description of the game world"
    )
    locations: list[LocationDescription] = Field(
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
    location_connections: dict[str, list[str]] = Field(
        description="For each location id, a list of destination ids accessible",
        default_factory=dict
    )
    location_exits: dict[str, list[LocationExit]] = Field(
        description="For each location id, a list of exits",
        default_factory=dict
    )
    starting_location_id: str = Field(
        description="The ID of the location that should be the starting point for players",
        default="" # TODO FIX
    )

    
    def find_location_by_id(self, location_id: str) -> LocationDescription | None:
        """
        Find a location in this world by its ID.
        
        Args:
            location_id: The ID of the location to find
            
        Returns:
            LocationDescription object if found, None otherwise
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
        if source_id not in self.location_connections:
            self.location_connections[source_id] = []

        if dest_id not in self.location_connections:
            self.location_connections[dest_id] = []

        if source_id not in self.location_connections[dest_id]:
            self.location_connections[dest_id].append(source_id)
       
        if dest_id not in self.location_connections[source_id]:
            self.location_connections[source_id].append(dest_id)

            
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
        
        # Remove exits to this location
        for src_id, exits in list(self.location_exits.items()):
            if src_id == location_id:
                continue
                
            # Filter out exits to the removed location
            updated_exits = [exit for exit in exits if exit.destination_id != location_id]
            if len(updated_exits) != len(exits):
                locations_connecting_to_location.append(src_id)
                self.location_exits[src_id] = updated_exits
        
        # Remove location from connections
        for src_id, dest_ids in list(self.location_connections.items()):
            if src_id == location_id:
                del self.location_connections[src_id]
            elif location_id in dest_ids:
                self.location_connections[src_id] = [x for x in dest_ids if x != location_id]
                if src_id not in locations_connecting_to_location:
                    locations_connecting_to_location.append(src_id)
        
        # Remove from location_exits
        if location_id in self.location_exits:
            del self.location_exits[location_id]
        
        # Update character locations
        for char_id, loc_ids in self.character_locations.items():
            self.character_locations[char_id] = [
                loc_id for loc_id in loc_ids if loc_id != location_id
            ]
        
        # Update starting location if needed
        if self.starting_location_id == location_id:
            self.starting_location_id = ""  # Reset to empty
        
        # Delete the location
        self.locations = [loc for loc in self.locations if loc.id != location_id]
        
        return locations_connecting_to_location
        
    def add_location(self, location: LocationDescription) -> LocationDescription:
        """
        Add a single location to the world design.
        
        Args:
            location: The LocationDescription to add
            
        Returns:
            The newly added LocationDescription object
        
        Raises:
            ValueError: If a location with the same ID already exists
        """
        # Check if location with this ID already exists
        if any(loc.id == location.id for loc in self.locations):
            raise ValueError(f"Location with ID '{location.id}' already exists in the world")
        
        self.locations.append(location)
        self.location_exits[location.id]=[]
        self.location_connections[location.id]=[]
        
        
    def rename_location_id(self, old_id: str, new_id: str) -> bool:
        """
        Rename a location's ID and update all references to that location.
        
        This method updates:
        1. The location's own ID
        2. All exits that reference this location
        3. Character location references
        4. Starting location ID if it matches
        
        Args:
            old_id: The current ID of the location
            new_id: The new ID to assign to the location
            
        Returns:
            True if the location was found and renamed, False otherwise
        """
        # Find the location
        location = self.find_location_by_id(old_id)
        if not location:
            return False
        
        # Update the location's ID
        location.id = new_id
        
        # Update location exits if they exist
        if old_id in self.location_exits:
            self.location_exits[new_id] = self.location_exits[old_id]
            del self.location_exits[old_id]
        
        # Update location connections if they exist
        if old_id in self.location_connections:
            self.location_connections[new_id] = self.location_connections[old_id]
            del self.location_connections[old_id]

        # Update references to this location in other locations' connections
        for src_id, dest_ids in self.location_connections.items():
            if old_id in dest_ids:
                self.location_connections[src_id] = [x for x in dest_ids if x!=old_id] + [new_id]

        # Update character locations
        for char_id, loc_ids in self.character_locations.items():
            self.character_locations[char_id] = [
                new_id if loc_id == old_id else loc_id for loc_id in loc_ids
            ]
        
        # Update starting location if needed
        if self.starting_location_id == old_id:
            self.starting_location_id = new_id
            
        return True

    def add_design(self, other_design: "WorldDesign"):
        """
            Adds all the locations and characters from other design into this design
        """
        self.locations.extend(other_design.locations)
        self.characters.extend(other_design.characters)
        self.character_locations.update(other_design.character_locations)
        self.location_connections.update(other_design.location_connections)
        self.location_exits.update(other_design.location_exits)

