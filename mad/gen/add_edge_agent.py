import random
from pydantic_ai import Agent

from mad.gen.data_model import Edge
from mad.gen.data_model import WorldDescription

from ..config import creative_model_instance


add_edge_prompt = """
You are a master environment designer for an immersive text adventure.
You are given the description of the world, and a list of existing
connections between rooms.

Your job is to create a new connection between two rooms. The new connection
can be either an existing room or a new room.

The goal is to expand the map in a way that is consistent with the overall
theme and style of the world.

The new connection should be a good fit for the overall map.
"""

add_edge_agent = Agent(
    model=creative_model_instance,
    result_type=Edge,
    retries=2,
    system_prompt=add_edge_prompt,
    model_settings={
        "temperature": 0.7,
    },
)


async def add_edge(
    world: WorldDescription,
    existing_edges: list[Edge],
    room_id: str,
) -> Edge:

    random.shuffle(existing_edges)

    user_prompt = f"""
    World Title: {world.title}
    World Description: {world.description}

    Existing edges:
    {existing_edges}

    Source Room ID: {room_id}
    """

    result = await add_edge_agent.run(user_prompt)
    return result.data
