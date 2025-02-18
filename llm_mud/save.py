from pathlib import Path
from pydantic import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from room import Room

class RoomData(BaseModel):
    name: str
    description: str
    exits: dict[str, str]

class WorldData(BaseModel):
    rooms: dict[str, RoomData]
    starting_room_id: str

def load_world_data(filepath: str | Path) -> tuple[dict[str, RoomData], str]:
    """
    Load world data from a JSON file and convert it to RoomData objects.
    
    Args:
        filepath: Path to the JSON world file
        
    Returns:
        Tuple of (Dictionary mapping room IDs to RoomData objects, starting room ID)
    """
    world_data = WorldData.model_validate_json(Path(filepath).read_text())
    return world_data.rooms, world_data.starting_room_id
