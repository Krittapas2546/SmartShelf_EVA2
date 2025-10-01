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
from core.models import JobRequest, ErrorRequest, LEDPositionRequest, LEDPositionsRequest, LMSCheckShelfRequest, LMSCheckShelfResponse
from core.database import (
    DB, get_job_by_id, get_lots_in_position, add_lot_to_position, remove_lot_from_position, update_lot_quantity, validate_position, get_shelf_info, SHELF_CONFIG
)
from core.lms_config import LMS_BASE_URL, LMS_ENDPOINT, LMS_API_KEY, LMS_TIMEOUT
from api.websockets import manager # <-- impor        },

# Gateway Configuration  
GATEWAY_BASE_URL = "http://127.0.0.1:5001"  # Gateway server URL (port 5001)

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
    ส่ง log events ไปยัง Gateway
    ✅ ส่ง actual IP address ใน header เพื่อให้ Gateway detect shelf_id ได้
    """
    try:
        # ดึง actual local IP address
        actual_ip = get_actual_local_ip()
        
        log_payload = {
            "logs": [{
                "shelf_log_id": f"LOG_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{event_type}",
                "event_type": event_type,
                "level": event_data.get("level"),
                "block": event_data.get("block"),
                "lot_no": event_data.get("lot_no"),
                "event_detail": event_data,
                "status": "COMPLETED",
                "createdate": datetime.now().isoformat()
            }]
        }
        
        # ✅ ส่ง actual IP ใน header
        headers = {
            "Content-Type": "application/json",
            "X-Forwarded-For": actual_ip,  # Original client IP
            "X-Real-IP": actual_ip         # Real client IP
        }
        
        print(f"🔍 Sending to Gateway: {GATEWAY_BASE_URL}/shelf/logs")
        print(f"📦 Payload: {log_payload}")
        print(f"🌐 Actual IP: {actual_ip}")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{GATEWAY_BASE_URL}/shelf/logs",
                json=log_payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                detected_shelf = result.get("shelf_id", "Unknown")
                print(f"📝 Logged to Gateway: {event_type} (Auto-detected: {detected_shelf})")
                return True
            else:
                error_detail = response.text
                print(f"⚠️ Gateway log failed: {response.status_code} - {error_detail}")
                return False
                
    except Exception as e:
        print(f"⚠️ Gateway logging error: {e}")
        return False

async def get_logs_from_gateway(limit: int = 20, event_type: str = None):
    """ดึง logs จาก Gateway (ใช้ auto-detected shelf_id)"""
    try:
        params = {"limit": limit}
        if event_type:
            params["event_type"] = event_type
            
        # ✅ ใช้ endpoint ใหม่ที่ Gateway auto-detect shelf จาก IP
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GATEWAY_BASE_URL}/shelf/logs/query",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Gateway returned {response.status_code}: {response.text}"}
                
    except Exception as e:
        return {"error": str(e)}

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
        
        # 📝 Log LED control to Gateway
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        await log_to_gateway("LED_ON", {
            "level": str(level),
            "block": str(block),
            "lot_no": None,
            "color": hex_color,
            "reason": "api_request",
            "brightness": 100
        })
        
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
        
        # 📝 Log LED clear to Gateway
        await log_to_gateway("LED_OFF", {
            "reason": "clear_all_api",
            "duration": None
        })
        
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "LED clear failed", "detail": str(e)})
    
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_shelf_ui(request: Request):
    return templates.TemplateResponse("shelf_ui.html", {"request": request})

@router.get("/simulator", response_class=HTMLResponse, include_in_schema=False)
def serve_simulator(request: Request):
    return templates.TemplateResponse("test_api.html", {"request": request})

@router.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "Barcode Smart Shelf Server is running"}

# 📊 NEW: Shelf Log API Endpoints
@router.get("/api/shelf/logs", tags=["Logging"])
async def get_shelf_logs(limit: int = 20, event_type: str = None):
    """ดึง shelf logs ล่าสุด"""
    try:
        logs_data = await get_logs_from_gateway(limit=limit, event_type=event_type)
        if "error" in logs_data:
            return JSONResponse(status_code=500, content={
                "status": "error", 
                "message": f"Gateway error: {logs_data['error']}"
            })
        return {"status": "success", "logs": logs_data.get("logs", []), "count": len(logs_data.get("logs", []))}
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "status": "error", 
            "message": f"Failed to get logs: {str(e)}"
        })

@router.get("/api/shelf/logs/stats", tags=["Logging"])
async def get_shelf_log_stats():
    """ดึงสถิติ shelf logs จาก Gateway"""
    try:
        # Gateway ยังไม่มี stats endpoint - ให้ส่ง placeholder
        return {"status": "success", "stats": {"message": "Stats available from Gateway dashboard"}}
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "status": "error", 
            "message": f"Failed to get stats: {str(e)}"
        })

@router.get("/api/shelf/logs/jobs", tags=["Logging"])
async def get_job_logs(limit: int = 10):
    """ดึงแค่ job events จาก Gateway"""
    try:
        logs_data = await get_logs_from_gateway(limit=limit, event_type="JOB_")
        if "error" in logs_data:
            return JSONResponse(status_code=500, content={
                "status": "error", 
                "message": f"Gateway error: {logs_data['error']}"
            })
        job_logs = [log for log in logs_data.get("logs", []) if log.get('event_type', '').startswith('JOB_')]
        return {"status": "success", "job_logs": job_logs, "count": len(job_logs)}
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "status": "error", 
            "message": f"Failed to get job logs: {str(e)}"
        })

@router.get("/api/shelf/logs/leds", tags=["Logging"])
async def get_led_logs(limit: int = 10):
    """ดึงแค่ LED events จาก Gateway"""
    try:
        logs_data = await get_logs_from_gateway(limit=limit, event_type="LED_")
        if "error" in logs_data:
            return JSONResponse(status_code=500, content={
                "status": "error", 
                "message": f"Gateway error: {logs_data['error']}"
            })
        led_logs = [log for log in logs_data.get("logs", []) if log.get('event_type', '').startswith('LED_')]
        return {"status": "success", "led_logs": led_logs, "count": len(led_logs)}
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "status": "error", 
            "message": f"Failed to get LED logs: {str(e)}"
        })

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
    # --- START: ปิดการตรวจสอบงานซ้ำชั่วคราว (สำหรับทดสอบ) ---
    existing_lot = any(j['lot_no'] == job.lot_no for j in DB["jobs"])
    if existing_lot:
         print(f"API: Rejected duplicate job for Lot {job.lot_no}")
         return {"status": "error", "message": f"Job for lot {job.lot_no} already exists in the queue."}
    # --- END: ปิดการตรวจสอบ ---

    # --- NEW: Validate lot exists in specified position (เฉพาะงานหยิบ) ---
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
            print(f"API: Lots in cell ({level}, {block}): {[lot['lot_no'] for lot in lots_in_cell]}")
            return {
                "status": "error", 
                "message": f"Lot {job.lot_no} not found in position L{level}B{block}. Cannot create pick job for non-existent lot."
            }
        
        print(f"API: Validation passed - Lot {job.lot_no} exists in L{level}B{block}")
    # --- END: Validation ---

    print(f"API: Received new job for Lot {job.lot_no}")
    new_job = job.dict()
    # Ensure tray_count is int
    tray_count = int(new_job.get("tray_count", 1))
    new_job["tray_count"] = tray_count
    DB["job_counter"] += 1
    new_job["jobId"] = f"job_{DB['job_counter']}"
    DB["jobs"].append(new_job)
    
    # 📝 Log job creation to Gateway
    await log_to_gateway("JOB_CREATED", {
        "job_id": new_job["jobId"],
        "lot_no": new_job["lot_no"],
        "level": new_job["level"],
        "block": new_job["block"],
        "place_flg": new_job["place_flg"],
        "tray_count": tray_count,
        "source": "API"
    })
    
    await manager.broadcast(json.dumps({"type": "new_job", "payload": new_job}))
    return {"status": "success", "job_data": new_job}

@router.post("/command/{job_id}/complete", tags=["Jobs"])
async def complete_job(job_id: str):
    print(f"API: Received 'Task Complete' for job {job_id}")
    job = get_job_by_id(job_id)
    if not job:
        return {"status": "error", "message": "Job not found"}
    level = int(job["level"])
    block = int(job["block"])
    lot_no = job["lot_no"]
    tray_count = int(job.get("tray_count", 1))
    if job["place_flg"] == "1":
        # วางของ: เพิ่ม lot เข้า cell
        add_lot_to_position(level, block, lot_no, tray_count)
        action = "placed"
    else:
        # หยิบของ: ลบ lot ออกจาก cell (หรือ update tray_count ถ้าหยิบไม่หมด)
        remove_lot_from_position(level, block, lot_no)
        action = "picked"
    
    # 📝 Log job completion to Gateway
    await log_to_gateway("JOB_COMPLETED", {
        "job_id": job_id,
        "lot_no": lot_no,
        "level": str(level),
        "block": str(block),
        "action": action,
        "method": "API"
    })
    
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
            "action": action
        }
    }))
    return {
        "status": "success",
        "lot_no": lot_no,
        "action": action,
        "location": f"L{level}B{block}"
    }

# เพิ่ม endpoint ใหม่สำหรับรับข้อมูลจาก JavaScript
@router.post("/command/complete", tags=["Jobs"])
async def complete_job_by_data(request_data: dict):
    """Complete job โดยใช้ข้อมูลที่ส่งมาจาก client"""
    job_id = request_data.get("job_id")
    lot_no = request_data.get("lot_no")
    
    print(f"API: Received 'Task Complete' via new endpoint for job {job_id}, lot {lot_no}")
    
    if not job_id:
        return {"status": "error", "message": "job_id is required"}
    
    # เรียกใช้ฟังก์ชันเดิม
    return await complete_job(job_id)

@router.post("/command/{job_id}/error", tags=["Jobs"])
async def error_job(job_id: str, body: ErrorRequest):
    print(f"API: Received 'Error' for job {job_id}")
    job = get_job_by_id(job_id)
    if not job: return {"status": "error", "message": "Job not found"}
        
    job["trn_status"] = "2"
    job["error"] = True
    job["errorLocation"] = body.errorLocation
    
    # 📝 Log job error to Gateway
    await log_to_gateway("JOB_ERROR", {
        "job_id": job_id,
        "lot_no": job["lot_no"],
        "level": job["level"],
        "block": job["block"],
        "error_type": "JOB_ERROR",
        "error_message": f"Error at {body.errorLocation}"
    })
    
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
