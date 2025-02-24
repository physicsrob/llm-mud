# LLM-MUD Project Guidelines

## Commands
- Install: `pip install -e .`
- Run development mode: `llmmud dev`
- Run server: `llmmud server`
- Run client: `llmmud client`

## Code Style
- Python >= 3.10 with type hints
- Imports: standard library first, then project imports
- Naming: snake_case for variables/functions, PascalCase for classes
- Classes: Pydantic models for data validation
- Async: Use asyncio for networking/concurrent operations
- Error handling: Specific exception handling with try/except
- Documentation: Docstrings for classes and functions
- Architecture: Clean separation between client/server components
- Modules: Organize by functionality (core, networking, gen)
- CLI: Use Click library for command interfaces