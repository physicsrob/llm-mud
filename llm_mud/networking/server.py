import asyncio
import traceback
import json
import os
from aiohttp import web, WSMsgType
from pathlib import Path

from ..core.player import Player
from ..core.world import World
from ..core.command_parser import parse


class Server:
    def __init__(self, world: World, serve_web: bool = True):
        self.clients = []  # List of (Player, WebSocketResponse) tuples
        self.world = world
        self.serve_web = serve_web
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.world_ticker_task = None
        
        # Set up routes
        self.setup_routes()

    @classmethod
    async def create(cls, world_file: str | Path, serve_web: bool = True) -> "Server":
        """Factory method to create a server with a loaded world.
        
        Args:
            world_file: Path to the world file to load
            serve_web: Whether to serve web frontend files
        """
        world = World.load(world_file)
        return cls(world, serve_web)
    
    def setup_routes(self):
        """Set up the HTTP and WebSocket routes."""
        # WebSocket endpoint
        self.app.router.add_get('/ws', self.websocket_handler)
        
        if self.serve_web:
            # Get the project root directory
            project_dir = Path(__file__).parent.parent.parent
            web_dir = project_dir / "web"
            
            if web_dir.exists():
                # Serve static files
                self.app.router.add_static('/', web_dir, show_index=True)
                print(f"Web directory found at {web_dir}")
            else:
                print(f"Warning: Web directory not found at {web_dir}")

    async def login_user(self, ws: web.WebSocketResponse) -> Player:
        """Login a user and add them to the world."""
        await ws.send_str("Welcome to the game!")
        await ws.send_str("What is your name?")
        
        msg = await ws.receive()
        if msg.type == WSMsgType.TEXT:
            name = msg.data.strip()
            return self.world.login_player(name)
        else:
            raise ValueError("Expected text message for login")

    async def websocket_handler(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        try:
            # Login the player
            player = await self.login_user(ws)
            self.clients.append((player, ws))
            
            # Broadcast join message
            await self.broadcast(f"{player.name} joined the server")
            
            # Set up player output task
            output_task = asyncio.create_task(self._handle_client_output(player, ws))
            
            # Welcome message with world info
            welcome_message = (
                f"Welcome to {self.world.title}!\n\n{self.world.brief_description}"
            )
            await player.send_message("server", welcome_message)
            
            # Show current room
            current_room = self.world.get_character_room(player.id)
            if current_room:
                await player.send_message("room", current_room.brief_describe())
            
            # Handle incoming messages
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await player.process_command(self.world, msg.data)
                elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                    break
            
            # Clean up output task
            output_task.cancel()
            try:
                await output_task
            except asyncio.CancelledError:
                pass
                
        except Exception as e:
            print(f"Error in websocket handler: {e}")
            print(f"Traceback: {traceback.format_exc()}")
        finally:
            # Get player from connection if it exists
            player_to_remove = None
            for p, w in self.clients:
                if w == ws:
                    player_to_remove = p
                    break
            
            if player_to_remove:
                print(f"Logging out player {player_to_remove.name}")
                self.world.logout_player(player_to_remove)
                self.clients = [(p, w) for p, w in self.clients if w != ws]
                await self.broadcast(f"{player_to_remove.name} left the server")
            
        return ws

    async def _handle_client_output(self, player: Player, ws: web.WebSocketResponse) -> None:
        """Handle outgoing messages to a client."""
        try:
            # Process messages from player's queue
            async for message in player:
                if ws.closed:
                    break
                await ws.send_str(str(message))
        except Exception as e:
            print(f"Error handling client output for {player.name}: {e}")
            print(f"Traceback: {traceback.format_exc()}")

    async def broadcast(self, message: str) -> None:
        """Send a text message to all connected clients."""
        for player, _ in self.clients:
            try:
                await player.send_message("server", message)
            except Exception:
                pass

    async def run_world_ticker(self) -> None:
        """Run the world simulation ticker."""
        try:
            while True:
                await self.world.tick()
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("World ticker cancelled")
            raise

    async def start(self, host: str = "localhost", port: int = 8765) -> None:
        """Start the server and world simulation."""
        # Set up runner and site
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port)
        
        # Start web server
        await self.site.start()
        print(f"Server started on http://{host}:{port}")
        print(f"WebSocket endpoint at ws://{host}:{port}/ws")
        
        # Start world ticker
        self.world_ticker_task = asyncio.create_task(self.run_world_ticker())
        
        # Keep server running
        try:
            # Wait forever or until cancelled
            await asyncio.Future()
        except asyncio.CancelledError:
            print("Server shutdown initiated...")
            # Cancel world ticker
            if self.world_ticker_task:
                self.world_ticker_task.cancel()
            # Close all websocket connections
            for _, ws in self.clients:
                await ws.close()
            # Cleanup runner
            await self.runner.cleanup()
            print("Server shutdown complete")


async def main(world_file: str | Path, serve_web: bool = True) -> None:
    """Start the server with the given world file.
    
    Args:
        world_file: Path to the world file to load
        serve_web: Whether to serve web frontend files
    """
    server = await Server.create(world_file, serve_web)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main("world1.json"))
