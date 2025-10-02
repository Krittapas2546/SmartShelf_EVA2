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
    """เรียก /ShelfName เพื่อดึงข้อมูล shelf_id และเก็บไว้ใน global variable"""
    try:
        print("🔄 Initializing shelf information...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8000/ShelfName")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Shelf initialized: {data.get('shelf_id')} ({data.get('shelf_name')})")
                return True
            else:
                print(f"⚠️ Failed to initialize shelf info: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Error initializing shelf info: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """เรียกใช้ฟังก์ชัน initialization เมื่อแอปพลิเคชันเริ่มต้น"""
    # รอสักครู่ให้เซิร์ฟเวอร์เริ่มต้นเสร็จก่อน
    await asyncio.sleep(2)
    await initialize_shelf_info()


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