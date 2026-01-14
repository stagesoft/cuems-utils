#!/usr/bin/env python3
"""
Test script for OscNodesHub in NODE mode.
This node creates multiple OSC player structures and sends them to the controller.
"""

import asyncio
import sys
from pathlib import Path
import random
import uuid

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType
from cuemsutils.log import Logger
import pyossia


def create_player_device(player_name: str, base_port: int):
    """Create a sample OSC device for a player."""
    device = pyossia.ossia.OSCDevice(player_name, "127.0.0.1", base_port, base_port + 1)
    
    # Create audio section
    audio = device.add_node("/audio")
    
    volume = audio.add_node("/volume")
    volume_param = volume.create_parameter(pyossia.ossia.ValueType.Float)
    volume_param.value = random.uniform(0.5, 1.0)
    
    pan = audio.add_node("/pan")
    pan_param = pan.create_parameter(pyossia.ossia.ValueType.Float)
    pan_param.value = random.uniform(-1.0, 1.0)
    
    # Create video section
    video = device.add_node("/video")
    
    brightness = video.add_node("/brightness")
    brightness_param = brightness.create_parameter(pyossia.ossia.ValueType.Float)
    brightness_param.value = random.uniform(0.5, 1.0)
    
    opacity = video.add_node("/opacity")
    opacity_param = opacity.create_parameter(pyossia.ossia.ValueType.Float)
    opacity_param.value = random.uniform(0.8, 1.0)
    
    return device


async def add_players_periodically(hub, players):
    """Add new players periodically."""
    await asyncio.sleep(2)  # Wait for connection to establish
    
    # Add initial players
    print("\n📤 Adding initial players...")
    for player_id, device in players.items():
        await hub.add_player(player_id, device.root_node, action=ActionType.ADD)
        print(f"   ✅ Queued player {player_id}")
        await asyncio.sleep(0.5)  # Stagger the sends
    
    print(f"\n✅ All {len(players)} players queued for sending")
    
    # Periodically update players
    counter = 0
    while True:
        try:
            await asyncio.sleep(20)
            counter += 1
            
            # Update a random player
            if players:
                player_id = random.choice(list(players.keys()))
                device = players[player_id]
                print(f"\n🔄 Update #{counter}: Updating player {player_id}...")
                await hub.add_player(player_id, device.root_node, action=ActionType.UPDATE)
                
        except Exception as e:
            Logger.error(f"Error updating players: {e}")


async def remove_player_later(hub, players):
    """Remove a player after some time."""
    await asyncio.sleep(30)
    
    if players:
        # Remove one player
        player_id = random.choice(list(players.keys()))
        print(f"\n❌ Removing player {player_id}...")
        await hub.remove_player(player_id)
        del players[player_id]
        print(f"   ✅ Player {player_id} removal queued")


async def monitor_health(hub):
    """Monitor connection health."""
    while True:
        try:
            await asyncio.sleep(25)
            
            health = hub.get_connection_health_info()
            print(f"\n💓 Connection Health:")
            print(f"   Status: {'✅ Healthy' if health['is_healthy'] else '❌ Unhealthy'}")
            print(f"   Messages TX: {health['messages_sent']} | RX: {health['messages_received']}")
            if health['seconds_since_activity'] is not None:
                print(f"   Last activity: {health['seconds_since_activity']:.1f}s ago")
            
        except Exception as e:
            Logger.error(f"Error monitoring health: {e}")


async def main():
    """Main function to run the OSC players hub node."""
    # Configure the address - must match the controller's address
    bus_address = "tcp://127.0.0.1:5555"
    
    print("=" * 60)
    print("📡 CUEMS OSC Players Hub Node")
    print("=" * 60)
    print(f"Address: {bus_address}")
    print(f"Mode: NODE (connecting)")
    print("-" * 60)
    
    # Create multiple players
    print("\n🎵 Creating sample player OSC structures...")
    players = {}
    num_players = 3
    
    for i in range(num_players):
        player_id = f"player_{uuid.uuid4().hex[:8]}"
        player_name = f"Player{i+1}"
        base_port = random.randint(20000, 30000)
        
        device = create_player_device(player_name, base_port)
        players[player_id] = device
        
        print(f"   ✅ Created {player_name} (ID: {player_id})")
    
    print(f"\n✅ Created {len(players)} players")
    print("-" * 60)
    
    # Create OSC hub in NODE mode
    hub = OscNodesHub(bus_address, mode=OscNodesHub.Mode.NODE)
    
    # Enable auto-pong to respond to controller pings
    hub.enable_auto_pong()
    
    # Create background tasks
    add_players_task = asyncio.create_task(add_players_periodically(hub, players))
    remove_task = asyncio.create_task(remove_player_later(hub, players))
    health_task = asyncio.create_task(monitor_health(hub))
    
    try:
        print("\n✅ Node starting...")
        print("🔌 Connecting to controller...")
        print("📤 Using base class sender (automatic)")
        print("Press Ctrl+C to stop\n")
        
        # Start the hub (this will run until error or cancellation)
        # The base class sender automatically processes the outgoing queue
        await hub.start()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Keyboard interrupt received")
    except Exception as e:
        Logger.error(f"Node error: {e}")
    finally:
        print("🛑 Stopping node...")
        add_players_task.cancel()
        remove_task.cancel()
        health_task.cancel()
        
        try:
            await asyncio.gather(
                add_players_task, remove_task, health_task,
                return_exceptions=True
            )
        except Exception:
            pass
        
        print("✅ Node stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
