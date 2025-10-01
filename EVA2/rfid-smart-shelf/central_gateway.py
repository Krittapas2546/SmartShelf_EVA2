from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncpg
import json
from typing import Dict, Optional
import uvicorn
from datetime import datetime

app = FastAPI(
    title="Smart Shelf Central Gateway",
    description="Central Gateway for LMS to Smart Shelf Communication",
    version="1.0.0"
)

# Database Configuration
DATABASE_CONFIG = {
    "host": "43.72.20.238",
    "port": 5432,
    "database": "OLTP_IoTManagement",
    "user": "postgres",  # แก้จาก postgre เป็น postgres
    "password": "1234"
}

# ============ DATABASE HELPER FUNCTIONS ============

async def get_db_connection():
    """สร้าง database connection ใหม่ทุกครั้ง"""
    try:
        return await asyncpg.connect(**DATABASE_CONFIG)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

# ============ REQUEST MODELS ============

class ShelfAskRequest(BaseModel):
    """รูปแบบข้อมูลที่ Smart Shelf ส่งมาถาม Gateway"""
    lot_no: str
    place_flg: str = "1"

class LMSCommandRequest(BaseModel):
    """รูปแบบข้อมูลที่ LMS ส่งมา"""
    shelf_ID: str      # LMS ระบุ shelf ที่ต้องการ
    lot_no: str
    level: str
    block: str
    place_flg: str
    trn_status: str    # LMS ส่งมาเป็น trn_status
    tray_count: str    # LMS ส่งมาเป็น tray_count ด้วย

class ShelfCommandRequest(BaseModel):
    """รูปแบบข้อมูลที่ส่งไปยัง Smart Shelf"""
    lot_no: str
    level: str
    block: str
    place_flg: str
    tray_count: str

# ============ CORE DATABASE FUNCTIONS ============

async def get_shelf_info_by_id(shelf_id: str) -> Optional[Dict]:
    """
    ค้นหาข้อมูล shelf จาก shelf_ID ที่ LMS ส่งมา (Connect per request)
    """
    conn = await get_db_connection()
    if not conn:
        print("❌ Cannot connect to database")
        return None
    
    try:
        # Query จาก IoTShelfMaster table ใหม่
        result = await conn.fetchrow("""
            SELECT ShelfID, ShelfName, Ip, IsActive
            FROM IoTShelfMaster
            WHERE ShelfID = $1 AND IsActive = true
        """, shelf_id)
        
        if result:
            return {
                "shelf_id": result["shelfid"],
                "shelf_name": result["shelfname"],
                "ip": result["ip"],
                "is_active": result["isactive"],
                "port": 8000,           # Default port
                "api_path": "/api/jobs/new"  # Updated API path
            }
        
        return None
        
    except Exception as e:
        print(f"❌ Error getting shelf info: {e}")
        return None
    finally:
        await conn.close()
        print(f"🔌 Database connection closed for shelf lookup: {shelf_id}")

async def log_transaction(
    shelf_id: str,
    lms_request: Dict,
    shelf_response: Dict,
    status: str
):
    """บันทึก transaction log (Connect per request)"""
    conn = await get_db_connection()
    if not conn:
        print(f"📝 Fallback Log (no DB): {status} - LMS → {shelf_id} - LOT: {lms_request.get('lot_no', 'N/A')}")
        return
    
    try:
        # สร้าง Log ID ที่เข้าใจง่าย: LOT_SHELF_วันเวลา
        timestamp = datetime.now().strftime('%m%d_%H%M%S')
        lot_no = lms_request.get("lot_no", "UNKNOWN")[:10]  # เอาแค่ 10 ตัวแรก
        log_id = f"{lot_no}_{shelf_id}_{timestamp}"
        
        # เนื่องจาก system log table ถูกลบออก ให้ใช้ structured logging
        transaction_log = {
            "log_id": log_id,
            "shelf_id": shelf_id,
            "event_type": "LMS_COMMAND_FORWARD",
            "lms_request": lms_request,
            "lot_no": lms_request.get("lot_no", "UNKNOWN"),
            "level": lms_request.get("level"),
            "block": lms_request.get("block"),
            "place_flg": lms_request.get("place_flg"),
            "trn_status": lms_request.get("trn_status"),
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📝 LMS TRANSACTION LOG: {json.dumps(transaction_log, indent=2)}")
        print(f"� Transaction logged: {log_id} for LOT: {lms_request.get('lot_no')}")
        
    except Exception as e:
        print(f"⚠️ Logging failed: {e}")
        print(f"📝 Fallback Log: {shelf_id} | {lms_request.get('lot_no')} | {status}")
    finally:
        await conn.close()
        print(f"🔌 Database connection closed for logging: {log_id}")

# ============ CORE GATEWAY FUNCTIONS ============

async def forward_to_shelf(shelf_info: Dict, lms_data: Dict) -> Dict:
    """
    ส่งคำสั่งจาก LMS ไปยัง Smart Shelf ที่ระบุ
    """
    shelf_url = f"http://{shelf_info['ip']}:{shelf_info['port']}{shelf_info['api_path']}"
    
    # แปลงข้อมูลให้ตรงกับ Smart Shelf API format
    shelf_request = {
        "lot_no": lms_data["lot_no"],
        "level": lms_data["level"],
        "block": lms_data["block"],
        "place_flg": lms_data["place_flg"],
        "tray_count": lms_data["tray_count"]  # ใช้ tray_count ที่ LMS ส่งมาโดยตรง
    }
    
    print(f"🔄 Forwarding LMS command to shelf: {shelf_info['shelf_id']}")
    print(f"📡 Target URL: {shelf_url}")
    print(f"📦 Payload: {shelf_request}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(shelf_url, json=shelf_request)
            
            if response.status_code in [200, 201]:
                shelf_response = response.json()
                
                result = {
                    "status": "success",
                    "message": f"Command successfully forwarded to {shelf_info['shelf_id']}",
                    "shelf_id": shelf_info["shelf_id"],
                    "shelf_ip": shelf_info["ip"],
                    "job_id": shelf_response.get("jobId"),
                    "shelf_response": shelf_response
                }
                
                print(f"✅ Shelf response: {shelf_response}")
                return result
                
            else:
                error_result = {
                    "status": "error",
                    "message": f"Shelf returned HTTP {response.status_code}",
                    "shelf_id": shelf_info["shelf_id"],
                    "details": response.text,
                    "http_status": response.status_code
                }
                
                print(f"❌ Shelf error: {error_result}")
                return error_result
                
    except httpx.TimeoutException:
        error_result = {
            "status": "error",
            "message": f"Timeout connecting to shelf {shelf_info['shelf_id']}",
            "shelf_id": shelf_info["shelf_id"],
            "shelf_url": shelf_url
        }
        print(f"⏱️ Timeout: {error_result}")
        return error_result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "shelf_id": shelf_info["shelf_id"],
            "shelf_url": shelf_url
        }
        print(f"💥 Connection error: {error_result}")
        return error_result

# ============ API ENDPOINTS ============

@app.post("/api/command", tags=["LMS Integration"])
async def receive_lms_command(request: LMSCommandRequest):
    """
    รับคำสั่งจาก LMS และส่งต่อไปยัง Smart Shelf ที่ระบุ
    
    LMS ส่ง shelf_ID มาเพื่อระบุ shelf ที่ต้องการ
    Central Gateway จะหา IP/Port ของ shelf นั้น แล้วส่งคำสั่งต่อไป
    """
    print(f"📨 Received LMS command: {request.model_dump()}")
    
    try:
        # 1. ค้นหาข้อมูล shelf จาก shelf_ID ที่ LMS ส่งมา
        shelf_info = await get_shelf_info_by_id(request.shelf_ID)
        
        if not shelf_info:
            error_msg = f"Shelf ID '{request.shelf_ID}' not found or inactive"
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "shelf_not_found",
                    "message": error_msg,
                    "shelf_id": request.shelf_ID
                }
            )
        
        print(f"✅ Found shelf: {shelf_info}")
        
        # 2. ส่งคำสั่งไปยัง shelf ที่ระบุ
        result = await forward_to_shelf(shelf_info, request.model_dump())
        
        # 3. บันทึก transaction log
        await log_transaction(
            request.shelf_ID,
            request.model_dump(),
            result,
            result["status"]
        )
        
        # 4. ส่ง response กลับ LMS
        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"Command forwarded to shelf {request.shelf_ID}",
                "shelf_id": request.shelf_ID,
                "shelf_ip": shelf_info["ip"],
                "job_id": result.get("job_id"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Shelf error
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "shelf_communication_error",
                    "message": result["message"],
                    "shelf_id": request.shelf_ID,
                    "details": result
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 Gateway error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "gateway_internal_error",
                "message": f"Internal gateway error: {str(e)}",
                "shelf_id": request.shelf_ID
            }
        )

@app.get("/shelves", tags=["Management"])
async def list_all_shelves():
    """แสดงรายการ shelf ทั้งหมดที่ระบบรู้จัก (Connect per request)"""
    conn = await get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection not available")
    
    try:
        results = await conn.fetch("""
            SELECT ShelfID, ShelfName, Ip, IsActive
            FROM IoTShelfMaster
            WHERE IsActive = true
            ORDER BY ShelfID
        """)
        
        shelves_data = {
            "shelves": [
                {
                    "shelf_id": row["shelfid"],
                    "shelf_name": row["shelfname"],
                    "ip": row["ip"],
                    "is_active": row["isactive"],
                    "port": 8000,           # Default port
                    "api_path": "/command"  # Default API path
                }
                for row in results
            ]
        }
        
        return shelves_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing shelves: {str(e)}")
    finally:
        await conn.close()
        print(f"🔌 Database connection closed for shelf listing")

@app.get("/shelves/{shelf_id}", tags=["Management"])
async def get_shelf_info(shelf_id: str):
    """ดูข้อมูล shelf เฉพาะ"""
    shelf_info = await get_shelf_info_by_id(shelf_id)
    
    if not shelf_info:
        raise HTTPException(status_code=404, detail=f"Shelf {shelf_id} not found")
    
    return shelf_info

@app.post("/callback/job-status", tags=["Callbacks"])
async def job_status_callback(
    job_id: str,
    status: str,
    message: str = None
):
    """Callback endpoint สำหรับรับสถานะจาก Smart Shelf (Connect per request)"""
    print(f"📞 Received callback: job_id={job_id}, status={status}")
    
    conn = await get_db_connection()
    if not conn:
        print(f"⚠️ Cannot log callback to database: {job_id}")
        return {
            "status": "callback_received",
            "job_id": job_id,
            "updated_status": status,
            "timestamp": datetime.now().isoformat(),
            "note": "Database logging failed"
        }
    
    try:
        # เนื่องจาก database ถูก simplify ไว้เฉพาะ configuration tables
        # ไม่มี job queue และ system log แล้ว - ใช้ logging แทน
        
        callback_data = {
            "timestamp": datetime.now().isoformat(),
            "job_id": job_id,
            "status": status,
            "message": message,
            "event_type": "JOB_STATUS_CALLBACK"
        }
        
        print(f"📊 JOB CALLBACK LOG: {json.dumps(callback_data, indent=2)}")
        print(f"✅ Job {job_id} status updated to: {status}")
        
        return {
            "status": "callback_received",
            "job_id": job_id,
            "updated_status": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Callback error: {e}")
        raise HTTPException(status_code=500, detail=f"Callback processing error: {str(e)}")
    finally:
        await conn.close()
        print(f"🔌 Database connection closed for callback: {job_id}")

@app.get("/health", tags=["Health Check"])
async def health_check():
    """ตรวจสอบสถานะของ Central Gateway (Connect per request)"""
    conn = await get_db_connection()
    
    if not conn:
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "database": "disconnected",
            "total_shelves": 0,
            "version": "1.0.0"
        }
    
    try:
        shelf_count = await conn.fetchval("""
            SELECT COUNT(*) FROM IoTShelfMaster WHERE IsActive = true
        """)
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "total_shelves": shelf_count,
            "version": "1.0.0"
        }
        
        return health_data
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        await conn.close()
        print(f"🔌 Database connection closed for health check")

@app.get("/", tags=["Info"])
async def root():
    """หน้าแรกของ Central Gateway"""
    return {
        "service": "Smart Shelf Central Gateway",
        "version": "1.0.0",
        "description": "Central gateway for LMS to Smart Shelf communication",
        "endpoints": {
            "main_api": "/api/command",
            "health": "/health",
            "shelves": "/shelves",
            "docs": "/docs"
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 Starting Smart Shelf Central Gateway (Connect-per-Request Mode)...")
    print("📍 LMS API Endpoint: http://localhost:5000/api/command")
    print("📄 API Documentation: http://localhost:5000/docs")
    print("🏥 Health Check: http://localhost:5000/health")
    print("📋 Shelf List: http://localhost:5000/shelves")
    print()
    print("🔧 Configuration:")
    print(f"   Database: {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}")
    print(f"   Database Name: {DATABASE_CONFIG['database']}")
    print("   Connection Mode: Per-Request (Connect → Query → Disconnect)")
    print()
    print("💡 Test Commands:")
    print("   curl http://localhost:5000/health")
    print("   curl http://localhost:5000/shelves")
    print()
    uvicorn.run(app, host="0.0.0.0", port=5000)
