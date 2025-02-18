from pathlib import Path
from collections import defaultdict
from .character import Character
from .player import Player
from .room import Room
from .save import load_world_data

class World:
    """Manages the game world, including rooms and their relationships."""
    
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self.characters: dict[str, Character] = {}
        self.room_characters: dict[str, list[Character]] = defaultdict(list)
        self.starting_room_id: str | None = None
    
    def load_from_file(self, file_path: Path) -> None:
        """Load world data from a JSON file.
        
        Args:
            file_path: Path to the JSON world data file
        """
        # Load and create all rooms
        room_data, starting_room_id = load_world_data(file_path)
        self.rooms = {room_id: Room(room_id, data) for room_id, data in room_data.items()}
        
        # Set starting room
        self.starting_room_id = starting_room_id
        
        # Connect rooms by setting up their exits to point to other Room objects
        for room_id, data in room_data.items():
            # Get the original exit data which contains room IDs
            exit_data = {k: v for k, v in data.exits.items()}
            # Clear the exits dict since it will now store Room references
            # Set up exits with Room objects
            for direction, target_room_id in exit_data.items():
                if target_room_id in self.rooms:
                    self.rooms[room_id].exits[direction] = self.rooms[target_room_id]
                else:
                    print(f"Room {target_room_id} not found")
    
    def get_room(self, room_id: str) -> Room | None:
        """Get a room by its ID.
        
        Args:
            room_id: The ID of the room to retrieve
            
        Returns:
            The Room object if found, None otherwise
        """
        return self.rooms.get(room_id)
    
    def login_player(self, player_name: str) -> Player:
        player = Player(player_name, self)
        self.characters[player.id] = player
        self.room_characters[self.starting_room_id].append(player)
        return player
    
    def logout_player(self, player: Player) -> None:
        room = self.get_character_room(player.id)
        self.room_characters[room.id].remove(player)
        self.characters.pop(player.id)
    
    def get_character_room(self, character_id: str) -> Room | None:
        character = self.characters[character_id]
        for room_id, characters in self.room_characters.items():
            if character in characters:
                return self.rooms[room_id]
        return None

    def move_character(self, character_id: str, direction: str) -> Room | None:
        character = self.characters[character_id]
        current_room = self.get_character_room(character_id)
        print(f"Current room: {current_room}")
        if current_room is None:
            return
        print(f"Current room exits: {current_room.exits}")
        if direction not in current_room.exits:
            print("No exit in that direction")
            return
        target_room = current_room.exits[direction]
        self.room_characters[current_room.id].remove(character)
        self.room_characters[target_room.id].append(character)
        return target_room
    
