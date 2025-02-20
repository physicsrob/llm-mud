from pathlib import Path
from pydantic import BaseModel
from .core.world import World

class RoomData(BaseModel):
    name: str
    description: str
    exits: dict[str, str]

class WorldData(BaseModel):
    rooms: dict[str, RoomData]
    starting_room_id: str

def load_world(filepath: str | Path) -> World:
    """
    Load world data from a JSON file and construct a World instance.
    
    Args:
        filepath: Path to the JSON world file
        
    Returns:
        A fully constructed World instance
    """
    world_data = WorldData.model_validate_json(Path(filepath).read_text())
    world = World()
    
    # First create all rooms
    for room_id, room_data in world_data.rooms.items():
        world.create_room(
            room_id=room_id,
            name=room_data.name,
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
    # TODO: Implement world serialization
    pass 