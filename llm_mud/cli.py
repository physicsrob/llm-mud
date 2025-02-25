import asyncio
import click
import sys
from pathlib import Path
from .core.world import World
from .networking.server import main as server_main
from .networking.client import main as client_main
from .gen.create_world import create_world as run_create_world


async def run_client():
    """Run the client."""
    await client_main()


async def run_server(world_file: str | Path, backend_only: bool = False):
    """Run the server.
    
    Args:
        world_file: Path to the world file to load
        backend_only: If True, don't serve web frontend files
    """
    await server_main(world_file, not backend_only)


@click.group()
def main():
    """LLM-MUD: A text-based multiplayer game."""
    pass


@main.command()
def client():
    """Connect to a running MUD server."""
    asyncio.run(run_client())


@main.command()
@click.argument("world_file")
@click.option(
    "--backend-only", 
    is_flag=True, 
    help="Run only the backend server without web interface"
)
def server(world_file: str, backend_only: bool = False):
    """Start the MUD server.

    WORLD_FILE: Path to the world file to load
    """
    asyncio.run(run_server(world_file, backend_only))


@main.command()
@click.argument("world_file")
@click.option(
    "--backend-only", 
    is_flag=True, 
    help="Run only the backend server without web interface"
)
def dev(world_file: str, backend_only: bool = False):
    """Run both server and client for development.

    WORLD_FILE: Path to the world file to load
    """

    async def run_dev():
        # Start server task
        server_task = asyncio.create_task(run_server(world_file, backend_only))

        # Wait a bit for server to start
        click.echo("Starting server...")
        await asyncio.sleep(2)

        # Start client
        click.echo("Starting client...")
        client_task = asyncio.create_task(run_client())

        try:
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [server_task, client_task], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        except KeyboardInterrupt:
            click.echo("\nShutting down...")
            for task in [server_task, client_task]:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

    try:
        asyncio.run(run_dev())
    except KeyboardInterrupt:
        sys.exit(0)


@main.command()
@click.argument("theme")
@click.argument("num_rooms", type=int)
@click.argument("output_file")
def create_world(theme: str, num_rooms: int, output_file: str):
    """Create a new world with the specified theme, number of rooms, and output name.

    THEME: The theme of the world (e.g. 'fantasy', 'scifi')
    NUM_ROOMS: The number of rooms to generate
    OUTPUT_NAME: Name of the output file (without extension)
    """
    try:
        world = asyncio.run(run_create_world(theme, num_rooms))
        # Add .json extension if not present
        if not output_file.endswith(".json"):
            output_file += ".json"
        world.save(output_file)
        click.echo(f"World saved to {output_file}")
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
