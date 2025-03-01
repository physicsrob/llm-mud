import asyncio
import click
import json
import sys
from pathlib import Path
from .core.world import World
from .networking.server import main as server_main
from .gen.create_world import (
    create_world as run_create_world,
    design_world as run_design_world,
    convert_design_to_world,
    improve_world_design_iteration
)
from .gen.data_model import WorldDesign


async def run_server(world_file: str | Path, backend_only: bool = False):
    """Run the server.

    Args:
        world_file: Path to the world file to load
        backend_only: If True, don't serve web frontend files
    """
    await server_main(world_file, not backend_only)


@click.group()
def main():
    """MAD: A text-based multiplayer game."""
    pass


@main.command()
@click.argument("world_file")
@click.option(
    "--backend-only",
    is_flag=True,
    help="Run only the backend server without web interface",
)
def server(world_file: str, backend_only: bool = False):
    """Start the MUD server.

    WORLD_FILE: Path to the world file to load
    """
    asyncio.run(run_server(world_file, backend_only))


@main.command()
@click.argument("theme")
@click.argument("num_stories", type=int)
@click.argument("output_file")
def create_world(theme: str, num_stories: int, output_file: str):
    """Create a new world with the specified theme, number of stories, and output name.

    THEME: The theme of the world (e.g. 'fantasy', 'scifi')
    NUM_STORIES: The number of stories to generate
    OUTPUT_FILE: Name of the output file (without extension)
    """
    try:
        world = asyncio.run(run_create_world(theme, num_stories))
        # Add .json extension if not present
        if not output_file.endswith(".json"):
            output_file += ".json"
        world.save(output_file)
        click.echo(f"World saved to {output_file}")
    except KeyboardInterrupt:
        sys.exit(0)


@main.command()
@click.argument("theme")
@click.argument("num_stories", type=int)
@click.argument("output_file")
def design_world(theme: str, num_stories: int, output_file: str):
    """Create a world design with the specified theme and number of stories.
    
    This command only produces the design; it does not create a playable world.
    Use 'mad build-world' to convert a design into a playable world.

    THEME: The theme of the world (e.g. 'fantasy', 'scifi')
    NUM_STORIES: The number of stories to generate
    OUTPUT_FILE: Name of the output file (without extension)
    """
    try:
        design = asyncio.run(run_design_world(theme, num_stories))
        # Add .json extension if not present
        if not output_file.endswith(".json"):
            output_file += ".json"
        
        # Save the design to a file
        with open(output_file, 'w') as f:
            f.write(design.model_dump_json(indent=2))
            
        click.echo(f"World design saved to {output_file}")
    except KeyboardInterrupt:
        sys.exit(0)


@main.command()
@click.argument("design_file")
@click.argument("output_file")
def build_world(design_file: str, output_file: str):
    """Convert a world design into a playable world.

    DESIGN_FILE: Path to the world design file
    OUTPUT_FILE: Name of the output file (without extension)
    """
    try:
        # Load the design
        with open(design_file, 'r') as f:
            design_json = f.read()
        
        design = WorldDesign.model_validate_json(design_json)
        
        # Convert the design to a world
        world = convert_design_to_world(design)
        
        # Add .json extension if not present
        if not output_file.endswith(".json"):
            output_file += ".json"
            
        # Save the world
        world.save(output_file)
        click.echo(f"World built and saved to {output_file}")
    except FileNotFoundError:
        click.echo(f"Error: Design file '{design_file}' not found", err=True)
        sys.exit(1)
    except json.JSONDecodeError:
        click.echo(f"Error: '{design_file}' is not a valid JSON file", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@main.command()
@click.argument("design_file")
@click.argument("output_file")
def improve_world(design_file: str, output_file: str):
    """Improve an existing world design.

    DESIGN_FILE: Path to the world design file to improve
    OUTPUT_FILE: Name of the output file (without extension)
    """
    try:
        # Load the design
        with open(design_file, 'r') as f:
            design_json = f.read()
        
        design = WorldDesign.model_validate_json(design_json)
        
        # Improve the design
        improved_design = asyncio.run(improve_world_design_iteration(design))
        
        # Add .json extension if not present
        if not output_file.endswith(".json"):
            output_file += ".json"
            
        # Save the improved design
        with open(output_file, 'w') as f:
            f.write(improved_design.model_dump_json(indent=2))
            
        click.echo(f"Improved world design saved to {output_file}")
    except FileNotFoundError:
        click.echo(f"Error: Design file '{design_file}' not found", err=True)
        sys.exit(1)
    except json.JSONDecodeError:
        click.echo(f"Error: '{design_file}' is not a valid JSON file", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
