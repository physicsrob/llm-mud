import asyncio
from pydantic import BaseModel, Field
from pathlib import Path
from collections import defaultdict

from mad.core.character import Character
from mad.core.character_action import CharacterAction
from mad.core.player import Player
from mad.core.room import Room
from mad.networking.messages import MessageToCharacter


class World(BaseModel):
    """
    Game world containing rooms, characters, and game state.
    """

    # Identity and description
    title: str
    brief_description: str
    long_description: str
    other_details: str = ""

    # Content
    rooms: dict[str, Room] = Field(default_factory=dict)
    starting_room_id: str | None = None

    # Runtime state
    room_characters: dict[str, list[str]] = Field(
        default_factory=lambda: {}
    )  # room_id -> [character_ids]
    characters: dict[str, Character] = Field(
        default_factory=dict
    )  # character_id -> Character object

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
        character_name = self.characters.get(character_id).name if character_id in self.characters else "Someone"

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
                    character_id = list(self.characters.keys())[i]
                    character_name = self.characters[character_id].name
                    print(f"Error in tick() for character {character_name} ({character_id}): {result}")
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
                    MessageToCharacter(
                        title="Error",
                        title_color="red",
                        message="You can't go that way.",
                        message_color="red"
                    )
                )
            else:
                await character.send_message(
                    MessageToCharacter(
                        title=room.title,
                        title_color="green",
                        message=room.brief_describe()
                    )
                )
        elif action.action_type == "look":
            room = self.get_character_room(character.id)
            if room:
                # Get characters in the room excluding the current character
                characters_in_room = []
                if room.id in self.room_characters:
                    for char_id in self.room_characters[room.id]:
                        if char_id != character.id and char_id in self.characters:
                            characters_in_room.append(self.characters[char_id].name)
                
                # Build the room description including characters
                room_desc = room.describe()
                if characters_in_room:
                    if len(characters_in_room) == 1:
                        room_desc += f"\n\nYou see {characters_in_room[0]} here."
                    else:
                        last_char = characters_in_room.pop()
                        chars_text = f"{', '.join(characters_in_room)} and {last_char}"
                        room_desc += f"\n\nYou see {chars_text} here."
                
                # Set scroll to true for room descriptions
                await character.send_message(
                    MessageToCharacter(
                        title=room.title,
                        title_color="green",
                        message=room_desc,
                        scroll=True
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
                    formatted_message = ""
                    message_color = None
                    
                    # Format based on action type
                    if action_type == "say":
                        formatted_message = f"{msg_src} says: {message}"
                        message_color = "cyan"
                    elif action_type == "emote":
                        formatted_message = f"{msg_src} {message}"
                        message_color = "magenta"
                    
                    await character.send_message(
                        MessageToCharacter(
                            message=formatted_message,
                            message_color=message_color,
                            msg_src=msg_src
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
