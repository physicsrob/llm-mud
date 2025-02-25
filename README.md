# MAD (Multi Agent Dungeon)

A text-based game engine inspired by Multi-User Dungeons (MUDs). The goal of this project is to explore the use of LLMs to power a text-based game.

## Features

- Multi-player support with client-server architecture
- Real-time player interactions and movement
- Dynamic world loading from JSON configuration
- Command parsing system for player actions
- Character system with basic attributes
- Room-based navigation and exploration
- LLM-powered world generation
- Graph-based room connectivity
- World visualization tools
- Web-based terminal interface using xterm.js

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mad.git
cd mad

# Install dependencies
pip install -e .
```

## Usage

Run the game server:

```bash
# Start the server (includes web interface)
mad server world1.json

# Start the server without web interface
mad server --backend-only world1.json
```

## Web Interface

The server includes a web-based terminal interface powered by xterm.js. To access it:

1. Start the server: `mad server world1.json`
2. Open a web browser and navigate to: `http://localhost:8765`
3. The web interface automatically connects to the WebSocket server

## Project Structure

The project is organized into several modules:

### Core Module
- `mad/core/world.py`: Manages the game world, rooms, and game state
- `mad/core/room.py`: Defines room structure and properties
- `mad/core/character.py`: Base character class for players and NPCs
- `mad/core/player.py`: Player-specific functionality and state
- `mad/core/command_parser.py`: Processes and validates player commands
- `mad/core/character_action.py`: Defines available character actions

### Networking Module
- `mad/networking/server.py`: Implements the game server and manages client connections
- `mad/networking/messages.py`: Message types for client-server communication

### Generation Module
- `mad/gen/create_world.py`: World generation and configuration
- `mad/gen/describe_room_agent.py`: LLM-powered room description generation
- `mad/gen/describe_world_agent.py`: World narrative generation
- `mad/gen/graph.py`: Graph-based world representation
- `mad/gen/vis_map.py`: World map visualization tools
- `mad/gen/cycle_finder.py`: Detects cycles in world graph

### Configuration and CLI
- `mad/cli.py`: Command-line interface for player interaction
- `mad/config.py`: Configuration settings

## Design Philosophy

This project emphasizes:
- Clean separation between client and server responsibilities
- Type safety using Python type hints
- Modular architecture for easy feature extension
- Real-time multiplayer interaction
- Data-driven world configuration
- LLM-powered procedural content generation

## Future Considerations

While the basic multiplayer framework and world generation are implemented, the architecture is designed to eventually support:
- More complex character interactions
- Items and inventories
- Combat system
- Persistent game state
- Chat and emote systems
- Advanced narrative generation
