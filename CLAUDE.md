# MAD Project Guidelines

## Commands
- Install: `pip install -e .`
- Run server: `mad server <world_file>`

## Pydantic AI
- pydantic-ai is a framework for building LLM agents. Whenever working with pydantic-ai read pydantic-ai-guide.md

## Code Style
- Python >= 3.10 with type hints
- Type annotations using Python 3.9+ style. Use built-in types like list and tuple directly rather than importing from typing. Use "|None" instead of Optional, etc.
- Thorough and professional comments
- Imports: standard library first, then project imports
- Naming: snake_case for variables/functions, PascalCase for classes
- Classes: Pydantic models for data validation
- Async: Use asyncio for networking/concurrent operations
- Error handling: Specific exception handling with try/except
- Documentation: Docstrings for classes and functions
- Architecture: Clean separation between client/server components
- Modules: Organize by functionality (core, networking, gen)
- CLI: Use Click library for command interfaces
