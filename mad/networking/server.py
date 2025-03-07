import asyncio
import traceback
import json
import os
from aiohttp import web, WSMsgType
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
from pathlib import Path

from ..core.player import Player
from ..core.world import World
from ..core.command_parser import parse
from ..db_models.users import User
from ..db_models.db import init_db, get_session
from ..db_models.auth import authenticate_user, create_access_token, get_user_by_token
from ..networking.messages import BaseMessage, SystemMessage


class Server:
    def __init__(self, world: World, serve_web: bool = True):
        self.clients = []  # List of (Player, WebSocketResponse) tuples
        self.world = world
        self.serve_web = serve_web
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.world_ticker_task = None

        # Set up session
        fernet_key = fernet.Fernet.generate_key()
        secret_key = fernet.Fernet(fernet_key)
        setup_session(self.app, EncryptedCookieStorage(secret_key))

        # Initialize database
        init_db()

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
        # API routes
        self.app.router.add_post("/api/register", self.register_handler)
        self.app.router.add_post("/api/login", self.login_handler)
        self.app.router.add_get("/api/world-info", self.world_info_handler)

        # WebSocket endpoint
        self.app.router.add_get("/ws", self.websocket_handler)

        if self.serve_web:
            # Get the project root directory
            project_dir = Path(__file__).parent.parent.parent
            web_dir = project_dir / "web"

            if web_dir.exists():
                # Serve static files
                self.app.router.add_static("/", web_dir, show_index=True)
                print(f"Web directory found at {web_dir}")
            else:
                print(f"Warning: Web directory not found at {web_dir}")

    async def register_handler(self, request):
        """Handle user registration."""
        try:
            data = await request.json()
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return web.json_response(
                    {"success": False, "message": "Username and password required"},
                    status=400,
                )

            # Check if user already exists
            session = get_session()
            try:
                existing_user = (
                    session.query(User).filter(User.username == username).first()
                )
                if existing_user:
                    return web.json_response(
                        {"success": False, "message": "Username already taken"},
                        status=400,
                    )

                # Create new user
                user = User.create(username=username, password=password)
                session.add(user)
                session.commit()

                # Create JWT token
                token = create_access_token({"sub": user.username})

                return web.json_response(
                    {"success": True, "token": token, "username": user.username}
                )
            finally:
                session.close()
        except Exception as e:
            print(f"Error in register handler: {e}")
            return web.json_response(
                {"success": False, "message": "Server error"}, status=500
            )

    async def login_handler(self, request):
        """Handle user login."""
        try:
            data = await request.json()
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return web.json_response(
                    {"success": False, "message": "Username and password required"},
                    status=400,
                )

            # Authenticate user
            user = await authenticate_user(username, password)
            if not user:
                return web.json_response(
                    {"success": False, "message": "Invalid username or password"},
                    status=401,
                )

            # Create JWT token
            token = create_access_token({"sub": user.username})

            return web.json_response(
                {"success": True, "token": token, "username": user.username}
            )
        except Exception as e:
            print(f"Error in login handler: {e}")
            return web.json_response(
                {"success": False, "message": "Server error"}, status=500
            )

    async def world_info_handler(self, request):
        """Handle world info requests."""
        try:
            # Return only basic world title
            return web.json_response({"success": True, "title": self.world.title})
        except Exception as e:
            print(f"Error in world info handler: {e}")
            return web.json_response(
                {"success": False, "message": "Server error"}, status=500
            )

    async def login_user(self, ws: web.WebSocketResponse) -> Player:
        """Login a user and add them to the world."""
        # Get token from client
        msg = await ws.receive()
        if msg.type != WSMsgType.TEXT:
            raise ValueError("Expected text message containing token")

        token = msg.data.strip()
        user = await get_user_by_token(token)

        if user is None:
            # Create error message and immediately convert to dict for sending
            error_msg = SystemMessage(
                content="Invalid or expired token. Please log in via the web interface.",
                title="Error",
                severity="error"
            )
            await ws.send_json(error_msg.model_dump())
            raise ValueError("Invalid authentication token")

        # Create player with authenticated username
        return await self.world.login_player(user.username)

    async def websocket_handler(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        try:
            # Login the player
            player = await self.login_user(ws)
            self.clients.append((player, ws))

            # Set up player output task
            output_task = asyncio.create_task(self._handle_client_output(player, ws))
            
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
                await self.world.logout_player(player_to_remove)
                self.clients = [(p, w) for p, w in self.clients if w != ws]

        return ws

    async def _handle_client_output(
        self, player: Player, ws: web.WebSocketResponse
    ) -> None:
        """Handle outgoing messages to a client."""
        try:
            # Process messages from player's queue
            async for message in player:
                if ws.closed:
                    break
                    
                # Send message as JSON to the client
                await ws.send_json(message.model_dump())
        except Exception as e:
            print(f"Error handling client output for {player.name}: {e}")
            print(f"Traceback: {traceback.format_exc()}")


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
