# LLM Mud

A text-based game engine inspired by Multi-User Dungeons (MUDs). The goal of this project is to explore the use of LLMs to power a text-based game.

## Features

- Multi-player support with client-server architecture
- Real-time player interactions and movement
- Dynamic world loading from JSON configuration
- Command parsing system for player actions
- Character system with basic attributes
- Room-based navigation and exploration

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-mud.git
cd llm-mud

# Install dependencies
pip install -e .
```

## Usage

You can run the game in different modes:

```bash
# Start in development mode (single player)
llmmud dev

# Start the server
llmmud server

# Start a client
llmmud client
```

## Project Structure

- `server.py`: Implements the game server and manages client connections
- `client.py`: Handles client-side networking and game state
- `cli.py`: Command-line interface for player interaction
- `world.py`: Manages the game world, rooms, and game state
- `room.py`: Defines room structure and properties
- `character.py`: Base character class for players and NPCs
- `player.py`: Player-specific functionality and state
- `command_parser.py`: Processes and validates player commands
- `character_action.py`: Defines available character actions
- `messages.py`: Message types for client-server communication
- `config.py`: Configuration settings
- `save.py`: Game state serialization and persistence

## Design Philosophy

This project emphasizes:
- Clean separation between client and server responsibilities
- Type safety using Python type hints
- Modular architecture for easy feature extension
- Real-time multiplayer interaction
- Data-driven world configuration

## Future Considerations

While the basic multiplayer framework is implemented, the architecture is designed to eventually support:
- More complex character interactions
- Items and inventories
- Combat system
- Persistent game state
- Chat and emote systems
- Dynamic world events
