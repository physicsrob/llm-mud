import asyncio
import websockets
from websockets import ClientConnection, serve
from .player import Player, PlayerMessageType
from .world import World

class Server:
    def __init__(self, world: World):
        self.clients: list[tuple[Player, ClientConnection]] = []
        self.world = world
    
    async def login_user(self, websocket: ClientConnection) -> Player:
        """
        Login a user and add them to the world.
        """
        await websocket.send("Welcome to the game!")
        await websocket.send("What is your name?")
        name = (await websocket.recv()).strip()
        return self.world.login_player(name) 
    
    async def handle_client(self, websocket: ClientConnection) -> None:
        """
        Handle a single client connection.
        """
        player = await self.login_user(websocket)
        self.clients.append((player, websocket))

        async def handle_websocket():
            try: 
                async for message in websocket:
                    await player.handle_input(message)
            except Exception:
                print("Error in handle_websocket")
                pass
        
        async def handle_player_output():
            try:
                async for message in player:
                    await websocket.send(str(message))
            except Exception:
                print("Error in player output")
                pass
        
        try:
            await self.broadcast(f"{player.name} joined the server")
            
            # Create tasks
            websocket_task = asyncio.create_task(handle_websocket())
            player_task = asyncio.create_task(handle_player_output())
            
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [websocket_task, player_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel any remaining tasks
            if websocket_task in pending:
                websocket_task.cancel()
                try:
                    await websocket_task
                except asyncio.CancelledError:
                    pass

            if player_task in pending:
                player_task.cancel() 
                try:
                    await player_task
                except asyncio.CancelledError:
                    pass

        finally:
            self.world.logout_player(player)
            self.clients = [(p, c) for p, c in self.clients if c != websocket]
            await self.broadcast(f"{player.name} left the server")
    
    async def broadcast(self, message: str) -> None:
        """
        Send a text message to all connected clients except the sender.
        """
        for player, client in self.clients:
            try:
                await player.send_message(PlayerMessageType.SERVER, message)
            except websockets.exceptions.ConnectionClosed:
                pass

    async def start(self, host: str = "localhost", port: int = 8765) -> None:
        async def world_ticker():
            while True:
                await self.world.tick()
                await asyncio.sleep(1)

        async with serve(self.handle_client, host, port) as server:
            print(f"Server started on ws://{host}:{port}")
            server_task = asyncio.create_task(server.serve_forever())
            ticker_task = asyncio.create_task(world_ticker())
            
            try:
                # Run both tasks until one completes or there's an error
                await asyncio.gather(server_task, ticker_task)
            except asyncio.CancelledError:
                # Handle graceful shutdown
                server_task.cancel()
                ticker_task.cancel()
                await asyncio.gather(server_task, ticker_task, return_exceptions=True)


async def main():
    world = World()
    world.load_from_file("world1.json")
    server = Server(world)
    await server.start()
    # player = world.login_player("John")
    # await player.handle_input("nort")
    # async for message in player:
    #     print(message)

if __name__ == "__main__":
    asyncio.run(main())