# PydanticAI Quick Reference Guide

## Basics of Agents

Agents are the primary interface for interacting with LLMs in PydanticAI. 

```python
from pydantic_ai import Agent

# Create a simple agent with system prompt
agent = Agent(
    'openai:gpt-4o',  # Models can be specified with 'provider:model_name' syntax
    system_prompt='Be concise, reply with one sentence.',
)

# Run the agent synchronously
result = agent.run_sync('Where does "hello world" come from?')
print(result.data)  # Access the response content via .data
```

### Adding Structure to Responses

Use Pydantic models for structured outputs:

```python
from pydantic import BaseModel

class CityLocation(BaseModel):
    city: str
    country: str

agent = Agent('openai:gpt-4o', result_type=CityLocation)
result = agent.run_sync('Where were the olympics held in 2012?')
print(result.data)  # Access as a structured object: city='London' country='United Kingdom'
```

### Using Dynamic System Prompts

```python
from pydantic_ai import Agent, RunContext

agent = Agent(
    'openai:gpt-4o',
    deps_type=str,  # Type of the dependency we'll inject
    system_prompt="Base instructions here."
)

# Dynamic system prompt using dependency
@agent.system_prompt
def add_context(ctx: RunContext[str]) -> str:
    return f"Additional context: {ctx.deps}"

# Run with a dependency
result = agent.run_sync('Tell me a joke.', deps="Make it about programming.")
```

## Basics of Tool Use

Tools let models call functions to retrieve information during runs.

### Simple Tool Example

```python
import random
from pydantic_ai import Agent, RunContext

agent = Agent(
    'openai:gpt-4o',
    system_prompt="You're a dice game. Roll the die and tell if user's guess matches."
)

@agent.tool_plain  # Use tool_plain for tools that don't need context
def roll_die() -> str:
    """Roll a six-sided die and return the result."""  # Docstring is used as tool description
    return str(random.randint(1, 6))

result = agent.run_sync('My guess is 4')
```

### Tool with Dependencies and Context

```python
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext

@dataclass
class Database:
    users: dict[int, str]
    
agent = Agent(
    'openai:gpt-4o',
    deps_type=Database,  # Specify dependency type
    system_prompt="Find information about users."
)

@agent.tool  # Use regular tool for accessing context/dependencies
def get_username(ctx: RunContext[Database], user_id: int) -> str:
    """Get username for the given user ID."""
    return ctx.deps.users.get(user_id, "Unknown user")

# Run with dependency
db = Database(users={1: "Alice", 2: "Bob"})
result = agent.run_sync('Who is user 1?', deps=db)
```

### Using Multiple Tools

Models can use multiple tools in a single run:

```python
from pydantic_ai import Agent, RunContext

agent = Agent(
    'openai:gpt-4o',
    system_prompt="Answer questions about the weather."
)

@agent.tool_plain
def get_location(city: str) -> dict:
    """Get latitude and longitude for a city."""
    # In real code, this would call a geocoding API
    locations = {"London": {"lat": 51.5, "lng": -0.12}}
    return locations.get(city, {"lat": 0, "lng": 0})

@agent.tool_plain
def get_weather(lat: float, lng: float) -> str:
    """Get weather for the given coordinates."""
    # In real code, this would call a weather API
    return "Sunny, 22°C"

result = agent.run_sync('What is the weather in London?')
# The model will likely call get_location first, then get_weather with the coordinates
```

## Basics of Graph Agents

For complex flows, PydanticAI provides a graph-based state machine via `pydantic-graph`.

```python
from __future__ import annotations
from dataclasses import dataclass

from pydantic_graph import BaseNode, End, Graph, GraphRunContext

# Define a state for the graph (optional)
@dataclass
class QuestionState:
    question: str | None = None
    attempts: int = 0

# Define nodes in the graph
@dataclass
class AskQuestion(BaseNode[QuestionState]):
    async def run(self, ctx: GraphRunContext[QuestionState]) -> CheckAnswer:
        if ctx.state.attempts == 0:
            ctx.state.question = "What is 2+2?"
        else:
            ctx.state.question = "What is 3+3?"
        return CheckAnswer()

@dataclass
class CheckAnswer(BaseNode[QuestionState]):
    answer: str = ""

    async def run(self, ctx: GraphRunContext[QuestionState]) -> GiveResult | AskQuestion:
        # In a real app, we'd get the answer from user input
        if self.answer == "":
            # Simulate user answering
            self.answer = "4" if ctx.state.attempts == 0 else "6"
            
        correct = (ctx.state.question == "What is 2+2?" and self.answer == "4") or \
                 (ctx.state.question == "What is 3+3?" and self.answer == "6")
                 
        if correct:
            return GiveResult("Correct!")
        else:
            ctx.state.attempts += 1
            if ctx.state.attempts >= 2:
                return GiveResult("Sorry, too many attempts!")
            return AskQuestion()

@dataclass
class GiveResult(BaseNode[QuestionState, None, str]):
    result: str
    
    async def run(self, ctx: GraphRunContext[QuestionState]) -> End[str]:
        return End(self.result)

# Create and run the graph
question_graph = Graph(nodes=[AskQuestion, CheckAnswer, GiveResult])
state = QuestionState()
result = question_graph.run_sync(AskQuestion(), state=state)
print(result.output)  # "Correct!"
```

## Error Handling and Retries

PydanticAI has built-in support for reflection and self-correction:

```python
from pydantic_ai import Agent, ModelRetry, RunContext

agent = Agent('openai:gpt-4o')

@agent.tool(retries=3)  # Specify max retry attempts
def validate_input(ctx: RunContext[None], value: str) -> str:
    """Validate that the input contains only letters.
    
    Args:
        value: The input string to validate
    """
    if not value.isalpha():
        # This causes the LLM to retry with a new value
        raise ModelRetry("Input must contain only letters")
    return value
```

## Using Type Unions for Flexible Responses

PydanticAI supports union types for result validation:

```python
from typing import Union
from pydantic import BaseModel

class Success(BaseModel):
    message: str

class Error(BaseModel):
    error_code: int
    description: str

# Create agent with union return type
agent = Agent[None, Union[Success, Error]](
    'openai:gpt-4o',
    result_type=Union[Success, Error],  # type: ignore until PEP-747
)

# Each type in the union becomes a separate tool option for the model
result = agent.run_sync("Process this request")
# Model can choose to return either Success or Error
```

## How Type Signatures and Docstrings Guide the LLM

PydanticAI leverages Python type annotations and docstrings to create detailed tool schemas:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-4o')

@agent.tool_plain
def search_database(query: str, filters: dict[str, str], max_results: int = 10) -> list[dict]:
    """Search the database for matching records.
    
    Args:
        query: The search query string to find relevant records
        filters: Dictionary of field:value pairs to filter results
        max_results: Maximum number of results to return (default: 10)
    
    Returns:
        List of matching records as dictionaries
    """
    # Implementation

# The LLM receives:
# 1. Function name: "search_database"
# 2. Description: "Search the database for matching records."
# 3. Parameters with types and descriptions:
#    - query (string): "The search query string to find relevant records"
#    - filters (object): "Dictionary of field:value pairs to filter results"
#    - max_results (integer, optional): "Maximum number of results to return (default: 10)"
# 4. Return type information
```

The type annotations and docstrings help the LLM understand:
- What each tool does (from the docstring description)
- What parameters each tool expects (from type signatures)
- What each parameter means (from parameter descriptions in docstrings)
- What optional values are available (from default values)
- What format the result will be in (from return type annotations)

This rich schema enables more accurate tool usage by the LLM.


## How to Write Collections of Pydantic-AI Tools

### Factory Function Pattern

The recommended approach for organizing collections of Pydantic-AI tools is the **Factory Function Pattern**. This pattern uses a function to create and return a collection of tools, leveraging Pydantic-AI's introspection capabilities while maintaining flexibility and encapsulation.

```python
def create_domain_tools(config=None) -> list[Tool]:
    """Create a collection of tools for working with a specific domain.
    
    Args:
        config: Optional configuration settings for tools
        
    Returns:
        A list of Pydantic-AI Tool objects ready for use with an agent
    """
    # Initialize any shared resources
    client = DomainClient(config)
    
    # Define tool functions within the closure to maintain access to client
    def create_item(name: str, description: str) -> Item:
        """Create a new item in the domain.
        
        Args:
            name: The name of the item to create
            description: The item description
            
        Returns:
            The created item object
        """
        return client.create_item(name, description)
    
    def get_item(item_id: str) -> Item:
        """Retrieve an item by its ID.
        
        Args:
            item_id: The ID of the item to retrieve
            
        Returns:
            The requested item
        """
        return client.get_item(item_id)
    
    # Return a list of Tool objects created from the functions
    return [
        Tool(create_item),
        Tool(get_item),
        # Add more tools as needed
    ]
```

### Best Practices

- Write clear docstrings in a consistent format (Google, NumPy, or Sphinx style)
- Use proper type annotations for all parameters and return values
- Keep tool functions focused on a single responsibility
- Group related tools into separate factory functions by domain
- Document parameter constraints in docstrings (e.g., valid values for status fields)
- Consider adding optional parameters to the factory function for different configurations

### Usage Example

```python
# In your agent setup code
from my_tools import create_domain_tools

# Create tools with default configuration
tools = create_domain_tools()

# Or with custom configuration
custom_tools = create_domain_tools(config={"api_key": "custom_key"})

# Add to your agent
agent = Agent("my-agent", tools=tools)
```

This pattern scales well across different domains while keeping your codebase organized and maintainable.


