# LLM Mud

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
git clone https://github.com/yourusername/llm-mud.git
cd llm-mud

# Install dependencies
pip install -e .
```

## Usage

You can run the game in different modes:

```bash
# Start in development mode (single player)
llmmud dev world1.json

# Start the server (includes web interface)
llmmud server world1.json

# Start the server without web interface
llmmud server --backend-only world1.json

# Start a client
llmmud client
```

## Web Interface

The server includes a web-based terminal interface powered by xterm.js. To access it:

1. Start the server: `llmmud server world1.json`
2. Open a web browser and navigate to: `http://localhost:8765`
3. The web interface automatically connects to the WebSocket server

You can play directly in your browser without installing a separate client.

## Project Structure

The project is organized into several modules:

### Core Module
- `llm_mud/core/world.py`: Manages the game world, rooms, and game state
- `llm_mud/core/room.py`: Defines room structure and properties
- `llm_mud/core/character.py`: Base character class for players and NPCs
- `llm_mud/core/player.py`: Player-specific functionality and state
- `llm_mud/core/command_parser.py`: Processes and validates player commands
- `llm_mud/core/character_action.py`: Defines available character actions

### Networking Module
- `llm_mud/networking/server.py`: Implements the game server and manages client connections
- `llm_mud/networking/client.py`: Handles client-side networking and game state
- `llm_mud/networking/messages.py`: Message types for client-server communication

### Generation Module
- `llm_mud/gen/create_world.py`: World generation and configuration
- `llm_mud/gen/describe_room_agent.py`: LLM-powered room description generation
- `llm_mud/gen/describe_world_agent.py`: World narrative generation
- `llm_mud/gen/graph.py`: Graph-based world representation
- `llm_mud/gen/vis_map.py`: World map visualization tools
- `llm_mud/gen/cycle_finder.py`: Detects cycles in world graph

### Configuration and CLI
- `llm_mud/cli.py`: Command-line interface for player interaction
- `llm_mud/config.py`: Configuration settings

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
