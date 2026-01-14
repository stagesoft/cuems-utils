#!/usr/bin/env python3
"""
Test script for OscNodesHub in CONTROLLER mode.
This controller receives OSC player structures from nodes and processes them.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType
from cuemsutils.log import Logger
import json


# Storage for players (controller manages this)
players_storage = {}  # {player_id: {sender, node_data, last_update}}


def on_player_received(sender: str, player_id: str, node_data: dict, action: ActionType):
    """Callback invoked when player operations are received."""
    print(f"\n🎯 Player operation received:")
    print(f"   Sender: {sender}")
    print(f"   Player ID: {player_id}")
    print(f"   Action: {action.value}")
    
    if action == ActionType.REMOVE:
        # Remove player from storage
        if player_id in players_storage:
            del players_storage[player_id]
            print(f"   ❌ Removed player {player_id}")
        else:
            print(f"   ⚠️  Player {player_id} not found in storage")
    else:
        # Add or update player
        players_storage[player_id] = {
            "sender": sender,
            "node_data": node_data,
            "action": action.value
        }
        print(f"   ✅ {'Updated' if action == ActionType.UPDATE else 'Added'} player {player_id}")
        if node_data:
            print(f"   Node: {node_data.get('name', 'unknown')}")
    
    print(f"   📊 Total players in storage: {len(players_storage)}")
    print("-" * 60)


async def status_display(hub):
    """Task to periodically display connection and player status."""
    while True:
        try:
            await asyncio.sleep(15)
            
            connections = hub.get_active_connections()
            print(f"\n📡 Status Report:")
            print(f"   Active connections: {len(connections)}")
            for conn in connections:
                print(f"      - {conn.sender} (since {conn.connected_at.strftime('%H:%M:%S')})")
            
            print(f"   Total players: {len(players_storage)}")
            for player_id, info in players_storage.items():
                node_name = info['node_data'].get('name', 'unknown') if info['node_data'] else 'N/A'
                print(f"      - {player_id} from {info['sender']} ({node_name})")
            
            health = hub.get_connection_health_info()
            print(f"   Health: {'✅ Healthy' if health['is_healthy'] else '❌ Unhealthy'}")
            print(f"   Messages RX: {health['messages_received']} | TX: {health['messages_sent']}")
            print("-" * 60)
            
        except Exception as e:
            Logger.error(f"Error displaying status: {e}")


async def main():
    """Main function to run the OSC players hub controller."""
    # Configure the address - using TCP for network communication
    bus_address = "tcp://127.0.0.1:5555"
    
    print("=" * 60)
    print("🎛️  CUEMS OSC Players Hub Controller")
    print("=" * 60)
    print(f"Address: {bus_address}")
    print(f"Mode: CONTROLLER (listening)")
    print("-" * 60)
    
    # Create OSC hub in CONTROLLER mode
    hub = OscNodesHub(bus_address, mode=OscNodesHub.Mode.CONTROLLER)
    
    # Set callback for when players are received
    hub.set_player_received_callback(on_player_received)
    
    # Enable auto-ping to keep connections alive
    hub.enable_auto_ping(interval=10.0, inactivity_threshold=5.0)
    
    # Create background tasks
    receiver_task = asyncio.create_task(hub.start_player_receiver())
    status_task = asyncio.create_task(status_display(hub))
    
    try:
        print("✅ Controller starting...")
        print("📡 Waiting for node connections...")
        print("🎵 Ready to receive OSC player structures...")
        print("Press Ctrl+C to stop\n")
        
        # Start the hub (this will run until error or cancellation)
        await hub.start()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Keyboard interrupt received")
    except Exception as e:
        Logger.error(f"Controller error: {e}")
    finally:
        print("🛑 Stopping controller...")
        receiver_task.cancel()
        status_task.cancel()
        
        try:
            await asyncio.gather(receiver_task, status_task, return_exceptions=True)
        except Exception:
            pass
        
        # Display final summary
        print(f"\n📊 Final Summary:")
        print(f"   Total players received: {len(players_storage)}")
        for player_id, info in players_storage.items():
            node_name = info['node_data'].get('name', 'unknown') if info['node_data'] else 'N/A'
            print(f"   - {player_id}: {node_name} from {info['sender']}")
        
        print("\n✅ Controller stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
