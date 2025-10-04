from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import pathlib
import httpx
import re
from datetime import datetime

# --- สำหรับควบคุม LED ---
from core.led_controller import set_led

# --- Import จากไฟล์ที่เราสร้างขึ้น ---
from core.models import JobRequest, ErrorRequest, LEDPositionRequest, LEDPositionsRequest, LEDClearAndBatch, LMSCheckShelfRequest, LMSCheckShelfResponse, ShelfComplete
from core.database import (
    DB, get_job_by_id, get_lots_in_position, add_lot_to_position, remove_lot_from_position, update_lot_quantity, validate_position, get_shelf_info, SHELF_CONFIG
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

# --- Routes ---

# --- LED Control Endpoint ---
from fastapi import Request
from fastapi.responses import JSONResponse

# ลบ endpoint ที่ซ้ำกัน - ใช้แค่อันด้านล่างที่ tags=["Jobs"]
# @router.get("/api/shelf/config", tags=["System"])
# def get_shelf_config():
#     config = SHELF_CONFIG
#     total_levels = len(config)
#     max_blocks = max(config.values())
#     return JSONResponse(content={
#         "config": config,
#         "total_levels": total_levels,
#         "max_blocks": max_blocks
#     })


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

    if not (1 <= level <= 4 and 1 <= block <= 6):
        return JSONResponse(status_code=400, content={"error": "Invalid level or block"})

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
        # ตัวอย่าง: [{level, block, r, g, b}, ...]
        from core.led_controller import set_led_batch
        set_led_batch(leds)
        return {"ok": True, "count": len(leds)}
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
        result = set_led(level, block, r, g, b)
        
        # LED control logged locally only
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        print(f"💡 LED Control: L{level}B{block} = {hex_color}")
        
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
async def ask_correct_shelf(request: Request):
    """
    Smart Shelf ส่งคำขอไป Gateway เพื่อตรวจสอบชั้นวางที่ถูกต้อง
    Smart Shelf → Gateway → LMS → Gateway → Smart Shelf
    """
    try:
        # รับข้อมูลจาก client
        payload = await request.json()
        lot_no = payload.get("lot_no")
        place_flg = payload.get("place_flg", "1")
        
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
        
        # เตรียมข้อมูลสำหรับส่งไป Gateway
        gateway_payload = {
            "lot_no": lot_no,
            "place_flg": place_flg
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
                lms_response = response.json()
                
                # ตรวจสอบ response format ใหม่ที่มี status, correct_shelf, lot_no, message
                if ("status" in lms_response and "correct_shelf" in lms_response and 
                    "lot_no" in lms_response and "message" in lms_response):
                    
                    # ตรวจสอบว่า LMS ประมวลผลสำเร็จหรือไม่
                    if lms_response["status"] == "success":
                        return {
                            "status": "success",
                            "correct_shelf": lms_response["correct_shelf"],
                            "lot_no": lms_response["lot_no"],
                            "message": lms_response["message"]
                        }
                    else:
                        return JSONResponse(
                            status_code=400,
                            content={
                                "error": "LMS processing failed",
                                "message": lms_response.get("message", "Unknown error from LMS"),
                                "status": lms_response["status"]
                            }
                        )
                else:
                    return JSONResponse(
                        status_code=502,
                        content={
                            "error": "Invalid LMS response format",
                            "message": "LMS response missing required fields (status, correct_shelf, lot_no, message)",
                            "received_fields": list(lms_response.keys())
                        }
                    )
            else:
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
                "error": "LMS server timeout",
                "message": "Connection to LMS server timed out"
            }
        )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={
                "error": "LMS server unavailable",
                "message": "Cannot connect to LMS server"
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
    return get_shelf_info()

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
        # วางของ: เพิ่ม lot เข้า cell
        add_lot_to_position(level, block, lot_no, tray_count)
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
