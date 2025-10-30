#!/usr/bin/env python3
"""
Test script สำหรับ LED Controller ใหม่ที่ใช้ state-based buffer
"""

import time
import sys
import os

# เพิ่ม path สำหรับ import module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.led_controller import (
    set_target_blue, set_target_green, add_error_red, clear_all_leds, 
    hard_clear, set_pixels, turn_off_some, show_state, 
    debug_mapping, validate_expected_mapping, NUM_PIXELS, state
)

def test_basic_functions():
    """ทดสอบฟังก์ชันพื้นฐาน"""
    print("\n🧪 Testing Basic LED Functions...")
    
    # ทดสอบ hard_clear
    print("\n1. Testing hard_clear...")
    clear_all_leds()
    time.sleep(1)
    
    # ทดสอบ set_target_blue
    print("\n2. Testing set_target_blue (L1B1)...")
    result = set_target_blue(1, 1)
    print(f"   Result: {result}")
    time.sleep(2)
    
    # ทดสอบ set_target_green
    print("\n3. Testing set_target_green (L1B1 -> Green)...")
    result = set_target_green(1, 1)
    print(f"   Result: {result}")
    time.sleep(2)
    
    # ทดสอบ add_error_red
    print("\n4. Testing add_error_red (L1B2 -> Red, keeping L1B1 green)...")
    result = add_error_red(1, 2)
    print(f"   Result: {result}")
    time.sleep(2)
    
    # แสดงสถานะ buffer
    print(f"\n5. Current LED state: {[i for i, rgb in enumerate(state) if rgb != (0, 0, 0)]}")
    
    # ทดสอบ turn_off_some
    print("\n6. Testing turn_off_some (turning off L1B1)...")
    turn_off_some([(1, 1)])
    time.sleep(1)
    
    print(f"   State after turn_off_some: {[i for i, rgb in enumerate(state) if rgb != (0, 0, 0)]}")
    
    # ล้างทั้งหมด
    print("\n7. Final clear...")
    clear_all_leds()
    time.sleep(1)

def test_job_scenario():
    """ทดสอบ scenario การทำงานจริง"""
    print("\n🎯 Testing Job Scenario...")
    
    # Scenario: Job L2B3 (งานหยิบ)
    target_level, target_block = 2, 3
    
    print(f"\n--- Job Started: Pick from L{target_level}B{target_block} ---")
    
    # 1. เริ่มงาน: แสดงช่องเป้าหมายเป็นสีน้ำเงิน
    print("1. Starting job - showing target in blue...")
    set_target_blue(target_level, target_block)
    time.sleep(2)
    
    # 2. Simulate กดปุ่มผิดตำแหน่ง (L1B1)
    wrong_level, wrong_block = 1, 1
    print(f"2. Wrong button pressed at L{wrong_level}B{wrong_block} - adding red LED...")
    add_error_red(wrong_level, wrong_block)
    time.sleep(3)
    
    # 3. Simulate กดปุ่มผิดอีกครั้ง (L1B2)
    wrong_level2, wrong_block2 = 1, 2
    print(f"3. Another wrong button at L{wrong_level2}B{wrong_block2} - adding more red...")
    add_error_red(wrong_level2, wrong_block2)
    time.sleep(3)
    
    # 4. สุดท้ายกดปุ่มถูก: เปลี่ยนเป้าหมายเป็นสีเขียว
    print(f"4. Correct button pressed - target becomes green...")
    set_target_green(target_level, target_block)
    time.sleep(3)
    
    # 5. งานเสร็จ: ล้างทั้งหมด
    print("5. Job completed - clearing all LEDs...")
    clear_all_leds()
    time.sleep(1)
    
    print("--- Job Scenario Complete ---")

def test_multiple_positions():
    """ทดสอบการทำงานกับหลายตำแหน่ง"""
    print("\n🔢 Testing Multiple Positions...")
    
    # ใช้ set_pixels ตั้งหลายสีพร้อมกัน
    print("1. Setting multiple LEDs with different colors...")
    
    # ล้างก่อน
    clear_all_leds()
    
    # ตั้งหลายสี
    positions = [
        (1, 1, (255, 0, 0)),    # L1B1 = Red
        (1, 2, (0, 255, 0)),    # L1B2 = Green  
        (1, 3, (0, 0, 255)),    # L1B3 = Blue
        (2, 1, (255, 255, 0)),  # L2B1 = Yellow
        (2, 2, (255, 0, 255)),  # L2B2 = Purple
    ]
    
    set_pixels(positions)
    time.sleep(3)
    
    # ดับบางดวง
    print("2. Turning off some LEDs...")
    turn_off_some([(1, 1), (2, 2)])  # ดับ red และ purple
    time.sleep(2)
    
    # เพิ่มสีใหม่
    print("3. Adding new LEDs without clearing existing...")
    set_pixels([(3, 1, (0, 255, 255))])  # L3B1 = Cyan
    time.sleep(2)
    
    # ล้างทั้งหมด
    print("4. Final clear...")
    clear_all_leds()

def test_debug_functions():
    """ทดสอบฟังก์ชัน debug"""
    print("\n🔍 Testing Debug Functions...")
    
    print("\n--- LED Mapping Debug ---")
    debug_mapping()
    
    print("\n--- Validation Test ---")
    result = validate_expected_mapping()
    print(f"Validation result: {'✅ PASS' if result else '❌ FAIL'}")

def main():
    """ฟังก์ชันหลัก"""
    print("🧪 LED Controller Test Suite")
    print(f"📊 Total pixels: {NUM_PIXELS}")
    print(f"🎮 Test mode: {'HARDWARE' if 'pi5neo' in str(type(eval('neo', globals(), {}))) else 'MOCK'}")
    
    try:
        # รันการทดสอบ
        test_debug_functions()
        time.sleep(1)
        
        test_basic_functions()
        time.sleep(1)
        
        test_multiple_positions()
        time.sleep(1)
        
        test_job_scenario()
        
        print("\n✅ All tests completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # ล้าง LED ก่อนจบ
        print("\n🧹 Cleaning up...")
        clear_all_leds()
        print("🔚 Test suite finished")

if __name__ == "__main__":
    main()