# OSC Players Hub - README

## What Is This?

The **OSC Players Hub** allows nodes to transmit multiple player structures to a controller over TCP/IPC. Each player has a unique ID and an OSC node tree that can be added, updated, or removed independently.

## Quick Example

### Start Controller (Terminal 1)
```bash
python test_osc_hub_controller.py
```

### Start Node (Terminal 2)
```bash
python test_osc_hub_node.py
```

Watch as players are added, updated, and removed in real-time!

## Basic Usage

### Node (Sends Players)

```python
import asyncio
import pyossia
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType

# Create players
device = pyossia.ossia.OSCDevice("Player1", "127.0.0.1", 10000, 10001)
device.add_node("/audio/volume").create_parameter(pyossia.ossia.ValueType.Float).value = 0.8

# Create hub
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.NODE)

async def main():
    # Start hub (sender is automatic)
    asyncio.create_task(hub.start())
    
    await asyncio.sleep(1)
    
    # Add player (automatically sent by base class)
    await hub.add_player("player_001", device.root_node, ActionType.ADD)
    
    # Update player later
    await hub.add_player("player_001", device.root_node, ActionType.UPDATE)
    
    # Remove player
    await hub.remove_player("player_001")

asyncio.run(main())
```

### Controller (Receives Players)

```python
import asyncio
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType

# Your storage
players = {}

def on_player(sender, player_id, node_data, action):
    if action == ActionType.REMOVE:
        players.pop(player_id, None)
    else:
        players[player_id] = {"sender": sender, "data": node_data}

# Create hub
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.CONTROLLER)
hub.set_player_received_callback(on_player)

async def main():
    asyncio.create_task(hub.start())
    asyncio.create_task(hub.start_player_receiver())
    
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
```

## Key Concepts

1. **Queue-Based**: Players are queued and sent asynchronously
2. **One Message Per Player**: Each player is transmitted separately
3. **No Auto-Storage**: You manage storage, hub handles transmission
4. **Per-Player Callbacks**: Controller receives callback for each player
5. **Independent Lifecycle**: Each player can be added/updated/removed independently

## Files

- `QUICK_START_OSC_PLAYERS.md` - Quick start guide
- `PLAYER_BASED_ARCHITECTURE.md` - Complete architecture documentation
- `CHANGES_SUMMARY.md` - List of changes from old API
- `test_osc_hub_controller.py` - Controller example
- `test_osc_hub_node.py` - Node example  
- `test_player_queue.py` - Unit tests

## Transport Options

**TCP (Default):**
```python
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=mode)
```

**IPC (Local Only):**
```python
hub = OscNodesHub("ipc:///tmp/osc_hub", mode=mode)
```

## Actions

- `ActionType.ADD` - First time sending a player
- `ActionType.UPDATE` - Player state changed
- `ActionType.SYNC` - Full sync/refresh
- `ActionType.REMOVE` - Player no longer exists

## Testing

```bash
# Run unit tests
python test_player_queue.py

# Run controller (terminal 1)
python test_osc_hub_controller.py

# Run node (terminal 2)
python test_osc_hub_node.py
```

## Documentation

- **Quick Start**: `QUICK_START_OSC_PLAYERS.md`
- **Architecture**: `PLAYER_BASED_ARCHITECTURE.md`  
- **Changes**: `CHANGES_SUMMARY.md`

## Support

For questions or issues, refer to the documentation files above.

