from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json

from core.database import DB, get_job_by_id # <-- เพิ่ม import

# --- Connection Manager for WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
router = APIRouter() # <-- สร้าง router สำหรับไฟล์นี้

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    initial_state = {"type": "initial_state", "payload": DB}
    await websocket.send_text(json.dumps(initial_state))
    try:
        while True:
            data = await websocket.receive_text()
            print(f"🔧 Raw WebSocket data received: {data}")
            try:
                message = json.loads(data)
                message_type = message.get("type")
                payload = message.get("payload", {})
                
                print(f"📩 WebSocket received: {message_type} with payload: {payload}")
                
                if message_type == "complete_job":
                    # จัดการคำสั่ง complete job
                    job_id = payload.get("jobId")
                    lot_no = payload.get("lot_no")
                    client_uuid = payload.get("uuid")
                    
                    print(f"🚀 Processing complete job: {job_id} for lot {lot_no}")
                    print(f"🔍 Client UUID: {client_uuid}")
                    
                    job = get_job_by_id(job_id)
                    print(f"🔍 Found job in database: {job}")
                    
                    if not job:
                        print(f"❌ Job {job_id} not found in database")
                        error_response = {
                            "type": "job_error", 
                            "payload": {
                                "error": "JOB_NOT_FOUND",
                                "message": f"Job {job_id} not found",
                                "jobId": job_id
                            }
                        }
                        await websocket.send_text(json.dumps(error_response))
                        continue
                        
                    # ตรวจสอบว่า job ยังอยู่ใน queue หรือไม่
                    if job_id not in [j.get("jobId") for j in DB["jobs"]]:
                        print(f"⚠️ Job {job_id} has already been completed or removed from queue")
                        warning_response = {
                            "type": "job_warning",
                            "payload": {
                                "warning": "JOB_ALREADY_COMPLETED",
                                "message": f"Job {job_id} ({lot_no}) has already been completed",
                                "jobId": job_id,
                                "lot_no": lot_no
                            }
                        }
                        await websocket.send_text(json.dumps(warning_response))
                        continue
                    
                    has_item = 1 if job["place_flg"] == "1" else 0
                    lot_no_to_store = job["lot_no"] if has_item == 1 else None
                    
                    print(f"📦 Updating shelf state: Level {job['level']}, Block {job['block']}, Item: {has_item}, Lot: {lot_no_to_store}")
                    
                    # อัปเดต shelf_state
                    # update_shelf_state ถูกลบออกในระบบใหม่ (ใช้ helper function อื่นแทน)
                    
                    # ลบงานออกจากคิว
                    print(f"🗑️ Removing job {job_id} from queue")
                    jobs_before = len(DB["jobs"])
                    DB["jobs"] = [j for j in DB["jobs"] if j.get("jobId") != job_id]
                    jobs_after = len(DB["jobs"])
                    print(f"📋 Jobs count: {jobs_before} -> {jobs_after}")
                    
                    # ส่งข้อมูลกลับไปยัง clients ทั้งหมด
                    response = {
                        "type": "job_completed",
                        "payload": {
                            "completedJobId": job_id,
                            "shelf_state": DB["shelf_state"],
                            "lot_no": job["lot_no"],
                            "action": "placed" if job["place_flg"] == "1" else "picked",
                            "uuid": client_uuid
                        }
                    }
                    print(f"📤 Broadcasting job_completed message: {response}")
                    await manager.broadcast(json.dumps(response))
                    print(f"✅ Job {job_id} completed successfully")
                        
                elif message_type == "job_error":
                    # จัดการรายงานข้อผิดพลาด
                    job_id = payload.get("jobId")
                    error_type = payload.get("errorType")
                    error_message = payload.get("errorMessage")
                    
                    print(f"🚨 Processing job error: {job_id} - {error_type}")
                    
                    job = get_job_by_id(job_id)
                    if job:
                        job["error"] = True
                        job["errorType"] = error_type
                        job["errorMessage"] = error_message
                        
                        response = {
                            "type": "job_error",
                            "payload": job
                        }
                        await manager.broadcast(json.dumps(response))
                        print(f"🚨 Job error broadcasted for {job_id}")
                        
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON received via WebSocket: {e}")
                print(f"❌ Raw data was: {data}")
            except Exception as e:
                print(f"💥 Unexpected error processing WebSocket message: {e}")
                print(f"💥 Message type: {message_type}")
                print(f"💥 Payload: {payload}")
                import traceback
                traceback.print_exc()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)