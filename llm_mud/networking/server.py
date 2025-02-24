import asyncio
import traceback
import websockets
from websockets import ClientConnection, serve
from pathlib import Path

from ..core.player import Player
from ..core.world import World
from ..core.command_parser import parse


class Server:
    def __init__(self, world: World):
        self.clients: list[tuple[Player, ClientConnection]] = []
        self.world = world

    @classmethod
    async def create(cls, world_file: str | Path) -> "Server":
        """Factory method to create a server with a loaded world."""
        world = World.load(world_file)
        return cls(world)

    async def login_user(self, websocket: ClientConnection) -> Player:
        """Login a user and add them to the world."""
        await websocket.send("Welcome to the game!")
        await websocket.send("What is your name?")
        name = (await websocket.recv()).strip()
        return self.world.login_player(name)

    async def handle_client(self, websocket: ClientConnection) -> None:
        """Handle a single client connection."""
        player = await self.login_user(websocket)
        self.clients.append((player, websocket))

        try:
            await self.broadcast(f"{player.name} joined the server")

            # Create tasks for input and output handling
            input_task = asyncio.create_task(
                self._handle_client_input(player, websocket)
            )
            output_task = asyncio.create_task(
                self._handle_client_output(player, websocket)
            )

            # Wait for the input task to complete OR for an exception in either task
            while not input_task.done():
                # Check for exceptions on a short timeout
                done, pending = await asyncio.wait(
                    [input_task, output_task],
                    return_when=asyncio.FIRST_EXCEPTION,
                    timeout=1.0,
                )

                # Check if tasks completed with exceptions
                for task in done:
                    if task.exception():
                        # Exit the loop on exception
                        input_task.cancel()
                        output_task.cancel()
                        break

                # If input task completed, we're done
                if input_task.done():
                    break

            # Cancel any remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            print(f"Error handling client {player.name}: {e}")
            print(f"Traceback: {traceback.format_exc()}")
        finally:
            print(f"Logging out player {player.name}")
            self.world.logout_player(player)
            self.clients = [(p, c) for p, c in self.clients if c != websocket]
            await self.broadcast(f"{player.name} left the server")

    async def _handle_client_input(
        self, player: Player, websocket: ClientConnection
    ) -> None:
        """Handle incoming messages from a client."""
        try:
            async for message in websocket:
                await player.process_command(self.world, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"Error handling client input for player {player.name}: {e}")
            print(f"Traceback: {traceback.format_exc()}")

    async def _handle_client_output(
        self, player: Player, websocket: ClientConnection
    ) -> None:
        """Handle outgoing messages to a client."""
        try:
            # Welcome message with world info
            welcome_message = (
                f"Welcome to {self.world.title}!\n\n{self.world.brief_description}"
            )
            await player.send_message("server", welcome_message)

            # Show current room
            current_room = self.world.get_character_room(player.id)
            if current_room:
                await player.send_message("room", current_room.brief_describe())

            # Process messages from player's queue
            async for message in player:
                await websocket.send(str(message))
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"Error handling client output for {player.name}: {e}")
            print(f"Traceback: {traceback.format_exc()}")

    async def broadcast(self, message: str) -> None:
        """Send a text message to all connected clients."""
        for player, _ in self.clients:
            try:
                await player.send_message("server", message)
            except websockets.exceptions.ConnectionClosed:
                pass

    async def run_world_ticker(self) -> None:
        """Run the world simulation ticker."""
        while True:
            await self.world.tick()
            await asyncio.sleep(1)

    async def start(self, host: str = "localhost", port: int = 8765) -> None:
        """Start the server and world simulation."""
        async with serve(self.handle_client, host, port) as server:
            print(f"Server started on ws://{host}:{port}")

            try:
                await asyncio.gather(server.serve_forever(), self.run_world_ticker())
            except asyncio.CancelledError:
                print("Server shutdown initiated...")


async def main(world_file: str | Path) -> None:
    server = await Server.create(world_file)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main("world1.json"))
