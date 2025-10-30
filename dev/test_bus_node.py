#!/usr/bin/env python3
"""
Test script for Nng_bus_hub in NODE mode.
This script creates a bus hub node that connects to the controller
and can send/receive messages.
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
            print(f"📨 Node received from {message.sender}: {message.data}")
        except Exception as e:
            Logger.error(f"Error receiving message: {e}")
            break


async def message_sender(hub):
    """Task to send periodic messages to the bus."""
    counter = 0
    while True:
        try:
            await asyncio.sleep(5)  # Send every 5 seconds
            counter += 1
            message = f"Node message #{counter}"
            print(f"📤 Node sending: {message}")
            await hub.send_message(message)
        except Exception as e:
            Logger.error(f"Error sending message: {e}")
            break


async def main():
    """Main function to run the bus hub node."""
    # Configure the address - must match the controller's address
    bus_address = "ipc:///tmp/cuems_bus_test"
    
    print("=" * 60)
    print("📡 CUEMS Bus Hub Node Test")
    print("=" * 60)
    print(f"Address: {bus_address}")
    print(f"Mode: NODE (connecting)")
    print("-" * 60)
    
    # Create hub in NODE mode
    hub = Nng_bus_hub(bus_address, mode=Nng_bus_hub.Mode.NODE)
    
    # Create background tasks for sending and receiving
    sender_task = asyncio.create_task(message_sender(hub))
    receiver_task = asyncio.create_task(message_receiver(hub))
    
    try:
        print("✅ Node starting...")
        print("🔌 Connecting to controller...")
        print("Press Ctrl+C to stop\n")
        
        # Start the hub (this will run until error or cancellation)
        await hub.start()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Keyboard interrupt received")
    except Exception as e:
        Logger.error(f"Node error: {e}")
    finally:
        print("🛑 Stopping node...")
        sender_task.cancel()
        receiver_task.cancel()
        
        try:
            await asyncio.gather(sender_task, receiver_task, return_exceptions=True)
        except Exception:
            pass
        
        print("✅ Node stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

