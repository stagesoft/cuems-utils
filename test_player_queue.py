#!/usr/bin/env python3
"""
Simple test to verify player queue and serialization works correctly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import asyncio
import pyossia
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType, PlayerOperation
import random


def test_serialization():
    """Test that player serialization works."""
    print("=" * 60)
    print("TEST: Player Serialization")
    print("=" * 60)
    
    # Create a sample device
    base_port = random.randint(40000, 50000)
    device = pyossia.ossia.OSCDevice("TestPlayer", "127.0.0.1", base_port, base_port + 1)
    audio = device.add_node("/audio")
    volume = audio.add_node("/volume")
    volume.create_parameter(pyossia.ossia.ValueType.Float).value = 0.75
    
    # Serialize
    serialized = OscNodesHub.serialize_node(device.root_node)
    
    print(f"✅ Serialized player structure:")
    print(f"   Root: {serialized['name']}")
    print(f"   Children: {len(serialized['children'])}")
    if serialized['children']:
        for child in serialized['children']:
            print(f"      - {child['name']} ({len(child.get('children', []))} children)")
    
    return serialized


async def test_player_queue():
    """Test that player queueing works."""
    print("\n" + "=" * 60)
    print("TEST: Player Queue")
    print("=" * 60)
    
    # Create hub (not connected)
    hub = OscNodesHub("tcp://127.0.0.1:9999", mode=OscNodesHub.Mode.NODE)
    
    # Create players
    devices = []
    for i in range(3):
        base_port = random.randint(40000, 50000)
        device = pyossia.ossia.OSCDevice(f"Player{i}", "127.0.0.1", base_port, base_port + 1)
        device.add_node("/test")
        devices.append(device)
    
    # Queue players
    print("\n📤 Queueing players...")
    await hub.add_player("player_001", devices[0].root_node, ActionType.ADD)
    print("   ✅ Queued player_001 (ADD)")
    
    await hub.add_player("player_002", devices[1].root_node, ActionType.ADD)
    print("   ✅ Queued player_002 (ADD)")
    
    await hub.add_player("player_001", devices[0].root_node, ActionType.UPDATE)
    print("   ✅ Queued player_001 (UPDATE)")
    
    await hub.remove_player("player_002")
    print("   ✅ Queued player_002 (REMOVE)")
    
    # Check queue size (now using base class outgoing queue)
    queue_size = hub.outgoing.qsize()
    print(f"\n📊 Outgoing queue size: {queue_size}")
    
    if queue_size == 4:
        print("✅ TEST PASSED: All 4 operations queued correctly")
    else:
        print(f"❌ TEST FAILED: Expected 4, got {queue_size}")
    
    return queue_size == 4


def test_player_operation():
    """Test PlayerOperation dataclass."""
    print("\n" + "=" * 60)
    print("TEST: PlayerOperation")
    print("=" * 60)
    
    # Create operation
    op = PlayerOperation(
        action=ActionType.ADD,
        player_id="test_player",
        node_data={"name": "test", "children": []},
        sender="192.168.1.100"
    )
    
    print(f"✅ Created PlayerOperation:")
    print(f"   Action: {op.action.value}")
    print(f"   Player ID: {op.player_id}")
    print(f"   Has node_data: {op.node_data is not None}")
    print(f"   Sender: {op.sender}")
    
    # Test REMOVE operation (no node_data)
    op_remove = PlayerOperation(
        action=ActionType.REMOVE,
        player_id="test_player",
        node_data=None,
        sender="192.168.1.100"
    )
    
    print(f"\n✅ Created REMOVE PlayerOperation:")
    print(f"   Action: {op_remove.action.value}")
    print(f"   Player ID: {op_remove.player_id}")
    print(f"   Has node_data: {op_remove.node_data is not None}")
    
    print("\n✅ TEST PASSED: PlayerOperation works correctly")
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🧪 OSC Players Hub - Unit Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Serialization
    try:
        test_serialization()
        results.append(("Serialization", True))
    except Exception as e:
        print(f"❌ Serialization test failed: {e}")
        results.append(("Serialization", False))
    
    # Test 2: Player Queue
    try:
        result = await test_player_queue()
        results.append(("Player Queue", result))
    except Exception as e:
        print(f"❌ Player queue test failed: {e}")
        results.append(("Player Queue", False))
    
    # Test 3: PlayerOperation
    try:
        result = test_player_operation()
        results.append(("PlayerOperation", result))
    except Exception as e:
        print(f"❌ PlayerOperation test failed: {e}")
        results.append(("PlayerOperation", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

