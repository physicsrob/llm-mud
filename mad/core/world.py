import asyncio
from pydantic import BaseModel, Field, model_validator
from typing import Annotated
from pathlib import Path
from collections import defaultdict

from mad.core.character import Character
from mad.core.character_action import CharacterAction
from mad.core.player import Player
from mad.core.char_agent import CharAgent
from mad.core.room import Room
from mad.networking.messages import (
    BaseMessage, RoomMessage, SystemMessage, 
    DialogMessage, EmoteMessage, MovementMessage, ExitDescription
)

CharType = Annotated[Player | CharAgent, Field(discriminator='type')]


class World(BaseModel):
    """
    Game world containing rooms, characters, and game state.
    """

    # Identity and description
    title: str
    description: str

    # Content
    rooms: dict[str, Room] = Field(default_factory=dict)
    starting_room_id: str | None = None

    # Runtime state
    room_characters: dict[str, list[str]] = Field(
        default_factory=lambda: {}
    )  # room_id -> [character_ids]
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

    def create_room(self, room: Room) -> None:
        """Add a room to the world."""
        self.rooms[room.id] = room

    def set_starting_room(self, room_id: str) -> None:
        """Set the starting room for new players."""
        if room_id not in self.rooms:
            raise ValueError(f"Room '{room_id}' does not exist")
        self.starting_room_id = room_id

    def get_character_room(self, character_id: str) -> Room | None:
        """Get the room a character is currently in."""
        for room_id, characters in self.room_characters.items():
            if character_id in characters:
                return self.rooms.get(room_id)
        return None
        
    def room_has_players(self, room_id: str) -> bool:
        """Check if a room has any player characters.
        
        Args:
            room_id: The ID of the room to check
            
        Returns:
            True if there are players in the room, False otherwise
        """
        from mad.core.player import Player
        
        if room_id not in self.room_characters:
            return False
            
        for char_id in self.room_characters[room_id]:
            if char_id in self.characters and isinstance(self.characters[char_id], Player):
                return True
                
        return False

    async def move_character(self, character_id: str, direction: str) -> Room | None:
        """Move a character in a direction if possible."""
        current_room = self.get_character_room(character_id)
        if not current_room:
            return None

        # Get the ID of the destination room
        # First check if the exit name matches any in the exit_objects list
        destination_id = None
        for exit in current_room.exit_objects:
            if exit.exit_name == direction:
                destination_id = exit.destination_id
                break
        
        # As a backup, check the old-style exits dictionary
        if not destination_id:
            destination_id = current_room.exits.get(direction)
            
        if not destination_id:
            return None

        # Get the destination room
        destination_room = self.rooms.get(destination_id)

        if not destination_room:
            return None

        # Move the character
        if not current_room.id in self.room_characters:
            self.room_characters[current_room.id] = []
        if not destination_room.id in self.room_characters:
            self.room_characters[destination_room.id] = []

        # Get character name for emote messages
        character = self.characters.get(character_id)
        character_name = character.name if character else "Someone"

        # Store previous room for all characters
        if character:
            character.previous_room_id = current_room.id
            character.previous_room_title = current_room.title

        if character_id in self.room_characters[current_room.id]:
            # Broadcast departure message to current room before removing character
            await self.broadcast_to_room(
                current_room.id, 
                "emote", 
                "leaves.", 
                msg_src=character_name,
                exclude_character_id=character_id
            )
            self.room_characters[current_room.id].remove(character_id)
            
        # Add character to destination room
        self.room_characters[destination_room.id].append(character_id)
        
        # Broadcast arrival message to destination room
        await self.broadcast_to_room(
            destination_room.id, 
            "emote", 
            "arrives.", 
            msg_src=character_name,
            exclude_character_id=character_id
        )

        return destination_room

    # Character management
    async def login_player(self, player_name: str) -> Player:
        """Create and place a new player in the starting room."""
        if not self.starting_room_id:
            raise RuntimeError("No starting room set")

        player = Player(player_name)

        # Add player to starting room
        if not self.starting_room_id in self.room_characters:
            self.room_characters[self.starting_room_id] = []
        self.room_characters[self.starting_room_id].append(player.id)

        # Add player to the characters dictionary
        self.characters[player.id] = player
        
        # Broadcast arrival message to starting room
        await self.broadcast_to_room(
            self.starting_room_id, 
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

        # Show current room
        current_room = self.get_character_room(player.id)

        # Get characters in the room excluding the player
        characters_in_room = self.get_characters_in_room(current_room.id, player.id)
        
        # Send room description to player
        await player.send_message(
            RoomMessage(
                title=current_room.title,
                description=current_room.brief_describe(),
                characters_present=characters_in_room,
                exits=[
                    ExitDescription(
                        name=exit.exit_name,
                        description=exit.exit_description,
                        destination_id=exit.destination_id
                    ) for exit in current_room.exit_objects
                ]
            )
        )

        return player

    async def logout_player(self, player: Player) -> None:
        """Remove a player from the world."""
        # Broadcast departure message before removing
        room = self.get_character_room(player.id)
        if room and player.id in self.room_characters[room.id]:
            await self.broadcast_to_room(
                room.id, 
                "emote", 
                "leaves.", 
                msg_src=player.name,
                exclude_character_id=player.id
            )
            self.room_characters[room.id].remove(player.id)

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
            room = await self.move_character(character.id, action.direction)
            if room is None:
                await character.send_message(
                    SystemMessage(
                        content="You can't go that way.",
                        title="Error",
                        severity="error"
                    )
                )
            else:
                # Get characters in the room excluding the current character
                characters_in_room = self.get_characters_in_room(room.id, character.id)
                
                # Send room description with all metadata
                exits_list = []
                for exit in room.exit_objects:
                    exit_desc = exit.exit_description
                    
                    # Check if this exit leads back to the previous room
                    if (character.previous_room_id and 
                        exit.destination_id == character.previous_room_id):
                        exit_desc += f" (Return to \"{character.previous_room_title}\")"
                    
                    exits_list.append(
                        ExitDescription(
                            name=exit.exit_name,
                            description=exit_desc,
                            destination_id=exit.destination_id
                        )
                    )
                
                await character.send_message(
                    RoomMessage(
                        title=room.title,
                        description=room.brief_describe(),
                        characters_present=characters_in_room,
                        exits=exits_list
                    )
                )
        elif action.action_type == "look":
            room = self.get_character_room(character.id)
            if room:
                # Get characters in the room excluding the current character
                characters_in_room = self.get_characters_in_room(room.id, character.id)
                
                # Send detailed room description
                exits_list = []
                for exit in room.exit_objects:
                    exit_desc = exit.exit_description
                    
                    # Check if this exit leads back to the previous room
                    if (character.previous_room_id and 
                        exit.destination_id == character.previous_room_id):
                        exit_desc += f" (Return to \"{character.previous_room_title}\")"
                    
                    exits_list.append(
                        ExitDescription(
                            name=exit.exit_name,
                            description=exit_desc,
                            destination_id=exit.destination_id
                        )
                    )
                
                await character.send_message(
                    RoomMessage(
                        title=room.title,
                        description=room.describe(),  # Full description for "look"
                        characters_present=characters_in_room,
                        exits=exits_list
                    )
                )
        elif action.action_type in ("say", "emote") and action.message:
            room = self.get_character_room(character.id)
            if room:
                await self.broadcast_to_room(
                    room.id, 
                    action.action_type, 
                    action.message, 
                    msg_src=character.name
                )

    def get_characters_in_room(self, room_id: str, exclude_character_id: str | None = None) -> list[str]:
        """Get names of characters in a specific room.
        
        Args:
            room_id: The ID of the room to check
            exclude_character_id: Optional character ID to exclude from the list
            
        Returns:
            A list of character names in the room
        """
        characters_in_room = []
        if room_id in self.room_characters:
            for char_id in self.room_characters[room_id]:
                if (exclude_character_id is None or char_id != exclude_character_id) and char_id in self.characters:
                    characters_in_room.append(self.characters[char_id].name)
        return characters_in_room

    # Note: Character formatting is now handled by the frontend using the characters_present list

    async def broadcast_to_room(
        self, 
        room_id: str, 
        action_type: str,  # "say" or "emote"
        message: str, 
        msg_src: str | None = None,
        exclude_character_id: str | None = None
    ) -> None:
        """Send a message to all characters in a specific room.
        
        Args:
            room_id: The ID of the room to broadcast to
            action_type: The type of action ("say" or "emote")
            message: The message content
            msg_src: The source of the message (character name)
            exclude_character_id: Optional character ID to exclude from broadcast
        """
        if room_id not in self.room_characters:
            return
        
        for character_id in self.room_characters[room_id]:
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
