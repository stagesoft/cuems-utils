#!/usr/bin/env python3
"""
Simple example demonstrating OscNodesHub usage.

This example shows how to:
1. Serialize a pyossia node structure
2. Send it over the bus
3. Receive and deserialize it on the other side
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pyossia
from cuemsutils.tools.Osc_nodes_hub import OscNodesHub, ActionType
import json


def create_sample_device():
    """Create a sample OSC device with some nodes."""
    print("Creating sample OSC device...")
    
    # Create OSC device with random ports to avoid conflicts
    import random
    base_port = random.randint(20000, 30000)
    device = pyossia.ossia.OSCDevice("SampleDevice", "127.0.0.1", base_port, base_port + 1)
    
    # Create audio section
    audio = device.add_node("/audio")
    
    volume = audio.add_node("/volume")
    volume_param = volume.create_parameter(pyossia.ossia.ValueType.Float)
    volume_param.value = 0.8
    
    mute = audio.add_node("/mute")
    mute_param = mute.create_parameter(pyossia.ossia.ValueType.Bool)
    mute_param.value = False
    
    # Create video section
    video = device.add_node("/video")
    
    opacity = video.add_node("/opacity")
    opacity_param = opacity.create_parameter(pyossia.ossia.ValueType.Float)
    opacity_param.value = 1.0
    
    return device


def demonstrate_serialization():
    """Demonstrate node serialization."""
    print("\n" + "=" * 60)
    print("DEMONSTRATION: Node Serialization")
    print("=" * 60)
    
    device = create_sample_device()
    root = device.root_node
    
    # Serialize the node tree
    print("\nSerializing node tree...")
    serialized = OscNodesHub.serialize_node(root)
    
    print("\nSerialized structure:")
    print(json.dumps(serialized, indent=2))
    
    print("\n✅ Serialization complete!")
    return serialized


def demonstrate_deserialization(serialized_data):
    """Demonstrate node deserialization."""
    print("\n" + "=" * 60)
    print("DEMONSTRATION: Node Deserialization")
    print("=" * 60)
    
    # Create a new device to hold the deserialized structure
    print("\nCreating new device to receive deserialized nodes...")
    import random
    base_port = random.randint(30000, 40000)
    new_device = pyossia.ossia.OSCDevice("ReceivedDevice", "127.0.0.1", base_port, base_port + 1)
    new_root = new_device.root_node
    
    print("Deserializing node tree...")
    OscNodesHub.deserialize_node(serialized_data, new_root)
    
    print("\n✅ Deserialization complete!")
    print("\nReconstructed node tree:")
    print_node_tree(new_root)


def print_node_tree(node, indent=0):
    """Recursively print a node tree."""
    prefix = "  " * indent
    name = node.name
    
    param = node.parameter
    if param:
        try:
            value = param.value
            print(f"{prefix}├─ {name} = {value}")
        except:
            print(f"{prefix}├─ {name} (parameter)")
    else:
        print(f"{prefix}├─ {name}")
    
    for child in node.children():
        print_node_tree(child, indent + 1)


async def demonstrate_transmission():
    """Demonstrate node transmission over the bus."""
    import asyncio
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION: Node Transmission (Simulated)")
    print("=" * 60)
    
    print("\nTo see actual transmission over TCP:")
    print("1. Run the controller in one terminal:")
    print("   python test_osc_hub_controller.py")
    print("   (Listens on tcp://127.0.0.1:5555)")
    print("\n2. Run the node in another terminal:")
    print("   python test_osc_hub_node.py")
    print("   (Connects to tcp://127.0.0.1:5555)")
    print("\n3. Watch as the node sends its structure to the controller!")
    print("\nNote: You can run multiple nodes to see multi-node tracking!")


def main():
    """Run all demonstrations."""
    print("=" * 60)
    print("🎵 OSC Nodes Hub - Example Demonstrations")
    print("=" * 60)
    
    # Demonstrate serialization
    serialized = demonstrate_serialization()
    
    # Demonstrate deserialization
    demonstrate_deserialization(serialized)
    
    # Show how to use transmission
    import asyncio
    asyncio.run(demonstrate_transmission())
    
    print("\n" + "=" * 60)
    print("✅ All demonstrations complete!")
    print("=" * 60)
    print("\nFor more information, see OSC_NODES_HUB_GUIDE.md")


if __name__ == "__main__":
    main()

