#!/usr/bin/env python3
"""
Button Reader Test Script
========================

Test the integrated button reader functionality with the main server.
"""

import sys
import os
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from core.pushbutton_reader import PushButtonReader
    print("✅ Button reader imported successfully")
except ImportError as e:
    print(f"❌ Failed to import button reader: {e}")
    sys.exit(1)

def test_button_callback(button_index: int, position: str):
    """Test callback function"""
    print(f"🔘 Test callback: Button {button_index} pressed at {position}")

def test_button_reader():
    """Test button reader functionality"""
    print("🧪 Testing Button Reader...")
    print("=" * 50)
    
    # Create reader
    reader = PushButtonReader(callback=test_button_callback, debug=True)
    
    # Show status
    status = reader.get_status()
    print(f"📊 Initial Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    print()
    
    # Test position mapping update
    new_mapping = {0: "L1B1", 1: "L1B2", 2: "L2B1"}
    reader.update_position_mapping(new_mapping)
    print(f"📍 Updated mapping: {reader.position_mapping}")
    print()
    
    # Start monitoring
    print("▶️ Starting monitoring...")
    reader.start_monitoring()
    
    # Test simulation
    if not reader.hardware_available:
        print("🧪 Hardware not available - testing simulation mode:")
        time.sleep(1)
        for i in range(3):
            print(f"  Simulating button {i}...")
            reader.simulate_button_press(i)
            time.sleep(0.5)
    else:
        print("🔧 Hardware available - press buttons to test!")
        print("Press Ctrl+C to stop...")
        try:
            for i in range(10):
                print(f"Waiting for button presses... ({i+1}/10)")
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    # Stop monitoring
    print("\n🛑 Stopping monitoring...")
    reader.stop_monitoring()
    
    # Final status
    final_status = reader.get_status()
    print(f"📊 Final Status: Running = {final_status.get('running')}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_button_reader()