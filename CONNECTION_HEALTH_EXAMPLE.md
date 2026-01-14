# Connection Health Monitoring

The `Nng_bus_hub` class now includes connection health monitoring based on message activity. This is particularly useful for **NODES** to check if they're still connected to the controller.

## Why This Matters

In NNG bus topology:
- **Controllers** track incoming node connections via `active_connections`
- **Nodes** DON'T track the outgoing controller connection the same way
- Solution: Monitor message activity to detect if connection is alive

## API

### `get_connection_health_info(activity_timeout=30.0)`

Returns detailed health information:

```python
health_info = hub.get_connection_health_info()
# Returns:
{
    'is_healthy': bool,              # True if activity within timeout
    'last_received': datetime,       # Last message received time
    'last_sent': datetime,           # Last message sent time  
    'seconds_since_activity': float, # Seconds since last activity
    'messages_received': int,        # Total messages received
    'messages_sent': int            # Total messages sent
}
```

### `is_connection_healthy(activity_timeout=30.0)`

Quick check for connection health:

```python
if hub.is_connection_healthy():
    print("✅ Connection is healthy")
else:
    print("⚠️ Connection may be down")
```

## Usage Examples

### Basic Health Check (Node)

```python
from cuemsutils.tools.CommunicatorServices import Nng_bus_hub

# Create node
node = Nng_bus_hub("tcp://127.0.0.1:5555", mode=Nng_bus_hub.Mode.NODE)

# Later, check health
health = node.get_connection_health_info()

if health['is_healthy']:
    print(f"✅ Healthy - last activity {health['seconds_since_activity']:.1f}s ago")
else:
    print(f"⚠️ Unhealthy - {health['seconds_since_activity']:.1f}s since last activity")
```

### Monitoring Loop

```python
import asyncio
from datetime import datetime

async def monitor_connection_health(hub):
    """Monitor connection health every 10 seconds."""
    while True:
        await asyncio.sleep(10)
        
        health = hub.get_connection_health_info(activity_timeout=30.0)
        
        if health['is_healthy']:
            print(f"✅ Connection healthy")
            print(f"   Last activity: {health['seconds_since_activity']:.1f}s ago")
        else:
            print(f"⚠️ Connection unhealthy!")
            if health['seconds_since_activity']:
                print(f"   No activity for: {health['seconds_since_activity']:.1f}s")
            else:
                print(f"   No activity detected yet")

# Run alongside your node
asyncio.create_task(monitor_connection_health(node))
```

### Automatic Reconnection

```python
async def connection_watchdog(hub, reconnect_callback):
    """Watch connection and trigger reconnect if unhealthy."""
    consecutive_unhealthy = 0
    
    while True:
        await asyncio.sleep(5)
        
        if not hub.is_connection_healthy(activity_timeout=20.0):
            consecutive_unhealthy += 1
            
            if consecutive_unhealthy >= 3:
                # Unhealthy for 3 consecutive checks (15 seconds)
                print("⚠️ Connection appears dead, reconnecting...")
                await reconnect_callback()
                consecutive_unhealthy = 0
        else:
            consecutive_unhealthy = 0
```

### Dashboard Display

```python
def display_connection_status(hub):
    """Display nice connection status."""
    health = hub.get_connection_health_info()
    
    print("="*60)
    print("CONNECTION STATUS")
    print("="*60)
    
    # Health indicator
    status = "✅ HEALTHY" if health['is_healthy'] else "⚠️ UNHEALTHY"
    print(f"Health: {status}")
    
    # Activity timing
    if health['seconds_since_activity'] is not None:
        print(f"Last Activity: {health['seconds_since_activity']:.1f}s ago")
    else:
        print(f"Last Activity: No activity yet")
    
    # Message stats
    print(f"\nMessage Statistics:")
    print(f"  Sent:     {health['messages_sent']}")
    print(f"  Received: {health['messages_received']}")
    
    # Timestamps
    if health['last_sent']:
        print(f"\nLast Sent:     {health['last_sent'].strftime('%H:%M:%S')}")
    if health['last_received']:
        print(f"Last Received: {health['last_received'].strftime('%H:%M:%S')}")
    
    print("="*60)
```

### Custom Timeout

```python
# Strict timeout (10 seconds)
if hub.is_connection_healthy(activity_timeout=10.0):
    print("Active connection")

# Relaxed timeout (60 seconds)  
if hub.is_connection_healthy(activity_timeout=60.0):
    print("Connection still alive")
```

## How It Works

The health monitoring tracks:

1. **Message Receipt** - Updates `_last_message_received` when messages arrive
2. **Message Send** - Updates `_last_message_sent` when messages are sent
3. **Health Calculation** - Compares time since last activity to timeout

**Important**: Health requires **actual message traffic**. If no messages are being sent/received naturally, consider implementing a heartbeat mechanism.

## Heartbeat Pattern

For reliable health checking, implement heartbeats:

```python
# Controller sends periodic heartbeats
async def send_heartbeats(hub):
    while True:
        await asyncio.sleep(5)
        await hub.send_message({"type": "heartbeat"})

# Node monitors for heartbeats
async def check_heartbeat_health(hub):
    while True:
        await asyncio.sleep(10)
        
        health = hub.get_connection_health_info(activity_timeout=15.0)
        
        if not health['is_healthy']:
            print("⚠️ No heartbeat received - connection may be down")
```

## Controller vs Node

### Controller
- Can use `get_active_connections()` to see connected nodes
- Can use health monitoring to track message activity
- Both methods work!

### Node  
- **Should use health monitoring** to check controller connection
- `get_active_connections()` returns empty (expected behavior)
- Health monitoring is the **primary way** to verify connection

## Test Script

See `test_bus_node.py` for a complete example showing:
- Health monitoring in action
- Status display every 15 seconds
- Warning when connection appears lost
- Message statistics tracking

## Troubleshooting

### "Connection Health: UNHEALTHY or NOT YET ESTABLISHED"

**Causes:**
1. No messages sent/received yet (wait for first message)
2. No activity for > timeout seconds
3. Connection actually lost

**Solutions:**
- Wait for messages to flow
- Implement heartbeat mechanism
- Check if controller is running
- Verify network connectivity

### "No activity detected yet"

This is normal on startup. Health will show as healthy once the first message is sent or received.

### False Positives

If your application naturally has quiet periods, increase the `activity_timeout`:

```python
# For apps with infrequent messages
health = hub.get_connection_health_info(activity_timeout=120.0)
```

## Best Practices

1. **Choose appropriate timeout** - Based on your message frequency
2. **Implement heartbeats** - For reliable connection monitoring
3. **Don't check too frequently** - Check health every 10-15 seconds
4. **Consider message patterns** - Adapt timeout to your traffic patterns
5. **Log health changes** - Track when connections go unhealthy

## Example Output

From `test_bus_node.py`:

```
============================================================
📊 NODE STATUS
============================================================
Status: ✅ Running
Uptime: 45.3s
Mode: NODE

Connection Health: ✅ HEALTHY
Last Activity: 2.1s ago

Message Statistics:
  Sent: 9
  Received: 15
============================================================
```

When disconnected:

```
============================================================
📊 NODE STATUS
============================================================
Status: ✅ Running
Uptime: 120.5s
Mode: NODE

Connection Health: ⚠️ UNHEALTHY or NOT YET ESTABLISHED
Last Activity: 45.2s ago

Message Statistics:
  Sent: 24
  Received: 30

⚠️  WARNING: No activity for 45s
   Connection to controller may be lost!
============================================================
```

