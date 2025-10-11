import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.led_controller import idx, get_num_pixels
from core.database import get_shelf_config, validate_position

print("=== LED Controller Debug ===")
print(f"Total pixels: {get_num_pixels()}")
print(f"Shelf config: {get_shelf_config()}")

# Test positions
test_positions = [(1, 6), (1, 7), (1, 8)]
for level, block in test_positions:
    position = f"L{level}B{block}"
    
    print(f"\n--- Testing {position} ---")
    print(f"validate_position({level}, {block}): {validate_position(level, block)}")
    
    led_idx = idx(level, block)
    print(f"idx({level}, {block}): {led_idx}")
    
    if led_idx != -1:
        print(f"✅ {position} -> LED index {led_idx}")
    else:
        print(f"❌ {position} -> Invalid")