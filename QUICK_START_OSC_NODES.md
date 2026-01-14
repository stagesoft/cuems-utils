# Quick Start: OSC Nodes Hub

## Installation

The `OscNodesHub` is now part of the `cuemsutils.tools` package.

```python
from cuemsutils.tools import OscNodesHub, ActionType
```

## 30-Second Example

### Node (Sender):
```python
import asyncio
import pyossia
from cuemsutils.tools import OscNodesHub, ActionType

# Create OSC device
device = pyossia.ossia.OSCDevice("MyDevice", "127.0.0.1", 10000, 10001)
volume = device.add_node("/audio/volume")
volume.create_parameter(pyossia.ossia.ValueType.Float).value = 0.8

# Create hub and send
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.NODE)

async def run():
    asyncio.create_task(hub.start())
    await asyncio.sleep(1)
    await hub.send_node_structure(device.root_node, ActionType.SYNC)

asyncio.run(run())
```

### Controller (Receiver):
```python
import asyncio
from cuemsutils.tools import OscNodesHub

# Create hub
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.CONTROLLER)

async def run():
    # Start hub and receive
    asyncio.create_task(hub.start())
    
    while True:
        op = await hub.get_node_operation()
        if op:
            print(f"Received from {op.sender}: {op.node_data}")

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

### Or Run Example:
```bash
python OSC_NODES_EXAMPLE.py
```

## Key Methods

| Method | Description |
|--------|-------------|
| `serialize_node(node)` | Convert pyossia node to dict |
| `deserialize_node(data, parent)` | Convert dict to pyossia node |
| `send_node_structure(node, action)` | Send node tree to bus |
| `get_node_operation()` | Receive node operation |
| `get_stored_nodes(sender)` | Get received nodes |

## Common Patterns

### Pattern 1: Send Updates Periodically
```python
async def periodic_sync(hub, root_node):
    while True:
        await asyncio.sleep(10)
        await hub.send_node_structure(root_node, ActionType.UPDATE)
```

### Pattern 2: Use Callback on Receive
```python
def on_receive(sender, node_data):
    print(f"Got nodes from {sender}")

hub.set_nodes_received_callback(on_receive)
```

### Pattern 3: Store and Retrieve
```python
# Nodes are auto-stored
all_nodes = hub.get_stored_nodes()
specific = hub.get_stored_nodes(sender="192.168.1.100")
```

## More Info

- Full Guide: `OSC_NODES_HUB_GUIDE.md`
- Implementation Details: `OSC_NODES_IMPLEMENTATION_SUMMARY.md`
- Examples: `OSC_NODES_EXAMPLE.py`

