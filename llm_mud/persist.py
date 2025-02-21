from pathlib import Path
from pydantic import BaseModel
from .core.world import World, WorldDescription
from .core.room import RoomDescription

class SerializedRoom(BaseModel):
    description: RoomDescription
    exits: dict[str, str]

class SerializedWorld(BaseModel):
    description: WorldDescription
    rooms: dict[str, SerializedRoom]
    starting_room_id: str

def load_world(filepath: str | Path) -> World:
    """
    Load world data from a JSON file and construct a World instance.
    
    Args:
        filepath: Path to the JSON world file
        
    Returns:
        A fully constructed World instance
    """
    world_data = SerializedWorld.model_validate_json(Path(filepath).read_text())
    world = World(description=world_data.description)
    
    # First create all rooms
    for room_id, room_data in world_data.rooms.items():
        world.create_room(
            room_id=room_id,
            description=room_data.description
        )
    
    # Then connect them
    for room_id, room_data in world_data.rooms.items():
        for direction, target_room_id in room_data.exits.items():
            world.connect_rooms(room_id, target_room_id, direction)
            
    world.set_starting_room(world_data.starting_room_id)
    
    return world

def save_world(world: World, filepath: str | Path) -> None:
    """Save world state to a JSON file"""
    serialized_rooms = {
        room_id: SerializedRoom(
            description=room.description,
            exits={direction: dest.id for direction, dest in room.exits.items()}
        )
        for room_id, room in world.rooms.items()
    }
    
    serialized_world = SerializedWorld(
        description=world.description,
        rooms=serialized_rooms,
        starting_room_id=world.starting_room_id
    )
    
    Path(filepath).write_text(serialized_world.model_dump_json(indent=2)) 