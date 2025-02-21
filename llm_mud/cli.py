import asyncio
import click
import sys
from pathlib import Path
from .core.world import World
from .networking.server import main as server_main
from .networking.client import main as client_main
from .core.world_gen import generate_world
from .core.room_gen import generate_starting_room

async def run_client():
    """Run the client."""
    await client_main()



async def run_server():
    """Run the server."""
    await server_main()


@click.group()
def main():
    """LLM-MUD: A text-based multiplayer game."""
    pass


@main.command()
def client():
    """Connect to a running MUD server."""
    asyncio.run(run_client())


@main.command()
def server():
    """Start the MUD server."""
    asyncio.run(run_server())


@main.command()
def dev():
    """Run both server and client for development."""

    async def run_dev():
        # Start server task
        server_task = asyncio.create_task(run_server())

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
@click.argument('theme')
def create_world(theme: str):
    """Create a new world with the specified theme."""
    async def run_create():
        world_desc = await generate_world(theme)
        click.echo(f"\nGenerated World: {world_desc.title}")
        click.echo("\nBrief Description:")
        click.echo(world_desc.brief_description)
        click.echo("\nDetailed Description:")
        click.echo(world_desc.long_description)
        click.echo("\nOther Details:")
        click.echo(world_desc.other_details)

        room_desc = await generate_starting_room(world_desc)
        click.echo(f"\nGenerated Room: {room_desc.title}")
        click.echo("\nBrief Description:")
        click.echo(room_desc.brief_description)
        click.echo("\nDetailed Description:")
        click.echo(room_desc.long_description)
    try:
        asyncio.run(run_create())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
