#!/usr/bin/env python3
"""
Test script for Nng_bus_hub in CONTROLLER mode.
This script creates a bus hub controller that listens for connections
and can send/receive messages to/from nodes.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cuemsutils.tools.CommunicatorServices import Nng_bus_hub
from cuemsutils.log import Logger


async def message_receiver(hub):
    """Task to continuously receive and display incoming messages."""
    while True:
        try:
            message = await hub.get_message()
            print(f"📨 Controller received from {message.sender}: {message.data}")
        except Exception as e:
            Logger.error(f"Error receiving message: {e}")
            break


async def message_sender(hub):
    """Task to send periodic messages to the bus."""
    counter = 0
    while True:
        try:
            await asyncio.sleep(3)  # Send every 3 seconds
            counter += 1
            message = f"Controller broadcast #{counter}"
            print(f"📤 Controller sending: {message}")
            await hub.send_message(message)
        except Exception as e:
            Logger.error(f"Error sending message: {e}")
            break


async def main():
    """Main function to run the bus hub controller."""
    # Configure the address - using IPC for local testing
    bus_address = "ipc:///tmp/cuems_bus_test"
    
    print("=" * 60)
    print("🎛️  CUEMS Bus Hub Controller Test")
    print("=" * 60)
    print(f"Address: {bus_address}")
    print(f"Mode: CONTROLLER (listening)")
    print("-" * 60)
    
    # Create hub in CONTROLLER mode (default)
    hub = Nng_bus_hub(bus_address, mode=Nng_bus_hub.Mode.CONTROLLER)
    
    # Create background tasks for sending and receiving
    sender_task = asyncio.create_task(message_sender(hub))
    receiver_task = asyncio.create_task(message_receiver(hub))
    
    try:
        print("✅ Controller starting...")
        print("📡 Waiting for node connections...")
        print("Press Ctrl+C to stop\n")
        
        # Start the hub (this will run until error or cancellation)
        await hub.start()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Keyboard interrupt received")
    except Exception as e:
        Logger.error(f"Controller error: {e}")
    finally:
        print("🛑 Stopping controller...")
        sender_task.cancel()
        receiver_task.cancel()
        
        try:
            await asyncio.gather(sender_task, receiver_task, return_exceptions=True)
        except Exception:
            pass
        
        print("✅ Controller stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

