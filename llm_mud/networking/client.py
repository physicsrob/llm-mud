import asyncio
import websockets
import sys
from websockets.client import WebSocketClientProtocol


async def handle_input(websocket: WebSocketClientProtocol) -> None:
    """Read input from console and send to server."""
    while True:
        try:
            message = await asyncio.get_event_loop().run_in_executor(None, input)
            await websocket.send(message)
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            print(f"Error in input handling: {e}")
            break


async def handle_messages(websocket: WebSocketClientProtocol) -> None:
    """Receive and print messages from the server."""
    try:
        async for message in websocket:
            print(message)
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"Error in message handling: {e}")


async def main(uri: str = "ws://localhost:8765") -> None:
    """Connect to the MUD server and handle I/O."""
    try:
        async with websockets.connect(uri) as websocket:
            input_task = asyncio.create_task(handle_input(websocket))
            message_task = asyncio.create_task(handle_messages(websocket))

            # Wait for both tasks to complete or until an exception occurs
            try:
                # Using FIRST_EXCEPTION to ensure we detect errors quickly
                done, pending = await asyncio.wait(
                    [input_task, message_task], return_when=asyncio.FIRST_EXCEPTION
                )

                # Check for exceptions
                for task in done:
                    if task.exception():
                        # Re-raise the exception so it can be handled
                        task.result()
            finally:
                # Cancel remaining tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
    except websockets.exceptions.ConnectionClosed:
        print("\nDisconnected from server")
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
