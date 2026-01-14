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


async def node_status(hub, start_time):
    """Task to periodically show node status and connection health."""
    from datetime import datetime
    
    # Wait a bit before starting
    await asyncio.sleep(2)
    
    while True:
        try:
            await asyncio.sleep(15)  # Status update every 15 seconds
            
            uptime = datetime.now() - start_time
            
            # Get connection health info
            health_info = hub.get_connection_health_info()
            is_healthy = health_info['is_healthy']
            seconds_since_activity = health_info['seconds_since_activity']
            
            print(f"\n{'='*60}")
            print(f"📊 NODE STATUS")
            print(f"{'='*60}")
            print(f"Status: ✅ Running")
            print(f"Uptime: {uptime.total_seconds():.1f}s")
            print(f"Mode: NODE")
            print()
            
            # Connection health status
            if is_healthy:
                print(f"Connection Health: ✅ HEALTHY")
                if seconds_since_activity is not None:
                    print(f"Last Activity: {seconds_since_activity:.1f}s ago")
            else:
                print(f"Connection Health: ⚠️  UNHEALTHY or NOT YET ESTABLISHED")
                if seconds_since_activity is not None:
                    print(f"Last Activity: {seconds_since_activity:.1f}s ago")
                else:
                    print(f"No activity detected yet")
            
            print(f"\nMessage Statistics:")
            print(f"  Sent: {health_info['messages_sent']}")
            print(f"  Received: {health_info['messages_received']}")
            print(f"  Pongs Sent: {hub._pong_count} (auto-responses to controller pings)")
            
            if not is_healthy and seconds_since_activity and seconds_since_activity > 30:
                print(f"\n⚠️  WARNING: No activity for {seconds_since_activity:.0f}s")
                print(f"   Connection to controller may be lost!")
            
            print(f"{'='*60}\n")
        except Exception as e:
            Logger.error(f"Error in node status: {e}")
            break


async def main():
    """Main function to run the bus hub node."""
    from datetime import datetime
    
    # Configure the address - must match the controller's address
    bus_address = "tcp://127.0.0.1:5555"
    
    print("=" * 60)
    print("📡 CUEMS Bus Hub Node Test")
    print("=" * 60)
    print(f"Address: {bus_address}")
    print(f"Mode: NODE (connecting)")
    print("-" * 60)
    
    # Create hub in NODE mode
    hub = Nng_bus_hub(bus_address, mode=Nng_bus_hub.Mode.NODE)
    
    # Auto-pong is enabled by default - node will automatically respond to controller pings
    print("✅ Auto-pong enabled (will respond to controller pings automatically)")
    
    # Track start time for uptime calculation
    start_time = datetime.now()
    
    # Create background tasks for sending, receiving, and status monitoring
    sender_task = asyncio.create_task(message_sender(hub))
    receiver_task = asyncio.create_task(message_receiver(hub))
    status_task = asyncio.create_task(node_status(hub, start_time))
    
    try:
        print("✅ Node starting...")
        print("🔌 Connecting to controller...")
        print("💡 Node status will be displayed every 15 seconds")
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
        status_task.cancel()
        
        try:
            await asyncio.gather(sender_task, receiver_task, status_task, return_exceptions=True)
        except Exception:
            pass
        
        print("✅ Node stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

