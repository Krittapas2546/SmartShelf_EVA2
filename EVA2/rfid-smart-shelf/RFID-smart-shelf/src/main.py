from fastapi import FastAPI
import uvicorn
from fastapi.staticfiles import StaticFiles
import pathlib
import socket
import os
import signal
import subprocess
import json
import httpx
import asyncio
# --- Import Routers จากไฟล์ที่เราสร้าง ---
from api import jobs, websockets

# สร้างแอปพลิเคชัน FastAPI หลัก
app = FastAPI(
    title="Smart Shelf API (Refactored)",
    description="A professional, well-structured server for the Smart Shelf system.",
    version="3.0.0"
)

# ฟังก์ชันเรียกใช้ตอนเริ่มต้นระบบ
async def initialize_shelf_info():
    """เรียกใช้ฟังก์ชัน get_shelf_info_endpoint โดยตรงแทนการเรียก HTTP"""
    try:
        print("🔄 Initializing shelf information...")
        # Import ฟังก์ชันที่จำเป็น
        from api.jobs import get_shelf_info_endpoint
        
        # เรียกฟังก์ชันโดยตรงแทนการเรียก HTTP
        result = await get_shelf_info_endpoint()
        
        if result.get("success"):
            shelf_id = result.get("shelf_id")
            shelf_name = result.get("shelf_name")
            print(f"✅ Shelf initialized: {shelf_id} ({shelf_name})")
            return True
        else:
            print(f"⚠️ Failed to initialize shelf info: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error initializing shelf info: {e}")
        return False

async def initialize_shelf_layout():
    """ดึง layout configuration จาก Gateway เมื่อเริ่มต้นระบบ"""
    try:
        print("🔄 Initializing shelf layout from Gateway...")
        
        # Import ฟังก์ชันที่จำเป็น
        from api.jobs import fetch_layout_from_gateway, GLOBAL_SHELF_INFO
        from core.database import update_layout_from_gateway
        
        # ตรวจสอบว่ามี shelf_id แล้วหรือไม่
        shelf_id = GLOBAL_SHELF_INFO.get("shelf_id")
        if not shelf_id:
            print("⚠️ No shelf_id available, using default PC2")
            shelf_id = "PC2"
            
        # ดึง layout จาก Gateway
        layout_data = await fetch_layout_from_gateway(shelf_id)
        
        if layout_data and layout_data.get("status") == "success":
            gateway_layout = layout_data.get("layout", {})
            
            if gateway_layout:
                # อัปเดต local database configuration
                update_success = update_layout_from_gateway(gateway_layout)
                
                if update_success:
                    print(f"✅ Layout initialized from Gateway: {len(gateway_layout)} positions")
                    return True
                else:
                    print("⚠️ Failed to update local database with Gateway layout")
                    return False
            else:
                print("📝 Empty layout from Gateway, using default configuration")
                return False
        else:
            print("❌ Failed to fetch layout from Gateway")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing layout: {e}")
        return False

async def initialize_shelf_state():
    """กู้คืน shelf state จาก Gateway เมื่อเริ่มต้นระบบ"""
    try:
        print("🔄 Initializing shelf state from Gateway...")
        
        # Import ฟังก์ชันที่จำเป็น
        from api.jobs import restore_shelf_state_from_gateway, GLOBAL_SHELF_INFO
        from core.database import DB
        
        # ตรวจสอบว่ามี shelf_id แล้วหรือไม่
        if not GLOBAL_SHELF_INFO.get("shelf_id"):
            print("⚠️ No shelf_id available, skipping shelf state restore")
            return False
            
        # กู้คืนจาก Gateway
        restored_state = await restore_shelf_state_from_gateway()
        
        if restored_state and isinstance(restored_state, dict):
            print(f"✅ Shelf state restored from Gateway: {len(restored_state)} positions")
            
            # แปลง Gateway format เป็น local DB format
            # สมมติว่า restored_state = {"L1B1": {...}, "L1B2": {...}}
            restored_count = 0
            for position_key, position_data in restored_state.items():
                # Parse position (L1B1 -> level=1, block=1)
                import re
                match = re.match(r'L(\d+)B(\d+)', position_key)
                if match:
                    level = int(match.group(1))
                    block = int(match.group(2))
                    lots = position_data.get("lots", [])
                    
                    # อัปเดต local DB
                    for cell in DB["shelf_state"]:
                        if cell[0] == level and cell[1] == block:
                            cell[2] = lots
                            restored_count += 1
                            break
            
            print(f"📦 Updated {restored_count} positions in local database")
            return True
            
        else:
            print("📝 No shelf state data from Gateway, using current local state")
            return True
            
    except Exception as e:
        print(f"❌ Error initializing shelf state: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """เรียกใช้ฟังก์ชัน initialization เมื่อแอปพลิเคชันเริ่มต้น"""
    # รอสักครู่ให้เซิร์ฟเวอร์เริ่มต้นเสร็จก่อน (ลดเวลาลง)
    await asyncio.sleep(1)
    
    # Migration: เพิ่ม biz field ให้กับ lots ที่มีอยู่แล้ว
    from core.database import migrate_existing_lots_add_biz
    migrate_existing_lots_add_biz()
    
    # Initialize shelf info first
    shelf_init_success = await initialize_shelf_info()
    
    # Initialize layout configuration from Gateway
    layout_init_success = await initialize_shelf_layout()
    
    # Then initialize shelf state (requires shelf_id and layout)
    if shelf_init_success:
        await initialize_shelf_state()
    else:
        print("⚠️ Skipping shelf state initialization due to shelf info failure")
        
    # แสดงสถานะการ initialization
    print("=" * 50)
    print("🚀 System Initialization Summary:")
    print(f"   📋 Shelf Info: {'✅' if shelf_init_success else '❌'}")
    print(f"   🏗️  Layout: {'✅' if layout_init_success else '❌'}")
    print(f"   📦 State: Available after shelf info")
    print("=" * 50)


STATIC_PATH = pathlib.Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


app.include_router(jobs.router)
app.include_router(websockets.router)



# --- Main ---
if __name__ == "__main__":
    # --- Kill any existing process on port 8000 before starting ---
    def kill_port_process(port=8000):
        """Kill process using specified port (optimized for Linux)"""
        try:
            import platform
            system = platform.system().lower()
            
            if system == "linux" or system == "darwin":  # Linux/macOS
                print(f"� Checking for processes on port {port} (Linux/Unix)...")
                
                # Method 1: Try lsof (most reliable)
                try:
                    result = subprocess.run(f"lsof -t -i:{port}", shell=True, 
                                         capture_output=True, text=True, timeout=5)
                    pids = [p.strip() for p in result.stdout.strip().split() if p.strip().isdigit()]
                    
                    if pids:
                        for pid in pids:
                            try:
                                print(f"🔌 Found process {pid} on port {port}. Terminating...")
                                os.kill(int(pid), signal.SIGTERM)
                                print(f"🔪 Process {pid} terminated successfully.")
                            except (ValueError, ProcessLookupError) as e:
                                print(f"⚠️ Process {pid} already terminated: {e}")
                    else:
                        print(f"✅ No processes found on port {port}")
                        
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # Method 2: Fallback to netstat + kill
                    print("� Using netstat fallback method...")
                    result = subprocess.run(f"netstat -tlnp | grep :{port}", shell=True,
                                         capture_output=True, text=True)
                    if result.stdout:
                        print(f"� Found service on port {port}, attempting graceful shutdown...")
                        subprocess.run(f"sudo fuser -k {port}/tcp", shell=True)
                        print(f"🔪 Port {port} cleared.")
                    else:
                        print(f"✅ No processes found on port {port}")
                        
            elif system == "windows":
                # Windows fallback (simplified)
                print(f"🪟 Checking for processes on port {port} (Windows)...")
                result = subprocess.run(f'netstat -ano | findstr ":{port}"', 
                                      shell=True, capture_output=True, text=True)
                
                pids = set()
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and f":{port}" in line:
                        parts = line.split()
                        if len(parts) >= 5 and parts[-1].isdigit():
                            pids.add(parts[-1])
                
                if pids:
                    for pid in pids:
                        try:
                            print(f"🔌 Terminating Windows process {pid}...")
                            subprocess.run(f"taskkill /F /PID {pid}", shell=True, check=True)
                            print(f"🔪 Process {pid} terminated.")
                        except subprocess.CalledProcessError as e:
                            print(f"⚠️ Could not terminate process {pid}: {e}")
                else:
                    print(f"✅ No processes found on port {port}")
                    
        except Exception as e:
            print(f"❌ Error while checking port {port}: {e}")
    
    # Kill any existing process on port 8000
    kill_port_process(8000)

    def get_local_ip():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 8000))
                return s.getsockname()[0]
        except:
            return "localhost"
    
    local_ip = get_local_ip()
    
    print("🚀 Starting RFID Smart Shelf Server (v2.0 Refactored)...")
    print(f"📱 Smart Shelf UI: http://localhost:8000")
    print(f"python /home/pi/Documents/GitHub/RFID-smart-shelf/RFID-smart-shelf/src/main.py")
    print(f"🎮 Event Simulator: http://localhost:8000/simulator")
    print(f"📄 API Docs:       http://localhost:8000/docs")
    print(f"🌐 Network API:    http://{local_ip}:8000") 
    print(f"📱 Pi Access:      http://{local_ip}:8000")  
    uvicorn.run(app, host="0.0.0.0", port=8000)