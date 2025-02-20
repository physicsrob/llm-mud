import asyncio
from collections import defaultdict
from typing import Optional

from .character import Character
from .player import Player
from .room import Room
from .character_action import CharacterAction

class World:
    """
    Central game world manager responsible for game state and logic.
    Provides factory methods for world construction and APIs for state modification.
    """

    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self.characters: dict[str, Character] = {}
        self.room_characters: dict[str, list[Character]] = defaultdict(list)
        self.starting_room_id: Optional[str] = None

    # Factory methods for world construction
    def create_room(self, room_id: str, name: str, description: str) -> Room:
        """Create and register a new room in the world."""
        if room_id in self.rooms:
            raise ValueError(f"Room with id '{room_id}' already exists")
        
        room = Room(room_id, name, description)
        self.rooms[room_id] = room
        return room

    def connect_rooms(self, from_id: str, to_id: str, direction: str) -> None:
        """Create a one-way connection between rooms."""
        if from_id not in self.rooms or to_id not in self.rooms:
            raise ValueError("Both rooms must exist")
            
        self.rooms[from_id].add_exit(direction, self.rooms[to_id])

    def set_starting_room(self, room_id: str) -> None:
        """Set the starting room for new players."""
        if room_id not in self.rooms:
            raise ValueError(f"Room '{room_id}' does not exist")
        self.starting_room_id = room_id

    # Character management
    def login_player(self, player_name: str) -> Player:
        """Create and place a new player in the starting room."""
        if not self.starting_room_id:
            raise RuntimeError("No starting room set")
            
        player = Player(player_name, self)
        self.characters[player.id] = player
        self.room_characters[self.starting_room_id].append(player)
        return player

    def logout_player(self, player: Player) -> None:
        """Remove a player from the world."""
        room = self.get_character_room(player.id)
        if room:
            self.room_characters[room.id].remove(player)
        self.characters.pop(player.id)

    def get_character_room(self, character_id: str) -> Room | None:
        """Get the room a character is currently in."""
        character = self.characters[character_id]
        for room_id, characters in self.room_characters.items():
            if character in characters:
                return self.rooms[room_id]
        return None

    def move_character(self, character_id: str, direction: str) -> Room | None:
        """Move a character in a direction if possible."""
        character = self.characters[character_id]
        current_room = self.get_character_room(character_id)
        if not current_room:
            return None
            
        target_room = current_room.get_exit(direction)
        if not target_room:
            return None
            
        self.room_characters[current_room.id].remove(character)
        self.room_characters[target_room.id].append(character)
        return target_room

    # Game loop and action processing
    async def tick(self) -> None:
        """Process one game tick for all characters."""
        await asyncio.gather(
            *(character.tick() for character in self.characters.values())
        )

    async def process_character_action(
        self, character: Character, action: CharacterAction
    ) -> None:
        """Process a character's action."""
        if action.action_type == "move":
            room = self.move_character(character.id, action.direction)
            if room is None:
                await character.send_message("error", "You can't go that way.")
            else:
                await character.send_message("room", room.describe())
        elif action.action_type == "look":
            room = self.get_character_room(character.id)
            if room:
                await character.send_message("room", room.describe())

    def create_npc(self, npc_id: str, name: str, room_id: str, attributes: dict[str, any] = {}) -> Character:
        """Create and register a new NPC in the world."""
        if npc_id in self.characters:
            raise ValueError(f"Character with id '{npc_id}' already exists")
        
        # Note: You'll need to create an NPC class that inherits from Character
        npc = NPC(npc_id, name, self, attributes)
        self.characters[npc_id] = npc
        self.room_characters[room_id].append(npc)
        return npc
