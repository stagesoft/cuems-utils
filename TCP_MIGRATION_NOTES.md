# TCP Migration Notes

## Summary

All OscNodesHub examples have been updated to use TCP transport instead of IPC for better network compatibility.

## Changes Made

### Transport Address Changes

**Before (IPC):**
```python
bus_address = "ipc:///tmp/cuems_osc_hub_test"
```

**After (TCP):**
```python
bus_address = "tcp://127.0.0.1:5555"
```

### Files Updated

1. **test_osc_hub_controller.py**
   - Changed from IPC to TCP on port 5555
   - Controller listens on `tcp://127.0.0.1:5555`

2. **test_osc_hub_node.py**
   - Changed from IPC to TCP on port 5555
   - Nodes connect to `tcp://127.0.0.1:5555`

3. **OSC_NODES_EXAMPLE.py**
   - Updated transmission demonstration text to mention TCP
   - Added note about multi-node tracking

4. **OSC_NODES_HUB_GUIDE.md**
   - Updated all code examples to use TCP
   - Added "Transport Options" section explaining TCP vs IPC

5. **QUICK_START_OSC_NODES.md**
   - Updated quick start examples to use TCP

6. **OSC_NODES_IMPLEMENTATION_SUMMARY.md**
   - Updated implementation examples to use TCP

## Benefits of TCP

✅ **Network Communication**: Nodes can connect from different machines
✅ **Flexibility**: Can specify any IP address and port
✅ **Standard Protocol**: More familiar to network developers
✅ **Remote Testing**: Can test across network boundaries

## Using IPC (If Preferred)

IPC is still fully supported and can be faster for local-only communication:

```python
# Just change the address to IPC format
bus_address = "ipc:///tmp/cuems_osc_hub"
```

## Port Configuration

The default TCP port is **5555**. To use a different port:

**Controller:**
```python
hub = OscNodesHub("tcp://127.0.0.1:6000", mode=OscNodesHub.Mode.CONTROLLER)
```

**Node:**
```python
hub = OscNodesHub("tcp://127.0.0.1:6000", mode=OscNodesHub.Mode.NODE)
```

## Network Usage Examples

### Local Network
```python
# Controller on 192.168.1.100
hub = OscNodesHub("tcp://0.0.0.0:5555", mode=OscNodesHub.Mode.CONTROLLER)

# Node connects from another machine
hub = OscNodesHub("tcp://192.168.1.100:5555", mode=OscNodesHub.Mode.NODE)
```

### Localhost Only
```python
# Both on same machine
hub = OscNodesHub("tcp://127.0.0.1:5555", mode=mode)
```

## Testing

All tests pass successfully:
- ✅ Example script runs without errors
- ✅ No linter errors
- ✅ Serialization/deserialization works correctly

## Backward Compatibility

The underlying `Nng_bus_hub` class supports both IPC and TCP, so existing code using IPC will continue to work without changes.

