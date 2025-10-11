from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse , JSONResponse
from fastapi.templating import Jinja2Templates

import json
import pathlib
import httpx
import re
from datetime import datetime

# --- สำหรับควบคุม LED ---
from core.led_controller import set_led

# --- Import จากไฟล์ที่เราสร้างขึ้น ---
from core.models import JobRequest, ErrorRequest, LEDPositionRequest, LEDPositionsRequest, LEDClearAndBatch, LMSCheckShelfRequest, LMSCheckShelfResponse, ShelfComplete, ShelfState, BlockState, LotData, LayoutRequest, LayoutResponse, SlotData
from core.database import (
    DB, get_job_by_id, get_lots_in_position, add_lot_to_position, remove_lot_from_position, update_lot_quantity, validate_position, get_shelf_info, SHELF_CONFIG, update_lot_biz, get_cell_capacity, update_layout_from_gateway, get_layout_info, is_layout_loaded_from_gateway, log_current_layout, get_layout_status
)
from core.lms_config import LMS_BASE_URL, LMS_ENDPOINT, LMS_API_KEY, LMS_TIMEOUT
from api.websockets import manager # <-- impor        },

# Gateway Configuration  
GATEWAY_BASE_URL = "http://43.72.20.238:8000"  # Gateway server URL

# Global shelf information (filled during startup)
GLOBAL_SHELF_INFO = {
    "shelf_id": None,
    "shelf_name": None,
    "local_ip": None
}

def get_actual_local_ip():
    """ดึง local IP address ที่แท้จริง (ไม่ใช่ 127.0.0.1)"""
    import socket
    try:
        # สร้าง socket เชื่อมต่อไปยัง external server เพื่อหา local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            return local_ip
    except Exception:
        # Fallback: ใช้ hostname
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip.startswith("127."):
                return "192.168.1.100" 
            return local_ip
        except:
            return "192.168.1.100"  #

# === Gateway Layout Functions ===
async def fetch_layout_from_gateway(shelf_id: str = None):
    """
    ดึงข้อมูล layout (ความจุและการกำหนดค่าช่องวาง) จาก Gateway
    """
    try:
        if not shelf_id:
            shelf_id = GLOBAL_SHELF_INFO.get("shelf_id", "PC2")
        
        gateway_payload = {
            "shelf_id": shelf_id,
            "update_flg": "0",  # อ่านข้อมูล
            "slots": {}
        }
        
        headers = {
            "Accept": "application/json", 
            "Content-Type": "application/json"
        }
        
        print(f"🔄 Fetching layout from Gateway: {GATEWAY_BASE_URL}/IoTManagement/shelf/layout")
        print(f"📦 Payload: {gateway_payload}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GATEWAY_BASE_URL}/IoTManagement/shelf/layout",
                json=gateway_payload,
                headers=headers
            )
            
            print(f"📡 Gateway Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ Layout fetched successfully")
                print(f"📦 Layout data: {response_data}")
                
                return response_data
            else:
                print(f"⚠️ Gateway layout fetch failed: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        print(f"⚠️ Layout fetch error: {e}")
        return None

async def sync_layout_to_gateway(layout_data: dict, shelf_id: str = None):
    """
    ส่งข้อมูล layout ไปบันทึกที่ Gateway (ไว้สำหรับอนาคต)
    """
    try:
        if not shelf_id:
            shelf_id = GLOBAL_SHELF_INFO.get("shelf_id", "PC2")
        
        gateway_payload = {
            "shelf_id": shelf_id,
            "update_flg": "1",  # เขียนข้อมูล
            "slots": layout_data
        }
        
        headers = {
            "Accept": "application/json", 
            "Content-Type": "application/json"
        }
        
        print(f"🔄 Syncing layout to Gateway: {GATEWAY_BASE_URL}/IoTManagement/shelf/layout")
        print(f"📦 Payload: {gateway_payload}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GATEWAY_BASE_URL}/IoTManagement/shelf/layout",
                json=gateway_payload,
                headers=headers
            )
            
            print(f"📡 Gateway Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Layout synced successfully")
                return True
            else:
                print(f"⚠️ Gateway layout sync failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"⚠️ Layout sync error: {e}")
        return False

# === Gateway Logging Functions ===
async def log_to_gateway(event_type: str, event_data: dict, shelf_id: str = None):
    """
    Gateway logging disabled - Gateway API requires full ShelfComplete format
    Only ShelfComplete data is sent via send_shelf_complete_to_gateway()
    """
    print(f"📝 Local log: {event_type} - {event_data}")
    return True  # Always return success to avoid breaking existing code

async def get_logs_from_gateway(limit: int = 20, event_type: str = None):
    """ดึง logs จาก Gateway (ใช้ auto-detected shelf_id)"""
    try:
        params = {"limit": limit}
        if event_type:
            params["event_type"] = event_type
            
        # ✅ ใช้ endpoint ใหม่ที่ Gateway auto-detect shelf จาก IP
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GATEWAY_BASE_URL}/IoTManagement/shelf/requestID",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Gateway returned {response.status_code}: {response.text}"}
                
    except Exception as e:
        return {"error": str(e)}

async def send_shelf_complete_to_gateway(job: dict):
    """
    ส่งข้อมูล ShelfComplete ไปยัง Gateway API
    ใช้ข้อมูลจาก job (ที่มี biz และ shelf_id ครบถ้วนแล้ว)
    """
    try:
        # ตรวจสอบข้อมูลที่จำเป็น
        if not job.get("biz"):
            print(f"⚠️ Warning: Missing biz in job {job.get('jobId', 'unknown')}")
            return False
            
        # สร้างข้อมูล ShelfComplete ตาม Gateway API format
        shelf_complete_data = {
            "job_id": job.get("jobId"),  # ใช้ jobId ของ local system
            "biz": job["biz"],  # บังคับต้องมี
            "shelf_id": job.get("shelf_id", "UNKNOWN"),
            "lot_no": job["lot_no"],
            "level": str(job["level"]),
            "block": str(job["block"]),
            "place_flg": str(job["place_flg"]),
            "trn_status": str(job.get("trn_status", "1")),  # ใช้ค่าเดิมจาก job
            "tray_count": str(job.get("tray_count", 1)),
            "status": "success"  # สำคัญ! Gateway ต้องการฟิลด์นี้เพื่อ mark เป็น completed
        }
        
        headers = {
            "Accept": "application/json", 
            "Content-Type": "application/json"
        }
        
        print(f"🔍 Sending ShelfComplete to Gateway: {GATEWAY_BASE_URL}/shelf/complete")
        print(f"📦 Payload: {shelf_complete_data}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GATEWAY_BASE_URL}/shelf/complete",
                json=shelf_complete_data,
                headers=headers
            )
            
            print(f"📡 Gateway Response Status: {response.status_code}")
            print(f"📄 Gateway Response Body: {response.text}")
            
            if response.status_code == 200:
                print(f"✅ ShelfComplete sent successfully")
                return True
            else:
                print(f"⚠️ Gateway ShelfComplete failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"⚠️ ShelfComplete Gateway error: {e}")
        return False

router = APIRouter() # <-- สร้าง router สำหรับไฟล์นี้
templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent.parent / "templates"))



# รองรับสั่งทีละดวง (เดิม)
@router.post("/api/led", tags=["System"])
async def control_led(request: Request):
    """รับ level, block แล้วควบคุม LED (Pi5Neo)"""
    try:
        data = await request.json()
        level = int(data.get('level', 0))
        block = int(data.get('block', 0))
        r = int(data.get('r', 0))
        g = int(data.get('g', 255))
        b = int(data.get('b', 0))
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON", "detail": str(e)})

    # Dynamic validation using current shelf config
    if not validate_position(level, block):
        return JSONResponse(status_code=400, content={
            "error": "Invalid position", 
            "message": f"Level {level}, Block {block} does not exist in current shelf configuration"
        })

    try:
        result = set_led(level, block, r, g, b)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "LED control failed", "detail": str(e)})

# รองรับสั่งหลายดวงพร้อมกัน
@router.post("/api/led/batch", tags=["System"])
async def control_led_batch(request: Request):
    """รับ array ของ led objects แล้วควบคุม LED หลายดวงพร้อมกัน"""
    try:
        data = await request.json()
        leds = data.get('leds', [])
        if not isinstance(leds, list):
            return JSONResponse(status_code=400, content={"error": "Invalid format: 'leds' must be a list"})
        
        # Validate all LED positions before execution
        invalid_positions = []
        for i, led in enumerate(leds):
            level = int(led.get('level', 0))
            block = int(led.get('block', 0))
            if not validate_position(level, block):
                invalid_positions.append(f"Index {i}: L{level}B{block}")
        
        if invalid_positions:
            return JSONResponse(status_code=400, content={
                "error": "Invalid LED positions found",
                "invalid_positions": invalid_positions
            })
        
        # ตัวอย่าง: [{level, block, r, g, b}, ...]
        from core.led_controller import set_led_batch
        result = set_led_batch(leds)
        return result
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON or batch", "detail": str(e)})

# รองรับสั่งไฟด้วยรูปแบบ position string เช่น "L1B1"
@router.post("/api/led/position", tags=["LED Control"])
async def control_led_by_position(request: LEDPositionRequest):
    """ควบคุม LED โดยส่ง position string เช่น L1B1, L2B3"""
    try:
        position = request.position.upper().strip()
        r = request.r
        g = request.g
        b = request.b
        
        # Parse position string (L1B1, L2B3, etc.)
        import re
        match = re.match(r'^L(\d+)B(\d+)$', position)
        if not match:
            return JSONResponse(status_code=400, content={
                "error": "Invalid position format", 
                "message": "Position must be in format L{level}B{block} (e.g., L1B1, L2B3)"
            })
        
        level = int(match.group(1))
        block = int(match.group(2))
        
        # Validate position exists in shelf config
        if not validate_position(level, block):
            return JSONResponse(status_code=400, content={
                "error": "Invalid position", 
                "message": f"Position {position} does not exist in shelf configuration"
            })
        
        # Control LED
        print(f"🔍 LED Control Debug: {position} -> L{level}B{block}")
        result = set_led(level, block, r, g, b)
        
        # ตรวจสอบผลการควบคุม LED
        if not result.get("ok", False):
            return JSONResponse(status_code=500, content={
                "error": "LED control failed",
                "message": result.get("error", "Unknown LED error"),
                "position": position
            })
        
        # LED control logged locally only
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        print(f"💡 LED Control: L{level}B{block} = {hex_color} ✅")
        
        result.update({
            "position": position,
            "level": level,
            "block": block,
            "color": {"r": r, "g": g, "b": b},
            "hex_color": hex_color
        })
        
        return result
        
    except Exception as e:
        return JSONResponse(status_code=400, content={
            "error": "Invalid request", 
            "detail": str(e)
        })

# รองรับสั่งไฟหลายตำแหน่งด้วย position strings
@router.post("/api/led/positions", tags=["LED Control"])
async def control_led_by_positions(request: LEDPositionsRequest):
    """ควบคุม LED หลายตำแหน่งโดยส่ง array ของ position objects"""
    try:
        led_commands = []
        invalid_positions = []
        
        # Parse each position
        import re
        for pos_data in request.positions:
            position = pos_data.position.upper().strip()
            r = pos_data.r
            g = pos_data.g
            b = pos_data.b
            
            # Parse position string
            match = re.match(r'^L(\d+)B(\d+)$', position)
            if not match:
                invalid_positions.append(f"{position}: Invalid format")
                continue
                
            level = int(match.group(1))
            block = int(match.group(2))
            
            # Validate position
            if not validate_position(level, block):
                invalid_positions.append(f"{position}: Not in shelf config")
                continue
                
            led_commands.append({
                "level": level,
                "block": block, 
                "r": r,
                "g": g,
                "b": b,
                "position": position,
                "hex_color": f"#{r:02x}{g:02x}{b:02x}"
            })
        
        if invalid_positions:
            return JSONResponse(status_code=400, content={
                "error": "Invalid positions found",
                "invalid_positions": invalid_positions,
                "valid_count": len(led_commands)
            })
        
        if not led_commands:
            return JSONResponse(status_code=400, content={
                "error": "No valid positions provided"
            })
        
        # Execute LED commands
        from core.led_controller import set_led_batch
        set_led_batch(led_commands)
        
        return {
            "ok": True,
            "count": len(led_commands),
            "positions": [cmd["position"] for cmd in led_commands],
            "colors": [
                {
                    "position": cmd["position"], 
                    "rgb": {"r": cmd["r"], "g": cmd["g"], "b": cmd["b"]},
                    "hex": cmd["hex_color"]
                } for cmd in led_commands
            ]
        }
        
    except Exception as e:
        return JSONResponse(status_code=400, content={
            "error": "Invalid request",
            "detail": str(e)
        })
    

@router.post("/api/led/clear", tags=["System"])
async def clear_leds():
    try:
        from core.led_controller import clear_all_leds
        clear_all_leds()
        
        # LED clear logged locally only
        print(f"💡 All LEDs cleared via API")
        
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "LED clear failed", "detail": str(e)})

@router.post("/api/led/clear-and-batch", tags=["LED Control"])
async def control_led_clear_and_batch(request: LEDClearAndBatch):
    """
    ควบคุม LED แบบ clear และ batch พร้อมกัน เพื่อป้องกันการกระพริบ
    รองรับการ clear ก่อน (ถ้า clear_first=True) แล้วจึง set LED หลายตำแหน่งพร้อมกัน
    """
    try:
        led_commands = []
        invalid_positions = []
        
        # Parse และ validate ทุก position ก่อน
        import re
        for pos_data in request.positions:
            position = pos_data.position.upper().strip()
            r = pos_data.r
            g = pos_data.g
            b = pos_data.b
            
            # Parse position string
            match = re.match(r'^L(\d+)B(\d+)$', position)
            if not match:
                invalid_positions.append(f"{position}: Invalid format")
                continue
                
            level = int(match.group(1))
            block = int(match.group(2))
            
            # Validate position exists in shelf config
            if not validate_position(level, block):
                invalid_positions.append(f"{position}: Not in shelf config")
                continue
                
            led_commands.append({
                "level": level,
                "block": block, 
                "r": r,
                "g": g,
                "b": b,
                "position": position,
                "hex_color": f"#{r:02x}{g:02x}{b:02x}"
            })
        
        if invalid_positions:
            return JSONResponse(status_code=400, content={
                "error": "Invalid positions found",
                "invalid_positions": invalid_positions,
                "valid_count": len(led_commands)
            })
        
        if not led_commands:
            return JSONResponse(status_code=400, content={
                "error": "No valid positions provided"
            })
        
        # Clear LEDs ก่อนถ้า clear_first=True
        if request.clear_first:
            from core.led_controller import clear_all_leds
            clear_all_leds()
            print(f"💡 LEDs cleared before batch operation")
            
            # เพิ่ม delay เล็กน้อยถ้าต้องการ
            if request.delay_ms > 0:
                import asyncio
                await asyncio.sleep(request.delay_ms / 1000.0)
        
        # Execute LED batch commands
        from core.led_controller import set_led_batch
        set_led_batch(led_commands)
        
        print(f"💡 LED Clear & Batch: {len(led_commands)} positions controlled")
        for cmd in led_commands:
            print(f"   {cmd['position']} = {cmd['hex_color']}")
        
        return {
            "ok": True,
            "cleared_first": request.clear_first,
            "delay_ms": request.delay_ms if request.clear_first else 0,
            "count": len(led_commands),
            "positions": [cmd["position"] for cmd in led_commands],
            "colors": [
                {
                    "position": cmd["position"], 
                    "rgb": {"r": cmd["r"], "g": cmd["g"], "b": cmd["b"]},
                    "hex": cmd["hex_color"]
                } for cmd in led_commands
            ]
        }
        
    except Exception as e:
        return JSONResponse(status_code=400, content={
            "error": "Invalid request",
            "detail": str(e)
        })
    
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_shelf_ui(request: Request):
    return templates.TemplateResponse("shelf_ui.html", {"request": request})

@router.get("/simulator", response_class=HTMLResponse, include_in_schema=False)
def serve_simulator(request: Request):
    return templates.TemplateResponse("test_api.html", {"request": request})

@router.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "Barcode Smart Shelf Server is running"}

@router.post("/api/shelf/askCorrectShelf", tags=["Shelf Operations"])
async def ask_correct_shelf(request: LMSCheckShelfRequest):
    """
    Smart Shelf ส่งคำขอไป Gateway เพื่อตรวจสอบชั้นวางที่ถูกต้อง
    Smart Shelf → Gateway → LMS → Gateway → Smart Shelf
    """
    try:
        # รับข้อมูลจาก Pydantic model
        lot_no = request.lot_no
        
        if not lot_no:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing lot number", "status": "missing_lot"}
            )
        
        # ตรวจสอบว่า LOT นี้มีอยู่ในคิวหรือไม่
        existing_job = any(j['lot_no'] == lot_no for j in DB["jobs"])
        
        if existing_job:
            return JSONResponse(
                status_code=400, 
                content={
                    "error": "LOT already exists in queue",
                    "status": "duplicate_lot",
                    "message": f"LOT {lot_no} is already in the job queue"
                }
            )
        
        # เตรียมข้อมูลสำหรับส่งไป Gateway (เฉพาะ lot_no ตาม format ใหม่)
        gateway_payload = {
            "lot_no": lot_no
        }
        
        # ส่งไป Gateway แทนการส่งไป LMS โดยตรง
        gateway_url = f"{GATEWAY_BASE_URL}/shelf/askCorrectShelf"  # Gateway endpoint
        
        headers = {
            "Content-Type": "application/json"
        }
        
        print(f"🔄 Shelf forwarding to Gateway: {gateway_url}")
        print(f"📦 Payload: {gateway_payload}")
        
        async with httpx.AsyncClient(timeout=LMS_TIMEOUT) as client:
            response = await client.post(
                gateway_url,
                json=gateway_payload,
                headers=headers
            )
            
            if response.status_code == 200:
                gateway_response = response.json()
                print(f"📋 Gateway response: {gateway_response}")
                
                # ตรวจสอบว่ามี status และ lot_no
                if "status" in gateway_response and "lot_no" in gateway_response:
                    
                    # ตรวจสอบว่า Gateway/LMS ประมวลผลสำเร็จหรือไม่
                    if gateway_response["status"] == "success":
                        # รองรับทั้ง correct_shelf และ correct_shelf_name
                        correct_shelf = (gateway_response.get("correct_shelf_name") or 
                                       gateway_response.get("correct_shelf") or 
                                       "UNKNOWN_SHELF")
                        
                        # ตรวจสอบว่ามีข้อมูล shelf หรือไม่
                        if correct_shelf == "UNKNOWN_SHELF" or correct_shelf == "undefined" or not correct_shelf:
                            return JSONResponse(
                                status_code=404,
                                content={
                                    "error": "Shelf information not found",
                                    "message": f"No shelf information found for LOT {gateway_response['lot_no']}",
                                    "status": "not_found"
                                }
                            )
                        
                        return {
                            "status": "success",
                            "correct_shelf_name": correct_shelf,
                            "lot_no": gateway_response["lot_no"],
                            "message": gateway_response.get("message", f"Found correct shelf: {correct_shelf}")
                        }
                    else:
                        # กรณี error response แบบใหม่ที่มี code และ data
                        error_code = gateway_response.get("code", 400)
                        return JSONResponse(
                            status_code=error_code,
                            content={
                                "error": "Gateway/LMS processing failed",
                                "message": gateway_response.get("message", "Unknown error from Gateway/LMS"),
                                "status": gateway_response["status"],
                                "code": error_code,
                                "data": gateway_response.get("data", [])
                            }
                        )
                else:
                    return JSONResponse(
                        status_code=502,
                        content={
                            "error": "Invalid Gateway response format",
                            "message": "Gateway response missing required fields (status, lot_no)",
                            "received_fields": list(gateway_response.keys()),
                            "raw_response": gateway_response
                        }
                    )
            else:
                # ตรวจสอบว่าเป็น error response แบบใหม่หรือไม่
                try:
                    error_response = response.json()
                    if "status" in error_response and error_response["status"] == "error":
                        error_code = error_response.get("code", response.status_code)
                        return JSONResponse(
                            status_code=error_code,
                            content={
                                "error": "Gateway/LMS error",
                                "message": error_response.get("message", "Unknown error"),
                                "status": "error",
                                "code": error_code,
                                "data": error_response.get("data", [])
                            }
                        )
                except:
                    pass  # ไม่สามารถ parse JSON ได้
                
                return JSONResponse(
                    status_code=502,
                    content={
                        "error": "Gateway server error", 
                        "message": f"Gateway server returned status {response.status_code}",
                        "detail": response.text
                    }
                )
                
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={
                "error": "Gateway server timeout",
                "message": "Connection to Gateway server timed out"
            }
        )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Gateway server unavailable",
                "message": "Cannot connect to Gateway server"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(e)
            }
        )

# Backward compatibility endpoint - รองรับ endpoint เดิม
# @router.post("/api/LMS/checkshelf", tags=["LMS Integration (Legacy)"])
# async def check_shelf_from_lms_legacy(request: LMSCheckShelfRequest):
#     """
#     Legacy endpoint สำหรับ backward compatibility
#     เรียกใช้ ask_correct_shelf ภายใน
#     """
#     # แปลง LMSCheckShelfRequest เป็น Request format
#     from fastapi import Request
#     from fastapi.datastructures import FormData
#     import json
    
#     # สร้าง mock request object
#     class MockRequest:
#         async def json(self):
#             return {
#                 "lot_no": request.lot_no,
#                 "place_flg": request.place_flg
#             }
    
#     mock_request = MockRequest()
    
#     # เรียกใช้ฟังก์ชัน ask_correct_shelf
#     return await ask_correct_shelf(mock_request)

@router.get("/command", tags=["Jobs"])
def get_all_jobs():
    return {"jobs": DB["jobs"]}

@router.get("/api/shelf/state", tags=["Jobs"])
def get_shelf_state():
    # Return lots as list per cell
    shelf_state = []
    for cell in DB["shelf_state"]:
        level, block, lots = cell
        shelf_state.append({
            "level": level,
            "block": block,
            "lots": lots
        })
    return {"shelf_state": shelf_state}

@router.get("/api/shelf/config", tags=["Jobs"])
def get_shelf_config():
    """ดึงข้อมูลการกำหนดค่าของชั้นวาง"""
    config = get_shelf_info()
    # เพิ่มข้อมูลความจุรายช่อง
    config["cell_capacities"] = {}
    for level, num_blocks in SHELF_CONFIG.items():
        for block in range(1, num_blocks + 1):
            cell_key = f"{level}-{block}"
            capacity = get_cell_capacity(level, block)
            config["cell_capacities"][cell_key] = capacity
    return config

@router.get("/api/shelf/layout/status", tags=["Shelf Layout Management"])
def get_layout_status_api():
    """
    ดึงสถานะ layout ปัจจุบัน - แสดงว่าใช้ข้อมูลจาก Gateway หรือ fallback
    """
    try:
        # Log detailed layout info to console/logs
        log_current_layout()
        
        # Return compact status for API response
        status = get_layout_status()
        
        return {
            "status": "success",
            "layout_status": status,
            "message": f"Layout loaded from {'Gateway' if status['gateway_loaded'] else 'fallback configuration'}"
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Failed to get layout status: {str(e)}"
            }
        )

@router.get("/api/shelf/capacity/{level}/{block}", tags=["Jobs"])
def get_cell_capacity_api(level: int, block: int):
    """ดึงความจุของช่องเฉพาะ"""
    if not validate_position(level, block):
        return {
            "error": "Invalid position",
            "message": f"Position L{level}B{block} does not exist in shelf configuration"
        }
    
    capacity = get_cell_capacity(level, block)
    lots = get_lots_in_position(level, block)
    current_tray = sum(lot.get("tray_count", 0) for lot in lots)
    
    return {
        "level": level,
        "block": block,
        "max_capacity": capacity,
        "current_tray": current_tray,
        "available_space": capacity - current_tray,
        "usage_percentage": round((current_tray / capacity) * 100, 1) if capacity > 0 else 0,
        "is_full": current_tray >= capacity
    }

@router.get("/api/shelf/position/{level}/{block}", tags=["Jobs"])
def get_position_info(level: int, block: int):
    """ดึงข้อมูลของช่องเฉพาะ (level, block)"""
    if not validate_position(level, block):
        return {
            "error": "Invalid position",
            "message": f"Position L{level}B{block} does not exist in shelf configuration"
        }
    lots = get_lots_in_position(level, block)
    return {
        "level": level,
        "block": block,
        "lots": lots,
        "message": f"Position L{level}B{block}: {len(lots)} lot(s)"
    }

@router.get("/api/shelf/lots", tags=["Jobs"])
def get_all_lots_in_shelf():
    """ดึงรายการ Lot ทั้งหมดที่อยู่ในชั้นวาง (ทุก lot ทุก cell)"""
    lots_info = []
    for cell in DB["shelf_state"]:
        level, block, lots = cell
        for lot in lots:
            lots_info.append({
                "level": level,
                "block": block,
                "lot_no": lot["lot_no"],
                "tray_count": lot["tray_count"]
            })
    return {
        "total_lots": len(lots_info),
        "lots": lots_info
    }

@router.post("/command", status_code=201, tags=["Jobs"])
async def create_job_via_api(job: JobRequest):
    # ตรวจสอบงานซ้ำ
    existing_lot = any(j['lot_no'] == job.lot_no for j in DB["jobs"])
    if existing_lot:
         print(f"API: Rejected duplicate job for Lot {job.lot_no}")
         return {"status": "error", "message": f"Job for lot {job.lot_no} already exists in the queue."}

    # ตรวจสอบงานหยิบ (pick)
    if job.place_flg == "0":  # งานหยิบ (pick)
        level = int(job.level)
        block = int(job.block)
        
        # ตรวจสอบว่า position ถูกต้องหรือไม่
        if not validate_position(level, block):
            print(f"API: Rejected job for invalid position L{level}B{block}")
            return {
                "status": "error", 
                "message": f"Invalid position L{level}B{block} does not exist in shelf configuration"
            }
        
        # ตรวจสอบว่า lot_no มีอยู่ในช่องนั้นหรือไม่
        lots_in_cell = get_lots_in_position(level, block)
        lot_exists = any(lot["lot_no"] == job.lot_no for lot in lots_in_cell)
        
        if not lot_exists:
            print(f"API: Rejected pick job for Lot {job.lot_no} - not found in L{level}B{block}")
            return {
                "status": "error", 
                "message": f"Lot {job.lot_no} not found in position L{level}B{block}. Cannot create pick job for non-existent lot."
            }
        
        print(f"API: Validation passed - Lot {job.lot_no} exists in L{level}B{block}")

    print(f"API: Received new job for Lot {job.lot_no}")
    
    # ตรวจสอบ biz (บังคับ)
    if not hasattr(job, 'biz') or not job.biz:
        print(f"API: Rejected job - missing biz field")
        return {"status": "error", "message": "biz field is required"}
    
    # ใช้ shelf_id จาก global ถ้ามี หรือจาก request
    shelf_id = GLOBAL_SHELF_INFO.get("shelf_id") or getattr(job, 'shelf_id', None)
    if not shelf_id:
        print(f"API: Warning - no shelf_id available, using UNKNOWN")
        shelf_id = "UNKNOWN"
    
    # สร้าง job object
    new_job = job.dict()
    new_job["shelf_id"] = shelf_id  # ใช้ shelf_id จาก global หรือ request
    
    # เพิ่ม tray_count default ถ้าไม่มี
    if "tray_count" not in new_job:
        new_job["tray_count"] = 1
    else:
        new_job["tray_count"] = int(new_job.get("tray_count", 1))
    
    DB["job_counter"] += 1
    new_job["jobId"] = f"job_{DB['job_counter']}"
    DB["jobs"].append(new_job)
    
    print(f"✅ Created job {new_job['jobId']} - Biz: {new_job['biz']}, Shelf: {new_job['shelf_id']}, Lot: {new_job['lot_no']}")
    
    # Job creation logged locally only
    print(f"📋 Job created: {new_job['jobId']} - {new_job['lot_no']} (Biz: {new_job['biz']}, Shelf: {new_job['shelf_id']})")
    
    await manager.broadcast(json.dumps({"type": "new_job", "payload": new_job}))
    return {"status": "success", "job_data": new_job}

@router.post("/command/{job_id}/complete", tags=["Jobs"])
async def complete_job(job_id: str):
    print(f"API: Received 'Task Complete' for job {job_id}")
    job = get_job_by_id(job_id)
    if not job:
        return {"status": "error", "message": "Job not found"}
    
    # ตรวจสอบข้อมูลที่จำเป็น
    if not job.get("biz"):
        print(f"⚠️ Job {job_id} missing biz field")
        return {"status": "error", "message": "Job missing biz field"}
    
    level = int(job["level"])
    block = int(job["block"])
    lot_no = job["lot_no"]
    tray_count = int(job.get("tray_count", 1))
    biz = job["biz"]
    shelf_id = job.get("shelf_id", "UNKNOWN")
    
    if job["place_flg"] == "1":
        # วางของ: เพิ่ม lot เข้า cell พร้อม biz
        add_lot_to_position(level, block, lot_no, tray_count, biz)
        action = "placed"
    else:
        # หยิบของ: ลบ lot ออกจาก cell
        remove_lot_from_position(level, block, lot_no)
        action = "picked"
    
    # ส่งข้อมูล ShelfComplete ไปยัง Gateway (job มีข้อมูล biz และ shelf_id แล้ว)
    gateway_success = await send_shelf_complete_to_gateway(job)
    
    print(f"📋 Job {job_id} completed - Biz: {biz}, Shelf: {shelf_id}, Lot: {lot_no}, Action: {action}")
    
    # Job completion logged locally (Gateway data sent via send_shelf_complete_to_gateway)
    print(f"✅ Job completed: {job_id} - {lot_no} ({action}) - Gateway: {'✅' if gateway_success else '❌'}")
    
    # 🔽 AUTO-SYNC SHELF STATE TO GATEWAY AFTER JOB COMPLETION 🔽
    try:
        # สร้าง current shelf_state สำหรับส่งไป Gateway
        current_shelf_state = {}
        for cell in DB["shelf_state"]:
            l, b, lots = cell
            position_key = f"L{l}B{b}"
            current_shelf_state[position_key] = {
                "level": l,
                "block": b, 
                "lots": lots,
                "total_trays": sum(lot.get("tray_count", 1) for lot in lots) if lots else 0
            }
        
        # ส่งไป Gateway
        sync_success = await sync_shelf_state_to_gateway(current_shelf_state)
        print(f"📡 Shelf state auto-sync after job completion: {'✅' if sync_success else '❌'}")
        
    except Exception as e:
        print(f"⚠️ Auto-sync shelf state failed: {e}")
        # ไม่ให้ error นี้ขัดขวางการทำงานหลัก
    
    # ลบงานออกจากคิว
    DB["jobs"] = [j for j in DB["jobs"] if j.get("jobId") != job_id]
    
    # Broadcast shelf_state as lots per cell
    shelf_state = []
    for cell in DB["shelf_state"]:
        l, b, lots = cell
        shelf_state.append({"level": l, "block": b, "lots": lots})
    await manager.broadcast(json.dumps({
        "type": "job_completed",
        "payload": {
            "completedJobId": job_id,
            "shelf_state": shelf_state,
            "lot_no": lot_no,
            "biz": biz,
            "shelf_id": shelf_id,
            "action": action,
            "gateway_success": gateway_success
        }
    }))
    return {
        "status": "success",
        "lot_no": lot_no,
        "action": action,
        "location": f"L{level}B{block}"
    }

@router.post("/command/{job_id}/error", tags=["Jobs"])
async def error_job(job_id: str, body: ErrorRequest):
    print(f"API: Received 'Error' for job {job_id}")
    job = get_job_by_id(job_id)
    if not job: return {"status": "error", "message": "Job not found"}
        
    job["trn_status"] = "2"
    job["error"] = True
    job["errorLocation"] = body.errorLocation
    
    # Job error logged locally only
    print(f"❌ Job error: {job_id} - {job['lot_no']} at {body.errorLocation}")
    
    await manager.broadcast(json.dumps({"type": "job_error", "payload": job}))
    return {"status": "success"}

@router.post("/api/system/reset", tags=["System"])
async def reset_system():
    print("API: Received 'System Reset'")
    DB["jobs"] = []
    # Reset shelf_state to empty stacked lots
    DB["shelf_state"] = []
    for level, num_blocks in SHELF_CONFIG.items():
        for block in range(1, num_blocks + 1):
            DB["shelf_state"].append([level, block, []])
    DB["job_counter"] = 0
    await manager.broadcast(json.dumps({"type": "system_reset"}))
    return {"status": "success"}

@router.post("/clearCommand", tags=["Gateway Operations"])
async def clear_command_from_gateway(request: Request):
    """
    Gateway สั่งยกเลิกงานเฉพาะ lot_no ออกจากคิว
    
    Request Body:
    {
        "shelf_id": "shelf_001",
        "lot_no": "LOT123456",
        "level": 1,
        "block": 2,
        "biz": "business_code"
    }
    """
    try:
        payload = await request.json()
        shelf_id = payload.get("shelf_id")
        lot_no = payload.get("lot_no")
        level = payload.get("level")
        block = payload.get("block")
        biz = payload.get("biz")
        
        print(f"🗑️ Gateway Clear Command: Shelf {shelf_id}, Lot {lot_no}, Position L{level}B{block}")
        
        # ตรวจสอบข้อมูลที่จำเป็น
        if not lot_no:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "shelf_id": shelf_id,
                    "lot_no": lot_no,
                    "message": "Missing lot_no parameter"
                }
            )
        
        # ค้นหางานที่ต้องการยกเลิก
        job_to_cancel = None
        for job in DB["jobs"]:
            if job.get("lot_no") == lot_no:
                job_to_cancel = job
                break
        
        if not job_to_cancel:
            # ไม่พบงานในคิว - อาจจะเสร็จแล้วหรือไม่มี
            return JSONResponse(
                status_code=404,
                content={
                    "status": "not_found",
                    "shelf_id": shelf_id,
                    "lot_no": lot_no,
                    "message": f"Job for lot {lot_no} not found in queue"
                }
            )
        
        # ลบงานออกจากคิว
        DB["jobs"] = [job for job in DB["jobs"] if job.get("lot_no") != lot_no]
        
        # ล้าง LED สำหรับตำแหน่งนั้น (ถ้ามีการระบุ level, block)
        if level and block:
            try:
                from core.led_controller import set_led
                set_led(int(level), int(block), 0, 0, 0)  # Turn off LED
                print(f"💡 LED cleared for L{level}B{block}")
            except Exception as led_error:
                print(f"⚠️ LED clear failed: {led_error}")
        
        print(f"✅ Gateway Clear Command Success: Lot {lot_no} removed from queue")
        
        # Broadcast to WebSocket clients
        broadcast_message = {
            "type": "job_canceled",
            "payload": {
                "lot_no": lot_no,
                "level": level,
                "block": block,
                "shelf_id": shelf_id,
                "biz": biz,
                "canceled_job": job_to_cancel,
                "message": f"Job for lot {lot_no} canceled by Gateway"
            }
        }
        
        print(f"📡 Broadcasting job_canceled: {broadcast_message}")
        await manager.broadcast(json.dumps(broadcast_message))
        
        return {
            "status": "success",
            "shelf_id": shelf_id,
            "lot_no": lot_no,
            "message": f"Command canceled successfully for lot {lot_no}",
            "canceled_job": job_to_cancel
        }
        
    except Exception as e:
        print(f"❌ Gateway Clear Command Error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "shelf_id": payload.get("shelf_id", "unknown") if 'payload' in locals() else "unknown",
                "lot_no": payload.get("lot_no", "unknown") if 'payload' in locals() else "unknown",
                "message": f"Internal server error: {str(e)}"
            }
        )

@router.get("/api/shelf/occupied", tags=["Jobs"])
def get_occupied_positions():
    """ดึงข้อมูลเฉพาะช่องที่มีของอยู่ในชั้นวาง (มี lot อย่างน้อย 1)"""
    occupied_positions = []
    for cell in DB["shelf_state"]:
        level, block, lots = cell
        if lots:
            for lot in lots:
                occupied_positions.append({
                    "position": f"L{level}B{block}",
                    "level": level,
                    "block": block,
                    "lot_no": lot["lot_no"],
                    "tray_count": lot["tray_count"]
                })
    return {
        "total_occupied": len(occupied_positions),
        "occupied_positions": occupied_positions
    }

@router.get("/api/shelf/summary", tags=["Jobs"])
def get_shelf_summary():
    """ดึงสรุปข้อมูลชั้นวางทั้งหมด (stacked lots)"""
    total_positions = len(DB["shelf_state"])
    occupied_count = 0
    empty_count = 0
    occupied_list = []
    for cell in DB["shelf_state"]:
        level, block, lots = cell
        if lots:
            occupied_count += 1
            for lot in lots:
                occupied_list.append({
                    "position": f"L{level}B{block}",
                    "lot_no": lot["lot_no"],
                    "tray_count": lot["tray_count"]
                })
        else:
            empty_count += 1
    return {
        "summary": {
            "total_positions": total_positions,
            "occupied": occupied_count,
            "empty": empty_count,
            "occupancy_rate": f"{(occupied_count/total_positions)*100:.1f}%"
        },
        "occupied_details": occupied_list
    }

@router.get("/api/shelf/pending", tags=["Shelf Operations"])
async def get_pending_jobs_from_gateway():
    """
    ดึงงานที่ค้างอยู่จาก Gateway API สำหรับการกู้คืนหลังไฟดับ
    Flow: Smart Shelf → Gateway → Response with pending jobs
    """
    try:
        # ขั้นตอนที่ 1: ตรวจสอบ shelf_id จาก global หรือดึงใหม่
        shelf_id = GLOBAL_SHELF_INFO.get("shelf_id")
        
        if not shelf_id:
            print("🔄 No shelf_id in global, fetching from Gateway...")
            
            # ดึง shelf_id จาก Gateway ก่อน
            local_ip = get_actual_local_ip()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    'http://43.72.20.238:8000/IoTManagement/shelf/requestID',
                    headers={
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                    },
                    json={"shelf_ip": local_ip}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    shelf_id = data.get("shelf_id")
                    
                    # อัพเดท global
                    GLOBAL_SHELF_INFO["shelf_id"] = shelf_id
                    GLOBAL_SHELF_INFO["shelf_name"] = data.get("shelf_name")
                    GLOBAL_SHELF_INFO["local_ip"] = local_ip
                    
                    print(f"✅ Got shelf_id: {shelf_id}")
                else:
                    return JSONResponse(
                        status_code=502,
                        content={
                            "error": "Cannot get shelf_id from Gateway",
                            "status": "gateway_error",
                            "message": f"Gateway returned {response.status_code}"
                        }
                    )
        
        # ขั้นตอนที่ 2: ดึงงานที่ค้างอยู่จาก Gateway
        pending_url = f"{GATEWAY_BASE_URL}/IoTManagement/shelf/pending/{shelf_id}"
        print(f"🔄 Fetching pending jobs from: {pending_url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                pending_url,
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                pending_data = response.json()
                print(f"📦 Gateway pending response: {pending_data}")
                
                if pending_data.get("status") == "success" and "data" in pending_data:
                    jobs_data = pending_data["data"]
                    
                    # แปลงข้อมูลเป็น format ที่ใช้ใน Smart Shelf
                    converted_jobs = []
                    for gateway_job in jobs_data:
                        # สร้าง jobId ใหม่ด้วย job_counter ของ local
                        DB["job_counter"] += 1
                        local_job_id = f"job_{DB['job_counter']}"
                        
                        converted_job = {
                            "jobId": local_job_id,  # ใช้ local job_counter สร้าง jobId ใหม่
                            "lot_no": gateway_job.get("lot_no"),
                            "level": gateway_job.get("level"),
                            "block": gateway_job.get("block"),
                            "place_flg": gateway_job.get("place_flg"),
                            "tray_count": gateway_job.get("tray_count"),
                            "status": gateway_job.get("status"),
                            "biz": gateway_job.get("biz", "Unknown"),
                            "shelf_id": shelf_id,
                            "create_date": gateway_job.get("create_date"),
                            "source": "gateway_recovery",
                            "gateway_job_id": gateway_job.get("job_id")  # เก็บ original job_id ไว้สำหรับส่งกลับ Gateway
                        }
                        converted_jobs.append(converted_job)
                    
                    print(f"✅ Converted {len(converted_jobs)} pending jobs")
                    
                    return {
                        "status": "success",
                        "shelf_id": shelf_id,
                        "total_pending": len(converted_jobs),
                        "jobs": converted_jobs,
                        "message": f"Found {len(converted_jobs)} pending jobs for shelf {shelf_id}"
                    }
                else:
                    return {
                        "status": "success",
                        "shelf_id": shelf_id,
                        "total_pending": 0,
                        "jobs": [],
                        "message": f"No pending jobs found for shelf {shelf_id}"
                    }
            else:
                return JSONResponse(
                    status_code=502,
                    content={
                        "error": "Gateway pending jobs request failed",
                        "status": "gateway_error",
                        "message": f"Gateway returned {response.status_code}",
                        "detail": response.text
                    }
                )
                
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={
                "error": "Gateway timeout",
                "status": "timeout",
                "message": "Connection to Gateway timed out"
            }
        )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Gateway unavailable",
                "status": "connection_error",
                "message": "Cannot connect to Gateway server"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status": "server_error",
                "message": str(e)
            }
        )

@router.post("/api/shelf/pending/load", tags=["Shelf Operations"])
async def load_pending_jobs_into_queue():
    """
    ดึงงานที่ค้างอยู่จาก Gateway และเพิ่มเข้า local job queue
    ใช้สำหรับการกู้คืนงานหลังจากไฟดับหรือรีสตาร์ทระบบ
    """
    try:
        # เรียกใช้ฟังก์ชันดึงงานที่ค้างอยู่
        pending_response = await get_pending_jobs_from_gateway()
        
        # ตรวจสอบว่าได้ response ที่ถูกต้องหรือไม่
        if isinstance(pending_response, JSONResponse):
            # ถ้าเป็น error response ให้ return เลย
            return pending_response
        
        if pending_response.get("status") != "success":
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Failed to get pending jobs",
                    "message": pending_response.get("message", "Unknown error")
                }
            )
        
        pending_jobs = pending_response.get("jobs", [])
        
        if not pending_jobs:
            return {
                "status": "success",
                "message": "No pending jobs to load",
                "loaded_count": 0,
                "skipped_count": 0,
                "total_queue_size": len(DB["jobs"])
            }
        
        # เพิ่มงานเข้า local queue (ข้ามงานซ้ำ)
        loaded_count = 0
        skipped_count = 0
        
        for pending_job in pending_jobs:
            # ตรวจสอบงานซ้ำ (lot_no, level, block) เท่านั้น ไม่สนใจ gateway_job_id
            job_exists = any(
                job["lot_no"] == pending_job["lot_no"] and
                job["level"] == pending_job["level"] and
                job["block"] == pending_job["block"]
                for job in DB["jobs"]
            )
            
            if not job_exists:
                # เพิ่มงานใหม่เข้า queue
                DB["jobs"].append(pending_job)
                loaded_count += 1
                print(f"✅ Loaded pending job: {pending_job['jobId']} - {pending_job['lot_no']} (L{pending_job['level']}B{pending_job['block']})")
            else:
                skipped_count += 1
                print(f"⚠️ Skipped duplicate job: {pending_job['jobId']} - {pending_job['lot_no']} (L{pending_job['level']}B{pending_job['block']})")
        
        # Broadcast ไปยัง WebSocket clients
        if loaded_count > 0:
            for job in pending_jobs[-loaded_count:]:  # ส่งเฉพาะงานที่เพิ่มจริง
                if not any(
                    existing_job["lot_no"] == job["lot_no"] and
                    existing_job["level"] == job["level"] and
                    existing_job["block"] == job["block"]
                    for existing_job in DB["jobs"][:-loaded_count]  # ไม่นับงานที่เพิ่มใหม่
                ):
                    await manager.broadcast(json.dumps({
                        "type": "new_job", 
                        "payload": job
                    }))
        
        return {
            "status": "success",
            "message": f"Successfully loaded {loaded_count} pending jobs into queue",
            "loaded_count": loaded_count,
            "skipped_count": skipped_count,
            "total_pending": len(pending_jobs),
            "total_queue_size": len(DB["jobs"])
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to load pending jobs",
                "status": "server_error",
                "message": str(e)
            }
        )

@router.post("/api/shelf/layout", tags=["Shelf Layout Management"])
async def manage_shelf_layout(layout_request: LayoutRequest):
    """
    จัดการ layout ของชั้นวาง - ดึงข้อมูลจาก Gateway และอัปเดต local database
    
    Parameters:
    - shelf_id: รหัสชั้นวาง (เช่น "PC2")
    - update_flg: "0" = อ่านข้อมูล, "1" = เขียนข้อมูล
    - slots: ข้อมูล layout (ใช้เมื่อ update_flg = "1")
    
    Returns:
    - Layout configuration พร้อมข้อมูล capacity และ active status
    """
    try:
        shelf_id = layout_request.shelf_id
        update_mode = layout_request.update_flg
        slots_data = layout_request.slots
        
        print(f"📋 Layout Management: ID={shelf_id}, Mode={update_mode}")
        
        if update_mode == "0":
            # Read mode - ดึงข้อมูลจาก Gateway
            print(f"📖 Reading layout from Gateway...")
            
            layout_data = await fetch_layout_from_gateway(shelf_id)
            
            if layout_data and layout_data.get("status") == "success":
                gateway_layout = layout_data.get("layout", {})
                
                # อัปเดต local database configuration
                from core.database import update_layout_from_gateway
                update_success = update_layout_from_gateway(gateway_layout)
                
                if update_success:
                    print(f"✅ Local database updated with Gateway layout")
                    
                    # Broadcast layout update to WebSocket clients  
                    try:
                        await manager.broadcast(json.dumps({
                            "type": "layout_updated",
                            "payload": {
                                "shelf_id": shelf_id,
                                "layout": gateway_layout,
                                "source": "gateway_fetch"
                            }
                        }))
                        print(f"📡 Broadcasted layout update to WebSocket clients")
                    except Exception as broadcast_error:
                        print(f"⚠️ WebSocket broadcast failed: {broadcast_error}")
                
                return {
                    "status": "success",
                    "shelf_id": shelf_id,
                    "update_flg": "0",
                    "layout": gateway_layout,
                    "local_update": update_success,
                    "message": f"Layout fetched from Gateway for shelf {shelf_id}"
                }
            else:
                return JSONResponse(
                    status_code=502,
                    content={
                        "status": "error",
                        "shelf_id": shelf_id,
                        "message": "Failed to fetch layout from Gateway",
                        "gateway_response": layout_data
                    }
                )
        
        elif update_mode == "1":
            # Write mode - ส่งข้อมูลไป Gateway (Future feature)
            print(f"💾 Writing layout to Gateway...")
            
            sync_success = await sync_layout_to_gateway(slots_data, shelf_id)
            
            return {
                "status": "success" if sync_success else "error",
                "shelf_id": shelf_id,
                "update_flg": "1",
                "slots": slots_data,
                "gateway_sync": sync_success,
                "message": "Layout synced to Gateway" if sync_success else "Gateway sync failed"
            }
        
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Invalid update_flg. Use '0' for read or '1' for write"
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

@router.get("/ShelfName", tags=["Shelf Operations"])
async def get_shelf_info_endpoint():
    """
    Endpoint สำหรับดึงข้อมูล shelf name จาก Gateway API
    และเก็บข้อมูลไว้ใน global variable
    """
    try:
        local_ip = get_actual_local_ip()
        print(f"🌐 Local IP: {local_ip}")
        
        # เรียก Gateway API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                'http://43.72.20.238:8000/IoTManagement/shelf/requestID',
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                json={
                    "shelf_ip": local_ip  # ใช้ local IP จริง
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Gateway Response: {data}")
                
                # เก็บข้อมูลใน global variable
                GLOBAL_SHELF_INFO["shelf_id"] = data.get("shelf_id")
                GLOBAL_SHELF_INFO["shelf_name"] = data.get("shelf_name")
                GLOBAL_SHELF_INFO["local_ip"] = local_ip
                
                print(f"💾 Stored global shelf info: {GLOBAL_SHELF_INFO}")
                
                return {
                    "success": True,
                    "shelf_id": data.get("shelf_id"),
                    "shelf_name": data.get("shelf_name"),
                    "local_ip": local_ip
                }
            else:
                print(f"❌ Gateway Error: {response.status_code}")
                # ใช้ค่า fallback แต่ไม่เก็บใน global
                return {
                    "success": False,
                    "error": f"Gateway returned {response.status_code}",
                    "shelf_id": "UNKNOWN",
                    "shelf_name": "Shelf",
                    "local_ip": local_ip
                }
                
    except Exception as e:
        print(f"Error calling Gateway: {e}")
        return {
            "success": False,
            "error": str(e),
            "shelf_id": "ERROR",  
            "shelf_name": "Shelf",
            "local_ip": "unknown"
        }

# === Shelf State Management Functions ===

async def sync_shelf_state_to_gateway(shelf_state_data):
    """
    ส่ง shelf_state ไปยัง Gateway เพื่อบันทึกสถานะปัจจุบัน
    """
    try:
        shelf_id = GLOBAL_SHELF_INFO.get("shelf_id", "UNKNOWN")
        
        # แปลงเป็น array format สำหรับ Gateway
        shelf_state_array = []
        if isinstance(shelf_state_data, dict):
            # แปลงจาก dict เป็น array
            for position_key, position_data in shelf_state_data.items():
                shelf_state_array.append({
                    "level": position_data["level"],
                    "block": position_data["block"], 
                    "lots": position_data["lots"]
                })
        else:
            # ถ้าเป็น array อยู่แล้ว
            shelf_state_array = shelf_state_data
        
        gateway_payload = {
            "shelf_id": shelf_id,
            "update_flg": "1",  # เปลี่ยนจาก update เป็น update_flg
            "shelf_state": shelf_state_array
        }
        
        headers = {
            "Accept": "application/json", 
            "Content-Type": "application/json"
        }
        
        print(f"🔄 Syncing shelf state to Gateway: {GATEWAY_BASE_URL}/IoTManagement/shelf/shelfItem")
        print(f"📦 Payload: {gateway_payload}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GATEWAY_BASE_URL}/IoTManagement/shelf/shelfItem",
                json=gateway_payload,
                headers=headers
            )
            
            print(f"📡 Gateway Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Shelf state synced successfully")
                return True
            else:
                print(f"⚠️ Gateway sync failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"⚠️ Shelf state sync error: {e}")
        return False

async def restore_shelf_state_from_gateway():
    """
    กู้คืน shelf_state จาก Gateway เมื่อเริ่มต้นระบบ
    """
    try:
        shelf_id = GLOBAL_SHELF_INFO.get("shelf_id")
        
        if not shelf_id:
            print(f"⚠️ No shelf_id available for state restore")
            return None
            
        gateway_payload = {
            "shelf_id": shelf_id,
            "update_flg": "0",  # เปลี่ยนจาก update เป็น update_flg
            "shelf_state": []  # empty array for read
        }
        
        headers = {
            "Accept": "application/json", 
            "Content-Type": "application/json"
        }
        
        print(f"🔄 Restoring shelf state from Gateway: {GATEWAY_BASE_URL}/IoTManagement/shelf/shelfItem")
        print(f"📦 Read Payload: {gateway_payload}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GATEWAY_BASE_URL}/IoTManagement/shelf/shelfItem",
                json=gateway_payload,
                headers=headers
            )
            
            print(f"📡 Gateway Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ Shelf state restored successfully")
                print(f"📦 Restored state: {response_data}")
                
        
                shelf_state = response_data.get("data", [])
                
                return shelf_state
            else:
                print(f"⚠️ Gateway restore failed: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        print(f"⚠️ Shelf state restore error: {e}")
        return None

@router.post("/api/shelf/shelfItem", tags=["Shelf State Management"])
async def manage_shelf_state(shelf_state_request: ShelfState):
    """
    จัดการ shelf state - รองรับทั้งการอ่าน (update_flg="0") และการเขียน (update_flg="1")
    ใช้เชื่อมต่อกับ Gateway API รูปแบบใหม่
    
    Example Values:
    - shelf_id: "PC2"
    - update_flg: "0" (read) or "1" (write)
    - shelf_state: Array of BlockState objects with lots data
    """
    try:
        shelf_id = shelf_state_request.shelf_id
        update_mode = shelf_state_request.update_flg  
        shelf_state_data = shelf_state_request.shelf_state
        
        print(f"📋 Shelf State Management: ID={shelf_id}, Mode={update_mode}")
        
        # Validate required fields
        if not shelf_id:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "shelf_id is required"
                }
            )
        
        if update_mode not in ["0", "1"]:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error", 
                    "message": "update_flg must be '0' (read) or '1' (write)"
                }
            )
        
        if update_mode == "0":
            # Read mode - กู้คืนสถานะจาก Gateway
            print(f"📖 Reading shelf state from Gateway...")
            
            restored_state = await restore_shelf_state_from_gateway()
            
            if restored_state is not None and len(restored_state) > 0:
                # อัปเดต local database ด้วยข้อมูลที่กู้คืนได้
                # แปลงจาก Gateway array format เป็น local DB format
                DB["shelf_state"] = []
                for level, num_blocks in SHELF_CONFIG.items():
                    for block in range(1, num_blocks + 1):
                        DB["shelf_state"].append([level, block, []])
                
                # อัปเดตด้วยข้อมูลจาก Gateway
                for cell_data in restored_state:
                    level = cell_data.get("level")
                    block = cell_data.get("block") 
                    lots = cell_data.get("lots", [])
                    
                    # หา cell ที่ตรงกันใน DB
                    for i, (l, b, existing_lots) in enumerate(DB["shelf_state"]):
                        if l == level and b == block:
                            DB["shelf_state"][i] = [level, block, lots]
                            break
                
                print(f"✅ Local DB updated with restored state")
                
                # Broadcast restored state to WebSocket clients
                try:
                    websocket_shelf_state = []
                    for cell in DB["shelf_state"]:
                        level, block, lots = cell
                        websocket_shelf_state.append({"level": level, "block": block, "lots": lots})
                    
                    await manager.broadcast(json.dumps({
                        "type": "shelf_state_restored",
                        "payload": {
                            "shelf_state": websocket_shelf_state,
                            "shelf_id": shelf_id,
                            "source": "gateway_restore"
                        }
                    }))
                    print(f"📡 Broadcasted restored shelf state to WebSocket clients")
                except Exception as broadcast_error:
                    print(f"⚠️ WebSocket broadcast failed: {broadcast_error}")
                
                return {
                    "status": "success", 
                    "shelf_id": shelf_id,
                    "update_flg": "0",
                    "shelf_state": restored_state,
                    "message": "Shelf state restored from Gateway"
                }
            else:
                # ถ้าไม่มีข้อมูลใน Gateway ให้ส่ง current state กลับ
                current_state = []
                for cell in DB["shelf_state"]:
                    level, block, lots = cell
                    if lots:  # ส่งเฉพาะ cell ที่มีของ
                        current_state.append({
                            "level": level,
                            "block": block,
                            "lots": lots
                        })
                
                return {
                    "status": "success",
                    "shelf_id": shelf_id, 
                    "update_flg": "0",
                    "shelf_state": current_state,
                    "message": "No data in Gateway, using current local state"
                }
        
        elif update_mode == "1":
            # Write mode - บันทึกสถานะไป Gateway
            print(f"💾 Writing shelf state to Gateway...")
            
            # อัปเดต local database ด้วยข้อมูลที่ส่งมา
            if shelf_state_data and len(shelf_state_data) > 0:
                # รีเซ็ต shelf_state
                DB["shelf_state"] = []
                for level, num_blocks in SHELF_CONFIG.items():
                    for block in range(1, num_blocks + 1):
                        DB["shelf_state"].append([level, block, []])
                
                # อัปเดตด้วยข้อมูลใหม่ (แปลง Pydantic models เป็น dict)
                for cell_data in shelf_state_data:
                    # แปลง BlockState object เป็น dict
                    if hasattr(cell_data, 'dict'):
                        cell_dict = cell_data.dict()
                    else:
                        cell_dict = cell_data
                        
                    level = cell_dict.get("level")
                    block = cell_dict.get("block")
                    lots = cell_dict.get("lots", [])
                    
                    # แปลง LotData objects เป็น dict ถ้าจำเป็น
                    lots_dict = []
                    for lot in lots:
                        if hasattr(lot, 'dict'):
                            lots_dict.append(lot.dict())
                        else:
                            lots_dict.append(lot)
                    
                    # หา cell ที่ตรงกันใน DB
                    for i, (l, b, existing_lots) in enumerate(DB["shelf_state"]):
                        if l == level and b == block:
                            DB["shelf_state"][i] = [level, block, lots_dict]
                            break
                
                print(f"✅ Local DB updated with new state")
            
            # ส่งไป Gateway (แปลง Pydantic models เป็น dict format)
            shelf_state_dict = []
            for block_state in shelf_state_data:
                if hasattr(block_state, 'dict'):
                    shelf_state_dict.append(block_state.dict())
                else:
                    shelf_state_dict.append(block_state)
            
            sync_success = await sync_shelf_state_to_gateway(shelf_state_dict)
            
            # Broadcast shelf state update to WebSocket clients
            if sync_success:
                try:
                    # แปลง shelf_state เป็น format สำหรับ WebSocket
                    websocket_shelf_state = []
                    for cell in DB["shelf_state"]:
                        level, block, lots = cell
                        websocket_shelf_state.append({"level": level, "block": block, "lots": lots})
                    
                    await manager.broadcast(json.dumps({
                        "type": "shelf_state_updated",
                        "payload": {
                            "shelf_state": websocket_shelf_state,
                            "shelf_id": shelf_id,
                            "source": "gateway_sync"
                        }
                    }))
                    print(f"📡 Broadcasted shelf state update to WebSocket clients")
                except Exception as broadcast_error:
                    print(f"⚠️ WebSocket broadcast failed: {broadcast_error}")
            
            return {
                "status": "success" if sync_success else "error",
                "shelf_id": shelf_id,
                "update_flg": "1", 
                "shelf_state": shelf_state_dict,
                "gateway_sync": sync_success,
                "message": "Shelf state updated and synced" if sync_success else "Gateway sync failed"
            }
            
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Invalid update_flg. Use '0' for read or '1' for write"
                }
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error", 
                "message": str(e)
            }
        )

# === Debug Endpoints ===
@router.get("/api/debug/position/{level}/{block}", tags=["Debug"])
async def debug_position_validation(level: int, block: int):
    """Debug position validation - ตรวจสอบว่าตำแหน่งมีอยู่หรือไม่"""
    try:
        from core.database import debug_position_validation, SHELF_CONFIG, DYNAMIC_LAYOUT
        
        # Run debug validation
        is_valid = debug_position_validation(level, block)
        
        return {
            "position": f"L{level}B{block}",
            "valid": is_valid,
            "shelf_config": SHELF_CONFIG,
            "has_gateway_layout": bool(DYNAMIC_LAYOUT),
            "gateway_positions": list(DYNAMIC_LAYOUT.keys()) if DYNAMIC_LAYOUT else []
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": "Debug validation failed",
            "detail": str(e)
        })
