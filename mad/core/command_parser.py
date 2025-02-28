from pydantic import BaseModel, Field

from .character_action import CharacterAction


class ParseResult(BaseModel):
    """Result of parsing a player's command input"""

    action: CharacterAction | None = Field(
        default=None, description="The parsed player action if command was valid"
    )
    error_msg: str | None = Field(
        default=None,
        description="Error message if command could not be parsed or was invalid",
    )


# Dictionary of direction abbreviations
DIRECTION_ABBREVIATIONS = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
    "u": "up",
    "d": "down",
}

# Movement command verbs
MOVEMENT_VERBS = {"go", "move", "walk", "run", "head", "travel", "leave", "exit"}

# Look command verbs and full phrases
LOOK_COMMANDS = {"l", "look", "look around", "describe", "examine", "examine room", "where am i"}

# Idle command verbs
IDLE_COMMANDS = {"idle", "wait", "rest"}


def normalize_command(command_input: str) -> tuple[str, str]:
    """Normalize and extract verb and arguments from a command.
    
    Args:
        command_input: Raw command string from user
        
    Returns:
        Tuple of (verb, arguments)
    """
    # Strip whitespace and convert to lowercase
    command = command_input.strip().lower()
    
    # Handle empty commands
    if not command:
        return "", ""
    
    # Remove leading slash if present
    if command.startswith("/"):
        command = command[1:].lstrip()
    
    # Try to split into verb and arguments
    parts = command.split(maxsplit=1)
    
    if len(parts) == 1:
        # Command is just a verb with no arguments
        return parts[0], ""
    else:
        # Command has both verb and arguments
        args = parts[1].strip()
        
        # Remove surrounding quotes if present (both single and double quotes)
        if (args.startswith('"') and args.endswith('"')) or \
           (args.startswith("'") and args.endswith("'")):
            args = args[1:-1].strip()
            
        return parts[0], args


async def parse(world: "World", player: "Player", command_input: str) -> ParseResult:
    """Parse and execute a player command.

    Args:
        world: The game world instance
        player: The player issuing the command
        command_input: The command string to parse

    Returns:
        ParseResult containing either a PlayerAction or error message
    """
    room = world.get_character_room(player.id)
    available_exits = room.exits.keys()
    
    # Handle empty commands
    if not command_input.strip():
        return ParseResult(error_msg="Please enter a command.")
    
    # Parse input into verb and args
    verb, args = normalize_command(command_input)
    
    # Handle single-word direction commands (including abbreviations)
    if not args:
        # Check if the verb is a direction or abbreviation
        direction = verb
        if direction in DIRECTION_ABBREVIATIONS:
            direction = DIRECTION_ABBREVIATIONS[direction]
        
        if direction in available_exits:
            return ParseResult(
                action=CharacterAction(action_type="move", direction=direction)
            )
        
        # Handle single word look commands
        if verb in LOOK_COMMANDS:
            return ParseResult(action=CharacterAction(action_type="look"))
        
        # Handle single word idle commands
        if verb in IDLE_COMMANDS:
            return ParseResult(action=CharacterAction(action_type="idle"))
    
    # Handle two-part commands
    
    # Movement commands like "go north"
    if verb in MOVEMENT_VERBS:
        direction = args
        if direction in DIRECTION_ABBREVIATIONS:
            direction = DIRECTION_ABBREVIATIONS[direction]
        
        if direction in available_exits:
            return ParseResult(
                action=CharacterAction(action_type="move", direction=direction)
            )
        else:
            return ParseResult(
                error_msg=f"You can't go {direction} from here. Available exits: {', '.join(available_exits)}"
            )
    
    # Look command with arguments (still just results in look)
    if verb in {"look", "examine"} and args:
        return ParseResult(action=CharacterAction(action_type="look"))
    
    # Say command
    if verb == "say" and args:
        return ParseResult(action=CharacterAction(action_type="say", message=args))
    elif verb == "say" and not args:
        return ParseResult(error_msg="What do you want to say?")
    
    # Emote commands (me/emote)
    if verb in {"me", "emote"} and args:
        return ParseResult(action=CharacterAction(action_type="emote", message=args))
    elif verb in {"me", "emote"} and not args:
        return ParseResult(error_msg="What do you want to emote?")
    
    # If nothing matched, return a helpful error message
    return ParseResult(
        error_msg=f"I don't understand '{command_input}'. Try movement ({', '.join(available_exits)}), 'look', 'say [message]', or 'emote [action]'."
    )
