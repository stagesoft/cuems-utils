## Player-Based OSC Nodes Hub Architecture

### Overview

The `OscNodesHub` has been redesigned to handle multiple **players** per node, where each player has:
- A unique `player_id` (globally unique, but guaranteed locally unique per node)
- An OSC `root_node` structure
- Individual lifecycle (ADD, UPDATE, REMOVE)

### Key Design Principles

1. **Queue-Based Transmission**: Nodes queue players to send, class transmits them
2. **One Message Per Player**: Each player is sent in a separate message
3. **No Storage Management**: The class doesn't store players, only queues and transmits
4. **Per-Player Callbacks**: Controller receives callback for each player operation
5. **Independent Player Lifecycle**: Players can be added, updated, or removed individually

### Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                     NODE                            │
│                                                     │
│  Application Logic                                  │
│       │                                             │
│       ├─> add_player(player_1, node_tree)          │
│       ├─> add_player(player_2, node_tree)          │
│       ├─> remove_player(player_1)                  │
│       └─> add_player(player_3, node_tree, UPDATE)  │
│                     │                               │
│                     ▼                               │
│           players_to_send Queue                     │
│                     │                               │
│                     ▼                               │
│           start_player_sender()                     │
│            (background task)                        │
│                     │                               │
└─────────────────────┼───────────────────────────────┘
                      │
                      │ TCP/IPC Bus
                      ▼
┌─────────────────────────────────────────────────────┐
│                  CONTROLLER                         │
│                                                     │
│           start_player_receiver()                   │
│            (background task)                        │
│                     │                               │
│                     ▼                               │
│         get_player_operation()                      │
│                     │                               │
│                     ▼                               │
│    Callback: on_player_received()                   │
│      (sender, player_id, node_data, action)         │
│                     │                               │
│                     ▼                               │
│         Application Storage/Processing              │
│         (managed by application)                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Message Protocol

Each player is transmitted as a JSON message:

**ADD/UPDATE/SYNC:**
```json
{
    "__type__": "osc_player",
    "player_id": "player_abc123",
    "action": "add",
    "node_data": {
        "name": "PlayerDevice",
        "children": [...],
        "parameter": null
    }
}
```

**REMOVE:**
```json
{
    "__type__": "osc_player",
    "player_id": "player_abc123",
    "action": "remove",
    "node_data": null
}
```

### Node Side Usage

```python
import asyncio
import pyossia
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType

# Create hub
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.NODE)

# Create players
device1 = pyossia.ossia.OSCDevice("Player1", "127.0.0.1", 10000, 10001)
device2 = pyossia.ossia.OSCDevice("Player2", "127.0.0.1", 11000, 11001)

async def main():
    # Start the hub (base class sender automatically processes outgoing queue)
    asyncio.create_task(hub.start())
    
    await asyncio.sleep(1)  # Wait for connection
    
    # Add players (automatically queued and sent by base class)
    await hub.add_player("player_1", device1.root_node, ActionType.ADD)
    await hub.add_player("player_2", device2.root_node, ActionType.ADD)
    
    # Later: update a player
    await hub.add_player("player_1", device1.root_node, ActionType.UPDATE)
    
    # Later: remove a player
    await hub.remove_player("player_2")
```

### Controller Side Usage

```python
import asyncio
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType

# Storage (managed by your application)
players = {}  # {player_id: {sender, node_data, ...}}

def on_player_received(sender, player_id, node_data, action):
    """Called for each player operation received."""
    if action == ActionType.REMOVE:
        if player_id in players:
            del players[player_id]
            print(f"Removed player {player_id}")
    else:
        players[player_id] = {
            "sender": sender,
            "node_data": node_data,
            "action": action
        }
        print(f"Added/Updated player {player_id} from {sender}")

# Create hub
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.CONTROLLER)
hub.set_player_received_callback(on_player_received)

async def main():
    # Start the hub and player receiver
    asyncio.create_task(hub.start())
    asyncio.create_task(hub.start_player_receiver())
    
    # Run forever
    while True:
        await asyncio.sleep(1)
```

### API Reference

#### Node Side

**`add_player(player_id, root_node, action=ActionType.ADD)`**
- Queues a player to be sent to the controller
- `player_id`: Unique string identifier for the player
- `root_node`: pyossia Node object (the player's device root)
- `action`: ADD or UPDATE

**`remove_player(player_id)`**
- Queues a player removal
- `player_id`: The player to remove

**Note:** Sending is automatic! The base class `_send_handler()` processes the outgoing queue.
No need for a separate sender task.

#### Controller Side

**`set_player_received_callback(callback)`**
- Set callback for received players
- Signature: `callback(sender, player_id, node_data, action)`
- `node_data` is `None` for REMOVE operations

**`get_player_operation()`** (async)
- Manually get next player operation from queue
- Returns: `PlayerOperation` or `None`

**`start_player_receiver()`** (async)
- Background task that receives players and calls callback
- Run as: `asyncio.create_task(hub.start_player_receiver())`

### PlayerOperation Dataclass

```python
@dataclass
class PlayerOperation:
    action: ActionType           # ADD, REMOVE, or UPDATE
    player_id: str              # Unique player identifier
    node_data: Optional[dict]   # None for REMOVE
    sender: str                 # Node that sent this
```

### Example: Multi-Player Scenario

```python
# Node has 3 players that become available over time

# Time 0: Player 1 appears
await hub.add_player("player_001", player1_device.root_node, ActionType.ADD)

# Time 5s: Player 2 appears
await hub.add_player("player_002", player2_device.root_node, ActionType.ADD)

# Time 10s: Player 1 updates their state
await hub.add_player("player_001", player1_device.root_node, ActionType.UPDATE)

# Time 15s: Player 3 appears
await hub.add_player("player_003", player3_device.root_node, ActionType.ADD)

# Time 20s: Player 2 leaves
await hub.remove_player("player_002")
```

Each of these operations is queued and sent as a separate message to the controller.

### Storage Responsibility

⚠️ **Important**: The `OscNodesHub` class does NOT store players. Storage is the responsibility of the application using the hub.

**Controller Example:**
```python
# Application manages storage
players_by_id = {}      # {player_id: data}
players_by_sender = {}  # {sender: [player_ids]}

def on_player_received(sender, player_id, node_data, action):
    if action == ActionType.REMOVE:
        # Remove from storage
        if player_id in players_by_id:
            del players_by_id[player_id]
        if sender in players_by_sender:
            players_by_sender[sender].remove(player_id)
    else:
        # Add/update in storage
        players_by_id[player_id] = {
            "sender": sender,
            "node_data": node_data,
            "timestamp": datetime.now()
        }
        if sender not in players_by_sender:
            players_by_sender[sender] = []
        if player_id not in players_by_sender[sender]:
            players_by_sender[sender].append(player_id)
```

### Benefits of This Architecture

1. **Scalability**: Each node can manage many players independently
2. **Flexibility**: Players can join/leave dynamically
3. **Clear Separation**: Transport layer (hub) vs storage/logic (application)
4. **Efficient**: Only changed players need to be transmitted
5. **Simple**: One message = one player operation

### Migration from Old API

**Old (Single Node):**
```python
await hub.send_node_structure(device.root_node, ActionType.SYNC)
```

**New (Multiple Players):**
```python
await hub.add_player("player_123", device.root_node, ActionType.ADD)
asyncio.create_task(hub.start_player_sender())
```

The new API is more flexible and scales to handle multiple players per node.

