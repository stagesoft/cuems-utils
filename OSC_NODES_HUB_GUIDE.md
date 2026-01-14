# OSC Nodes Hub Guide

## Overview

The `OscNodesHub` class extends `Nng_bus_hub` to enable transmission of pyossia OSC node structures from nodes to a controller over a message bus. This allows distributed OSC devices to share their node hierarchies with a central controller.

## Key Features

- **Serialize/Deserialize** pyossia node structures to/from JSON
- **Transmit node trees** from nodes to controller
- **Track received structures** on the controller side
- **Action types** for different operations (ADD, REMOVE, UPDATE, SYNC)
- **Callbacks** for processing received node structures
- **Automatic storage** of node structures by sender

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Node 1        │      │   Node 2        │      │   Node 3        │
│  (OSC Device)   │      │  (OSC Device)   │      │  (OSC Device)   │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         │  Send node structures  │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Controller    │
                         │ (Receives nodes)│
                         └─────────────────┘
```

## Usage

### Controller Side

The controller listens for incoming node structures and stores them:

```python
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType

# Create hub in CONTROLLER mode
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.CONTROLLER)

# Optional: Set callback for when nodes are received
def on_nodes_received(sender: str, node_data: dict):
    print(f"Received nodes from {sender}")
    # Process the node data...

hub.set_nodes_received_callback(on_nodes_received)

# Start the hub and receive node operations
async def main():
    # Start hub communication
    await hub.start()
    
    # OR manually receive and process operations
    while True:
        operation = await hub.get_node_operation()
        if operation:
            print(f"Action: {operation.action}")
            print(f"Sender: {operation.sender}")
            print(f"Node data: {operation.node_data}")

# Access stored node structures
stored_nodes = hub.get_stored_nodes()
# Or get nodes from specific sender
sender_nodes = hub.get_stored_nodes(sender="192.168.1.100")
```

### Node Side

Nodes create OSC device structures and send them to the controller:

```python
import pyossia
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType

# Create OSC device with node structure
device = pyossia.ossia.OSCDevice("MyDevice", "127.0.0.1", 10000, 10001)
audio = device.add_node("/audio")
volume = audio.add_node("/volume")
volume_param = volume.create_parameter(pyossia.ossia.ValueType.Float)
volume_param.value = 0.75

# Get the root node
device_root = device.root_node

# Create hub in NODE mode
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=OscNodesHub.Mode.NODE)

async def main():
    # Start hub in background
    asyncio.create_task(hub.start())
    
    # Send initial node structure
    await asyncio.sleep(1)  # Wait for connection
    await hub.send_node_structure(device_root, action=ActionType.SYNC)
    
    # Later, send updates
    await hub.send_node_structure(device_root, action=ActionType.UPDATE)
```

## ActionType Options

- **`ActionType.SYNC`**: Full synchronization of the node tree
- **`ActionType.ADD`**: Add new nodes to the structure
- **`ActionType.UPDATE`**: Update existing node structure
- **`ActionType.REMOVE`**: Remove nodes from the structure

## Node Serialization

The `serialize_node()` method converts a pyossia node tree to a JSON-serializable dictionary:

```python
node_dict = OscNodesHub.serialize_node(device_root)
# Result:
# {
#     "name": "MyDevice",
#     "children": [
#         {
#             "name": "audio",
#             "children": [
#                 {
#                     "name": "volume",
#                     "parameter": {
#                         "access": "GET_SET",
#                         "bounding": "FREE",
#                         "type": "FLOAT",
#                         "value": 0.75
#                     },
#                     "children": []
#                 }
#             ],
#             "parameter": null
#         }
#     ],
#     "parameter": null
# }
```

## Node Deserialization

The `deserialize_node()` method reconstructs pyossia nodes from a dictionary:

```python
# Requires a parent node to attach to
parent_device = pyossia.ossia.OSCDevice("Parent", "127.0.0.1", 11000, 11001)
parent_root = parent_device.root_node

# Deserialize received node data
reconstructed = OscNodesHub.deserialize_node(node_dict, parent_root)
```

## Message Format

Node structures are transmitted as JSON messages with this format:

```json
{
    "__type__": "osc_nodes",
    "action": "sync",
    "node_data": {
        "name": "device_name",
        "children": [...],
        "parameter": {...}
    }
}
```

## Complete Example

### Running the Controller

```bash
python test_osc_hub_controller.py
```

### Running a Node

In another terminal:

```bash
python test_osc_hub_node.py
```

You can run multiple nodes simultaneously to see how the controller tracks all of them.

## API Reference

### OscNodesHub

**Constructor:**
```python
OscNodesHub(hub_address: str, mode: Mode = Mode.CONTROLLER)
```

**Methods:**

- `serialize_node(node)` - Static method to serialize a pyossia node
- `deserialize_node(node_data, parent_node)` - Static method to deserialize to pyossia nodes
- `send_node_structure(root_node, action)` - Send node structure to bus
- `get_node_operation()` - Get next node operation from queue
- `receive_and_store_nodes()` - Continuously receive and store nodes (async loop)
- `get_stored_nodes(sender=None)` - Get stored node structures
- `set_nodes_received_callback(callback)` - Set callback for received nodes

**Inherited from Nng_bus_hub:**

- `start()` - Start the hub communication
- `send_message(message)` - Send a message to the bus
- `get_message()` - Get a message from the bus
- `get_active_connections()` - Get list of active connections
- `is_connection_healthy()` - Check connection health
- `enable_auto_ping()` - Enable automatic ping/pong

### NodeOperation

Data class representing a node operation:

```python
@dataclass
class NodeOperation:
    action: ActionType       # The action type (ADD/REMOVE/UPDATE/SYNC)
    node_data: dict         # The serialized node structure
    sender: str             # The sender identifier
```

## Transport Options

The hub supports both TCP and IPC transports:

**TCP (Network):**
```python
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=mode)
# Can communicate over network, use actual IP addresses for remote nodes
hub = OscNodesHub("tcp://192.168.1.100:5555", mode=mode)
```

**IPC (Local):**
```python
hub = OscNodesHub("ipc:///tmp/osc_hub", mode=mode)
# Faster for local-only communication, uses Unix sockets
```

The examples use TCP by default for flexibility and network capability.

## Notes

- Node structures are automatically stored on the controller side by sender identifier
- The serialization captures node hierarchy, parameters, values, and metadata
- Connection health tracking is inherited from `Nng_bus_hub`
- Supports both IPC and TCP transport (via pynng)
- TCP allows communication across network interfaces
- Thread-safe and async-first design

## Limitations

- Parameter type deserialization defaults to `Float` (may need manual type handling)
- Some pyossia parameter properties may not serialize perfectly
- Large node trees may have performance considerations

