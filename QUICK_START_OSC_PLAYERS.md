# Quick Start: OSC Players Hub

## Overview

The `OscNodesHub` transmits **multiple players** from nodes to controller. Each player has:
- A unique `player_id`
- An OSC `root_node` structure
- Independent lifecycle (ADD, UPDATE, REMOVE)

## Installation

```python
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType, PlayerOperation
```

## 30-Second Example

### Node (Sends Players):
```python
import asyncio
import pyossia
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType

# Create players
device1 = pyossia.ossia.OSCDevice("Player1", "127.0.0.1", 10000, 10001)
device1.add_node("/audio/volume").create_parameter(pyossia.ossia.ValueType.Float).value = 0.8

device2 = pyossia.ossia.OSCDevice("Player2", "127.0.0.1", 11000, 11001)
device2.add_node("/video/opacity").create_parameter(pyossia.ossia.ValueType.Float).value = 1.0

# Create hub
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.NODE)

async def run():
    # Start hub (base class sender automatically handles transmission)
    asyncio.create_task(hub.start())
    
    await asyncio.sleep(1)
    
    # Add players (they'll be sent automatically by base class)
    await hub.add_player("player_001", device1.root_node, ActionType.ADD)
    await hub.add_player("player_002", device2.root_node, ActionType.ADD)
    
    # Later: update player
    await hub.add_player("player_001", device1.root_node, ActionType.UPDATE)
    
    # Later: remove player
    await hub.remove_player("player_002")

asyncio.run(run())
```

### Controller (Receives Players):
```python
import asyncio
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType

# Application manages storage
players = {}

def on_player(sender, player_id, node_data, action):
    if action == ActionType.REMOVE:
        players.pop(player_id, None)
        print(f"❌ Removed {player_id}")
    else:
        players[player_id] = {"sender": sender, "data": node_data}
        print(f"✅ Added/Updated {player_id} from {sender}")

hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.CONTROLLER)
hub.set_player_received_callback(on_player)

async def run():
    asyncio.create_task(hub.start())
    asyncio.create_task(hub.start_player_receiver())
    while True:
        await asyncio.sleep(1)

asyncio.run(run())
```

## Try It Now

### Terminal 1 - Start Controller:
```bash
python test_osc_hub_controller.py
```

### Terminal 2 - Start Node:
```bash
python test_osc_hub_node.py
```

Watch as players are added, updated, and removed!

## Key Methods

### Node Side

| Method | Description |
|--------|-------------|
| `add_player(id, node, action)` | Queue player to send (automatic) |
| `remove_player(id)` | Queue player removal (automatic) |

### Controller Side

| Method | Description |
|--------|-------------|
| `set_player_received_callback(cb)` | Set callback for players |
| `get_player_operation()` | Manually get next operation |
| `start_player_receiver()` | Start background receiver task |

### Static Methods

| Method | Description |
|--------|-------------|
| `serialize_node(node)` | Convert pyossia node to dict |
| `deserialize_node(data, parent)` | Convert dict to pyossia node |

## Common Patterns

### Pattern 1: Add Players as They Appear
```python
async def add_players_dynamically(hub, player_queue):
    """Add players to hub as they become available."""
    while True:
        player_id, device = await player_queue.get()
        await hub.add_player(player_id, device.root_node, ActionType.ADD)
```

### Pattern 2: Periodic Player Updates
```python
async def update_players(hub, players_dict):
    """Periodically update all active players."""
    while True:
        await asyncio.sleep(10)
        for player_id, device in players_dict.items():
            await hub.add_player(player_id, device.root_node, ActionType.UPDATE)
```

### Pattern 3: Controller Storage by Sender
```python
# Track which players belong to which node
storage = {}  # {sender: {player_id: node_data}}

def on_player(sender, player_id, node_data, action):
    if sender not in storage:
        storage[sender] = {}
    
    if action == ActionType.REMOVE:
        storage[sender].pop(player_id, None)
    else:
        storage[sender][player_id] = node_data
```

### Pattern 4: Controller Storage by Player
```python
# Track all players globally
players = {}  # {player_id: {sender, node_data}}

def on_player(sender, player_id, node_data, action):
    if action == ActionType.REMOVE:
        players.pop(player_id, None)
    else:
        players[player_id] = {
            "sender": sender,
            "node_data": node_data
        }
```

## Action Types

| Action | When to Use | node_data |
|--------|------------|-----------|
| `ADD` | First time sending player | Required |
| `UPDATE` | Player state changed | Required |
| `REMOVE` | Player no longer exists | None |

## Important Notes

- ⚠️ **No Auto-Storage**: The hub does NOT store players. Your app manages storage.
- ✅ **Queue-Based**: Players are queued and sent asynchronously
- ✅ **Per-Player Messages**: Each player = one message
- ✅ **Player ID Scope**: Unique globally, guaranteed unique locally per node
- ✅ **Callback Per Player**: Controller callback invoked for each player operation

## Message Format

```json
{
    "__type__": "osc_player",
    "player_id": "player_123",
    "action": "add",
    "node_data": { "name": "...", "children": [...] }
}
```

For REMOVE:
```json
{
    "__type__": "osc_player",
    "player_id": "player_123",
    "action": "remove",
    "node_data": null
}
```

## More Info

- Full Architecture: `PLAYER_BASED_ARCHITECTURE.md`
- Transport Options: Both TCP and IPC supported
- Examples: `test_osc_hub_controller.py` and `test_osc_hub_node.py`

