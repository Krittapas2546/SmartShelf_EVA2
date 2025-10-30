#!/usr/bin/env python3
"""
API Test สำหรับทดสอบ LED Controller ใหม่ผ่าน HTTP API
ทดสอบ endpoints ที่ปรับปรุงแล้ว
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_led_clear():
    """ทดสอบ LED clear"""
    print("\n🧹 Testing LED Clear...")
    
    response = requests.post(f"{BASE_URL}/api/led/clear")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Clear success: {data}")
    else:
        print(f"❌ Clear failed: {response.text}")
    
    return response.status_code == 200

def test_led_control_single():
    """ทดสอบการควบคุม LED เดี่ยวด้วยชื่อสี"""
    print("\n🔴 Testing Single LED Control...")
    
    test_cases = [
        {"level": "1", "block": "1", "color": "blue"},
        {"level": "1", "block": "2", "color": "red"}, 
        {"level": "2", "block": "1", "color": "green"},
        {"level": "2", "block": "2", "color": "yellow"},
    ]
    
    for case in test_cases:
        print(f"   Setting L{case['level']}B{case['block']} = {case['color']}")
        
        response = requests.post(
            f"{BASE_URL}/api/led/control",
            json=case,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {data.get('position')} = {data.get('hex')}")
        else:
            print(f"   ❌ Failed: {response.text}")
        
        time.sleep(1)
    
    time.sleep(2)
    return True

def test_led_batch():
    """ทดสอบการควบคุม LED แบบ batch"""
    print("\n📦 Testing Batch LED Control...")
    
    # ล้างก่อน
    test_led_clear()
    time.sleep(0.5)
    
    batch_data = {
        "positions": [
            {"position": "L1B1", "r": 255, "g": 0, "b": 0},    # Red
            {"position": "L1B2", "r": 0, "g": 255, "b": 0},    # Green
            {"position": "L1B3", "r": 0, "g": 0, "b": 255},    # Blue
            {"position": "L2B1", "r": 255, "g": 255, "b": 0},  # Yellow
            {"position": "L2B2", "r": 255, "g": 0, "b": 255},  # Purple
        ],
        "clear_first": False  # ไม่ล้างก่อน
    }
    
    response = requests.post(
        f"{BASE_URL}/api/led",
        json=batch_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Batch success: {data.get('count')} LEDs set")
        for color_info in data.get('colors', []):
            print(f"   {color_info['position']} = {color_info['hex']}")
    else:
        print(f"❌ Batch failed: {response.text}")
    
    time.sleep(3)
    return response.status_code == 200

def test_job_scenario_api():
    """ทดสอบ scenario การทำงานผ่าน API"""
    print("\n🎯 Testing Job Scenario via API...")
    
    # 1. เคลียร์ LED
    print("1. Clearing LEDs...")
    test_led_clear()
    time.sleep(0.5)
    
    # 2. แสดงช่องเป้าหมายเป็นสีน้ำเงิน (L2B3)
    print("2. Setting target position (L2B3) to blue...")
    response = requests.post(
        f"{BASE_URL}/api/led/control",
        json={"level": "2", "block": "3", "color": "blue"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        print("   ✅ Target set to blue")
    time.sleep(2)
    
    # 3. เพิ่มสีแดงเมื่อกดปุ่มผิด (L1B1) - ไม่ล้างสีเดิม
    print("3. Adding red for wrong button (L1B1)...")
    response = requests.post(
        f"{BASE_URL}/api/led/control",
        json={"level": "1", "block": "1", "color": "red"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        print("   ✅ Error red added")
    time.sleep(2)
    
    # 4. เพิ่มสีแดงอีกครั้งเมื่อกดผิดอีก (L1B2)
    print("4. Adding another red for wrong button (L1B2)...")
    response = requests.post(
        f"{BASE_URL}/api/led/control",
        json={"level": "1", "block": "2", "color": "red"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        print("   ✅ Another error red added")
    time.sleep(2)
    
    # 5. เปลี่ยนเป้าหมายเป็นสีเขียวเมื่อกดถูก
    print("5. Changing target to green (success)...")
    response = requests.post(
        f"{BASE_URL}/api/led/control",
        json={"level": "2", "block": "3", "color": "green"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        print("   ✅ Target changed to green")
    time.sleep(3)
    
    # 6. ล้างทั้งหมดเมื่องานเสร็จ
    print("6. Job completed - clearing all...")
    test_led_clear()
    
    print("✅ Job scenario completed")

def test_debug_endpoints():
    """ทดสอบ debug endpoints"""
    print("\n🔍 Testing Debug Endpoints...")
    
    # ทดสอบ debug mapping
    debug_data = {
        "test_type": "mapping",
        "show_green": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/led/debug",
        json=debug_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Debug mapping status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Debug success: {data.get('message')}")
        for result in data.get('test_results', []):
            print(f"   {result['position']}: {result['color']} RGB{result['rgb']}")
    else:
        print(f"❌ Debug failed: {response.text}")

def test_error_cases():
    """ทดสอบ error cases"""
    print("\n⚠️ Testing Error Cases...")
    
    # ทดสอบตำแหน่งไม่ถูกต้อง
    print("1. Testing invalid position...")
    response = requests.post(
        f"{BASE_URL}/api/led/control",
        json={"level": "99", "block": "99", "color": "red"},
        headers={"Content-Type": "application/json"}
    )
    print(f"   Invalid position status: {response.status_code} (should be 400 or 500)")
    
    # ทดสอบสีไม่ถูกต้อง  
    print("2. Testing invalid color...")
    response = requests.post(
        f"{BASE_URL}/api/led/control",
        json={"level": "1", "block": "1", "color": "invalid_color"},
        headers={"Content-Type": "application/json"}
    )
    print(f"   Invalid color status: {response.status_code} (should work with default)")

def main():
    """ฟังก์ชันหลัก"""
    print("🧪 LED Controller API Test Suite")
    print(f"🌐 Base URL: {BASE_URL}")
    
    try:
        # รันการทดสอบ
        print("\n" + "="*50)
        
        # ทดสอบพื้นฐาน
        test_led_clear()
        time.sleep(1)
        
        test_led_control_single()
        time.sleep(1)
        
        test_led_batch()
        time.sleep(1)
        
        # ทดสอบ scenario
        test_job_scenario_api()
        time.sleep(1)
        
        # ทดสอบ debug
        test_debug_endpoints()
        time.sleep(1)
        
        # ทดสอบ error cases
        test_error_cases()
        
        print("\n✅ All API tests completed!")
        
        # ล้าง LED สุดท้าย
        test_led_clear()
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to {BASE_URL}")
        print("   Make sure the server is running!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔚 API test suite finished")

if __name__ == "__main__":
    main()