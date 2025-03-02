import asyncio
from pydantic import BaseModel, Field, model_validator
from typing import Annotated
from pathlib import Path
from collections import defaultdict

from mad.core.character import Character
from mad.core.character_action import CharacterAction
from mad.core.player import Player
from mad.core.char_agent import CharAgent
from mad.core.location import Location
from mad.networking.messages import (
    BaseMessage, LocationMessage, SystemMessage, 
    DialogMessage, EmoteMessage, MovementMessage, ExitDescription
)

CharType = Annotated[Player | CharAgent, Field(discriminator='type')]


class World(BaseModel):
    """
    Game world containing locations, characters, and game state.
    """

    # Identity and description
    title: str
    description: str

    # Content
    locations: dict[str, Location] = Field(default_factory=dict)
    starting_location_id: str | None = None

    # Runtime state
    location_characters: dict[str, list[str]] = Field(
        default_factory=lambda: {}
    )  # location_id -> [character_ids]
    characters: dict[str, CharType] = Field(
        default_factory=dict,
    )  # character_id -> Character object

    @model_validator(mode='after')
    def init(self):
        for char_id, char in self.characters.items():
            if isinstance(char, CharAgent):
                print(f"Initializing {char_id}")
                char.init(self)
        return self

    def create_location(self, location: Location) -> None:
        """Add a location to the world."""
        self.locations[location.id] = location

    def set_starting_location(self, location_id: str) -> None:
        """Set the starting location for new players."""
        if location_id not in self.locations:
            raise ValueError(f"Location '{location_id}' does not exist")
        self.starting_location_id = location_id

    def get_character_location(self, character_id: str) -> Location | None:
        """Get the location a character is currently in."""
        for location_id, characters in self.location_characters.items():
            if character_id in characters:
                return self.locations.get(location_id)
        return None
        
    def location_has_players(self, location_id: str) -> bool:
        """Check if a location has any player characters.
        
        Args:
            location_id: The ID of the location to check
            
        Returns:
            True if there are players in the location, False otherwise
        """
        from mad.core.player import Player
        
        if location_id not in self.location_characters:
            return False
            
        for char_id in self.location_characters[location_id]:
            if char_id in self.characters and isinstance(self.characters[char_id], Player):
                return True
                
        return False

    async def move_character(self, character_id: str, direction: str) -> Location | None:
        """Move a character in a direction if possible."""
        current_location = self.get_character_location(character_id)
        if not current_location:
            return None

        # Get the ID of the destination location
        # First check if the exit name matches any in the exit_objects list
        destination_id = None
        for exit in current_location.exit_objects:
            if exit.exit_name == direction:
                destination_id = exit.destination_id
                break
        
        # As a backup, check the old-style exits dictionary
        if not destination_id:
            destination_id = current_location.exits.get(direction)
            
        if not destination_id:
            return None

        # Get the destination location
        destination_location = self.locations.get(destination_id)

        if not destination_location:
            return None

        # Move the character
        if not current_location.id in self.location_characters:
            self.location_characters[current_location.id] = []
        if not destination_location.id in self.location_characters:
            self.location_characters[destination_location.id] = []

        # Get character name for emote messages
        character = self.characters.get(character_id)
        character_name = character.name if character else "Someone"

        # Store previous location for all characters
        if character:
            character.previous_location_id = current_location.id
            character.previous_location_title = current_location.title

        if character_id in self.location_characters[current_location.id]:
            # Broadcast departure message to current location before removing character
            await self.broadcast_to_location(
                current_location.id, 
                "emote", 
                "leaves.", 
                msg_src=character_name,
                exclude_character_id=character_id
            )
            self.location_characters[current_location.id].remove(character_id)
            
        # Add character to destination location
        self.location_characters[destination_location.id].append(character_id)
        
        # Broadcast arrival message to destination location
        await self.broadcast_to_location(
            destination_location.id, 
            "emote", 
            "arrives.", 
            msg_src=character_name,
            exclude_character_id=character_id
        )

        return destination_location

    # Character management
    async def login_player(self, player_name: str) -> Player:
        """Create and place a new player in the starting location."""
        if not self.starting_location_id:
            raise RuntimeError("No starting location set")

        player = Player(player_name)

        # Add player to starting location
        if not self.starting_location_id in self.location_characters:
            self.location_characters[self.starting_location_id] = []
        self.location_characters[self.starting_location_id].append(player.id)

        # Add player to the characters dictionary
        self.characters[player.id] = player
        
        # Broadcast arrival message to starting location
        await self.broadcast_to_location(
            self.starting_location_id, 
            "emote", 
            "arrives.", 
            msg_src=player.name,
            exclude_character_id=player.id
        )

        # Welcome message with world info
        welcome_message = f"Welcome to {self.title}!"
        # Send system message with world info
        await player.send_message(
            SystemMessage(
                content=self.description,
                title=welcome_message,
                severity="info"
            )
        )

        # Show current location
        current_location = self.get_character_location(player.id)

        # Get characters in the location excluding the player
        characters_in_location = self.get_characters_in_location(current_location.id, player.id)
        
        # Send location description to player
        await player.send_message(
            LocationMessage(
                title=current_location.title,
                description=current_location.brief_describe(),
                characters_present=characters_in_location,
                exits=[
                    ExitDescription(
                        name=exit.exit_name,
                        description=exit.exit_description,
                        destination_id=exit.destination_id
                    ) for exit in current_location.exit_objects
                ]
            )
        )

        return player

    async def logout_player(self, player: Player) -> None:
        """Remove a player from the world."""
        # Broadcast departure message before removing
        location = self.get_character_location(player.id)
        if location and player.id in self.location_characters[location.id]:
            await self.broadcast_to_location(
                location.id, 
                "emote", 
                "leaves.", 
                msg_src=player.name,
                exclude_character_id=player.id
            )
            self.location_characters[location.id].remove(player.id)

        # Remove from characters dictionary
        if player.id in self.characters:
            del self.characters[player.id]

    # Game loop and action processing
    async def tick(self) -> None:
        """Process one game tick for all characters."""
        # Only tick actual character objects from our characters dict
        if self.characters:
            # Use return_exceptions=True to prevent one failure from stopping all ticks
            results = await asyncio.gather(
                *(character.tick() for character in self.characters.values()),
                return_exceptions=True
            )
            
            # Handle any exceptions that occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    import traceback
                    character_id = list(self.characters.keys())[i]
                    character_name = self.characters[character_id].name
                    print(f"Error in tick() for character {character_name} ({character_id}): {result}")
                    print(f"Stacktrace for {character_name}:")
                    traceback.print_exception(type(result), result, result.__traceback__)
                    # Consider additional error handling like removing crashed characters
                    # or sending admin notifications for persistent issues

    async def process_character_action(
        self, character: Character, action: CharacterAction
    ) -> None:
        """Process a character's action."""
        
        if action.action_type == "move":
            location = await self.move_character(character.id, action.direction)
            if location is None:
                await character.send_message(
                    SystemMessage(
                        content="You can't go that way.",
                        title="Error",
                        severity="error"
                    )
                )
            else:
                # Get characters in the location excluding the current character
                characters_in_location = self.get_characters_in_location(location.id, character.id)
                
                # Send location description with all metadata
                exits_list = []
                for exit in location.exit_objects:
                    exit_desc = exit.exit_description
                    
                    # Check if this exit leads back to the previous location
                    if (character.previous_location_id and 
                        exit.destination_id == character.previous_location_id):
                        exit_desc += f" (Return to \"{character.previous_location_title}\")"
                    
                    exits_list.append(
                        ExitDescription(
                            name=exit.exit_name,
                            description=exit_desc,
                            destination_id=exit.destination_id
                        )
                    )
                
                await character.send_message(
                    LocationMessage(
                        title=location.title,
                        description=location.brief_describe(),
                        characters_present=characters_in_location,
                        exits=exits_list
                    )
                )
        elif action.action_type == "look":
            location = self.get_character_location(character.id)
            if location:
                # Get characters in the location excluding the current character
                characters_in_location = self.get_characters_in_location(location.id, character.id)
                
                # Send detailed location description
                exits_list = []
                for exit in location.exit_objects:
                    exit_desc = exit.exit_description
                    
                    # Check if this exit leads back to the previous location
                    if (character.previous_location_id and 
                        exit.destination_id == character.previous_location_id):
                        exit_desc += f" (Return to \"{character.previous_location_title}\")"
                    
                    exits_list.append(
                        ExitDescription(
                            name=exit.exit_name,
                            description=exit_desc,
                            destination_id=exit.destination_id
                        )
                    )
                
                await character.send_message(
                    LocationMessage(
                        title=location.title,
                        description=location.describe(),  # Full description for "look"
                        characters_present=characters_in_location,
                        exits=exits_list
                    )
                )
        elif action.action_type in ("say", "emote") and action.message:
            location = self.get_character_location(character.id)
            if location:
                await self.broadcast_to_location(
                    location.id, 
                    action.action_type, 
                    action.message, 
                    msg_src=character.name
                )

    def get_characters_in_location(self, location_id: str, exclude_character_id: str | None = None) -> list[str]:
        """Get names of characters in a specific location.
        
        Args:
            location_id: The ID of the location to check
            exclude_character_id: Optional character ID to exclude from the list
            
        Returns:
            A list of character names in the location
        """
        characters_in_location = []
        if location_id in self.location_characters:
            for char_id in self.location_characters[location_id]:
                if (exclude_character_id is None or char_id != exclude_character_id) and char_id in self.characters:
                    characters_in_location.append(self.characters[char_id].name)
        return characters_in_location

    # Note: Character formatting is now handled by the frontend using the characters_present list

    async def broadcast_to_location(
        self, 
        location_id: str, 
        action_type: str,  # "say" or "emote"
        message: str, 
        msg_src: str | None = None,
        exclude_character_id: str | None = None
    ) -> None:
        """Send a message to all characters in a specific location.
        
        Args:
            location_id: The ID of the location to broadcast to
            action_type: The type of action ("say" or "emote")
            message: The message content
            msg_src: The source of the message (character name)
            exclude_character_id: Optional character ID to exclude from broadcast
        """
        if location_id not in self.location_characters:
            return
        
        for character_id in self.location_characters[location_id]:
            if exclude_character_id and character_id == exclude_character_id:
                continue
                
            character = self.characters.get(character_id)
            if character and msg_src:
                try:
                    # Create appropriate message type
                    if action_type == "say":
                        await character.send_message(
                            DialogMessage(
                                content=message,
                                from_character_name=msg_src
                            )
                        )
                    elif action_type == "emote":
                        await character.send_message(
                            EmoteMessage(
                                action=message,
                                from_character_name=msg_src
                            )
                        )
                except Exception as e:
                    print(f"Error sending message to {character_id}: {e}")
    
    # Persistence
    def save(self, filepath: str | Path) -> None:
        """Save world state to a JSON file"""
        Path(filepath).write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, filepath: str | Path) -> "World":
        """
        Load world data from a JSON file and construct a World instance.

        Args:
            filepath: Path to the JSON world file

        Returns:
            A fully constructed World instance
        """
        return cls.model_validate_json(Path(filepath).read_text())
