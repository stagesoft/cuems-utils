# Automatic Ping/Pong Connection Verification

The `Nng_bus_hub` class includes an automatic ping/pong mechanism that allows controllers to verify node connections even during periods of inactivity.

## Overview

**Problem:** In periods of no user message traffic, it's difficult to detect if connections are still alive.

**Solution:** The controller automatically sends "ping" messages when there's been no recent activity. Nodes automatically respond with "pong" messages, confirming the connection is alive.

## Features

- ✅ **Automatic Ping** - Controller sends pings during inactivity
- ✅ **Automatic Pong** - Nodes respond automatically (enabled by default)
- ✅ **Transparent** - Ping/pong messages don't appear in your message queue
- ✅ **Configurable** - Adjust intervals and thresholds
- ✅ **Tracked** - Ping/pong counts available for monitoring

## Quick Start

### Controller Setup

```python
from cuemsutils.tools.CommunicatorServices import Nng_bus_hub

# Create controller
hub = Nng_bus_hub("tcp://0.0.0.0:5555", mode=Nng_bus_hub.Mode.CONTROLLER)

# Enable auto-ping
hub.enable_auto_ping(
    interval=10.0,              # Check every 10 seconds
    inactivity_threshold=5.0    # Ping if no activity for 5 seconds
)

await hub.start()
```

### Node Setup

```python
# Create node
node = Nng_bus_hub("tcp://127.0.0.1:5555", mode=Nng_bus_hub.Mode.NODE)

# Auto-pong is enabled by default - no configuration needed!
# Nodes will automatically respond to controller pings

await node.start()
```

## How It Works

### Controller Side

1. **Monitoring Loop** runs every `interval` seconds
2. **Check Inactivity** - Has it been > `inactivity_threshold` since last message sent?
3. **Send Ping** - If inactive, broadcast ping message to all nodes
4. **Receive Pongs** - Nodes respond, confirming they're alive
5. **Track Activity** - Pong responses count as activity

### Node Side

1. **Receive Ping** - Detect incoming ping message
2. **Send Pong** - Automatically send pong response (if auto-pong enabled)
3. **Transparent** - Ping/pong don't interrupt normal message flow
4. **Track Stats** - Count pongs sent for monitoring

### Message Format

**Ping Message:**
```json
{
    "__type__": "ping",
    "timestamp": "2025-10-21T14:30:00.123456"
}
```

**Pong Message:**
```json
{
    "__type__": "pong",
    "timestamp": "2025-10-21T14:30:00.234567",
    "ping_timestamp": "2025-10-21T14:30:00.123456"
}
```

Messages with `__type__` field are handled internally and don't reach your message queue.

## API Reference

### Enable/Disable Auto-Ping (Controller)

```python
# Enable auto-ping
hub.enable_auto_ping(
    interval=10.0,              # How often to check for inactivity
    inactivity_threshold=5.0    # Send ping after this many seconds of inactivity
)

# Disable auto-ping
hub.disable_auto_ping()

# Manual ping
await hub.send_ping()  # Send ping immediately
```

### Enable/Disable Auto-Pong (Node)

```python
# Auto-pong is enabled by default

# Disable auto-pong (not recommended)
node.disable_auto_pong()

# Re-enable auto-pong
node.enable_auto_pong()
```

### Monitoring

```python
# Access ping/pong counts
print(f"Pings sent: {hub._ping_count}")
print(f"Pongs sent: {node._pong_count}")

# Check if connection is healthy (includes ping/pong activity)
if node.is_connection_healthy():
    print("✅ Connection is healthy")
```

## Configuration Examples

### Aggressive Keep-Alive (Quick Detection)

```python
# Ping every 5 seconds if no activity for 2 seconds
hub.enable_auto_ping(interval=5.0, inactivity_threshold=2.0)
```

**Use case:** Critical systems requiring quick connection failure detection

### Relaxed Keep-Alive (Reduce Traffic)

```python
# Ping every 60 seconds if no activity for 30 seconds
hub.enable_auto_ping(interval=60.0, inactivity_threshold=30.0)
```

**Use case:** Non-critical systems or high-traffic environments

### Balanced (Default Recommendation)

```python
# Ping every 10 seconds if no activity for 5 seconds
hub.enable_auto_ping(interval=10.0, inactivity_threshold=5.0)
```

**Use case:** Most applications

## Complete Example

```python
import asyncio
from cuemsutils.tools.CommunicatorServices import Nng_bus_hub

async def run_controller():
    """Controller with auto-ping enabled."""
    hub = Nng_bus_hub("tcp://0.0.0.0:5555", mode=Nng_bus_hub.Mode.CONTROLLER)
    
    # Enable ping/pong mechanism
    hub.enable_auto_ping(interval=10.0, inactivity_threshold=5.0)
    
    # Monitor ping/pong activity
    async def monitor_ping_pong():
        while True:
            await asyncio.sleep(30)
            print(f"📊 Pings sent: {hub._ping_count}")
    
    asyncio.create_task(monitor_ping_pong())
    
    await hub.start()

async def run_node():
    """Node with auto-pong (enabled by default)."""
    node = Nng_bus_hub("tcp://127.0.0.1:5555", mode=Nng_bus_hub.Mode.NODE)
    
    # Auto-pong is already enabled by default
    # Monitor pong responses
    async def monitor_pongs():
        while True:
            await asyncio.sleep(30)
            print(f"📊 Pongs sent: {node._pong_count}")
    
    asyncio.create_task(monitor_pongs())
    
    await node.start()

# Run controller or node
asyncio.run(run_controller())
```

## Interaction with Connection Health

The ping/pong mechanism integrates seamlessly with connection health monitoring:

```python
# Ping/pong messages count as activity
health = node.get_connection_health_info()

# If controller is pinging and node is ponging:
# - is_healthy will be True
# - seconds_since_activity will be small (< threshold)
# - messages_received will include pings
# - messages_sent will include pongs

print(f"Healthy: {health['is_healthy']}")
print(f"Last activity: {health['seconds_since_activity']:.1f}s ago")
```

## Troubleshooting

### No Pongs Received (Controller)

**Symptoms:** Controller sends pings but no pongs received

**Possible Causes:**
1. No nodes connected
2. Nodes have auto-pong disabled
3. Network connectivity issues
4. Nodes crashed/stopped

**Solutions:**
- Check `hub.get_connection_count()` 
- Verify nodes are running
- Check network connectivity
- Ensure nodes have auto-pong enabled

### Too Many Pings

**Symptoms:** Pings being sent too frequently

**Solutions:**
```python
# Increase inactivity threshold
hub.enable_auto_ping(interval=10.0, inactivity_threshold=15.0)

# Or increase check interval
hub.enable_auto_ping(interval=30.0, inactivity_threshold=5.0)

# Or disable if not needed
hub.disable_auto_ping()
```

### Pings Not Sent

**Symptoms:** No pings being sent despite inactivity

**Possible Causes:**
1. Auto-ping not enabled
2. There IS recent activity (messages being sent)
3. Auto-ping task not running

**Solutions:**
```python
# Verify auto-ping is enabled
hub.enable_auto_ping()

# Check if messages are being sent
print(f"Last message sent: {hub._last_message_sent}")

# Lower inactivity threshold
hub.enable_auto_ping(interval=10.0, inactivity_threshold=2.0)
```

## Best Practices

### 1. Always Enable Auto-Ping on Controllers

```python
# Controllers should enable auto-ping for connection verification
hub.enable_auto_ping()
```

### 2. Keep Auto-Pong Enabled on Nodes

```python
# Don't disable auto-pong unless you have a specific reason
# (it's enabled by default, just don't call disable_auto_pong())
```

### 3. Tune Based on Message Frequency

```python
# High-frequency messages: Relaxed ping
if average_message_interval < 5:
    hub.enable_auto_ping(interval=30.0, inactivity_threshold=10.0)

# Low-frequency messages: Aggressive ping  
if average_message_interval > 60:
    hub.enable_auto_ping(interval=10.0, inactivity_threshold=5.0)
```

### 4. Monitor Ping/Pong Stats

```python
# Periodically log stats for debugging
async def log_stats(hub):
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        logger.info(f"Ping/pong stats - Pings: {hub._ping_count}, Pongs: {hub._pong_count}")
```

### 5. Combine with Connection Health

```python
# Use both mechanisms together
hub.enable_auto_ping(interval=10.0, inactivity_threshold=5.0)

# Check health (will include ping/pong activity)
if not node.is_connection_healthy(activity_timeout=20.0):
    logger.warning("Connection unhealthy despite ping/pong!")
```

## Performance Considerations

### Bandwidth

Ping/pong messages are small (~100 bytes each):
- At 10-second intervals: ~8.6 KB/day per node
- Negligible bandwidth impact

### CPU

Minimal CPU overhead:
- Periodic timer checks
- JSON parsing for ping/pong detection
- No impact on normal message throughput

### Recommendations

- **Most systems:** Default settings are fine
- **Bandwidth-constrained:** Increase intervals (30-60s)
- **Quick detection needed:** Decrease to 5s intervals
- **Many nodes (100+):** Increase thresholds to reduce broadcast traffic

## Testing the Ping/Pong Mechanism

### Test 1: Verify Ping/Pong Works

```bash
# Terminal 1: Start controller with auto-ping
python test_bus_controller.py

# Terminal 2: Start node
python test_bus_node.py

# Stop sending normal messages
# Within 5 seconds, you should see in logs:
# Controller: "Sending ping due to inactivity"
# Node: "Received ping, sent pong"
```

### Test 2: Verify Connection Health with Ping/Pong

```bash
# Start both controller and node
# Stop controller's normal message sending
# Wait and observe - node should stay healthy due to pings/pongs
# Node status should show "Connection Health: ✅ HEALTHY"
```

### Test 3: Node Disconnection Detection

```bash
# Start controller and node
# Kill the node
# Controller should continue sending pings (no pongs received)
# Connection count should drop to 0
```

## See Also

- [CONNECTION_HEALTH_EXAMPLE.md](CONNECTION_HEALTH_EXAMPLE.md) - Connection health monitoring
- [test_bus_controller.py](test_bus_controller.py) - Example controller with auto-ping
- [test_bus_node.py](test_bus_node.py) - Example node with auto-pong stats

