# LLM Mud

A simple text-based game engine inspired by Multi-User Dungeons (MUDs). This proof-of-concept focuses on implementing core game world functionality, specifically rooms and navigation between them.


## Project Structure
- `save.py`: Handles serialization and deserialization of game world data
- `room.py`: Implements core Room functionality
- `world.py`: Manages the game world and relationships between rooms
- `loop.py`: Contains the main game loop and command processing

## Design Philosophy

This project emphasizes:
- Clear separation of concerns between data and behavior
- Type safety using Python type hints
- Simple, extensible architecture that can grow with new features

## Future Considerations

While not yet implemented, the architecture is designed to eventually support:
- Characters (players and NPCs)
- Items and inventories
- More complex room connections
- Game state persistence
