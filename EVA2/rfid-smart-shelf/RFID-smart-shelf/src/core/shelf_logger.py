"""
Shelf Logger Module
เก็บ logs สำหรับ IoTShelfLog ที่รองรับ:
1. Job State Changes
2. LED Control Events
"""

import asyncpg
import json
import uuid
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Database Configuration (เหมือนใน central_gateway.py)
DATABASE_CONFIG = {
    "host": "43.72.20.238",
    "port": 5432,
    "database": "OLTP_IoTManagement",
    "user": "postgres",
    "password": "1234"
}

async def get_db_connection():
    """สร้าง database connection สำหรับ shelf logger"""
    try:
        return await asyncpg.connect(**DATABASE_CONFIG)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

class ShelfLogger:
    """Logger สำหรับเก็บ shelf events ลง IoTShelfLog"""
    
    def __init__(self, shelf_id: str = "SHELF_001"):
        self.shelf_id = shelf_id
    
    async def log_event(self, 
                       event_type: str,
                       level: Optional[str] = None,
                       block: Optional[str] = None, 
                       lot_no: Optional[str] = None,
                       event_data: Dict[str, Any] = None,
                       status: str = "COMPLETED") -> bool:
        """
        บันทึก shelf event ลง IoTShelfLog
        
        Args:
            event_type: ประเภท event (JOB_CREATED, LED_ON, etc.)
            level: Level ที่เกิดเหตุการณ์
            block: Block ที่เกิดเหตุการณ์
            lot_no: LOT number ที่เกี่ยวข้อง
            event_data: ข้อมูลเพิ่มเติมเป็น JSON
            status: สถานะ (COMPLETED, FAILED, IN_PROGRESS)
        """
        conn = await get_db_connection()
        if not conn:
            print("❌ Cannot connect to database for logging")
            return False
        
        try:
            # สร้าง unique ShelfLogID
            timestamp = int(datetime.now().timestamp())
            log_id = f"SLOG_{timestamp}_{str(uuid.uuid4())[:8]}"
            
            # เตรียมข้อมูล
            event_data_json = json.dumps(event_data) if event_data else None
            
            # Insert ลง database
            await conn.execute("""
                INSERT INTO IoTShelfLog 
                (ShelfLogID, ShelfID, EventType, Level, Block, LotNo, EventData, Status, Create_At)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, 
            log_id, self.shelf_id, event_type, level, block, lot_no, 
            event_data_json, status, datetime.now())
            
            print(f"📝 Shelf Event Logged: {event_type} - L{level}B{block} - {lot_no}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to log shelf event: {e}")
            return False
        finally:
            await conn.close()
    
    # === JOB STATE CHANGE EVENTS ===
    
    async def log_job_created(self, job_id: str, lot_no: str, level: str, block: str, 
                             place_flg: str, tray_count: int, source: str = "API"):
        """Log เมื่อสร้าง job ใหม่"""
        return await self.log_event(
            "JOB_CREATED",
            level=level,
            block=block,
            lot_no=lot_no,
            event_data={
                "jobId": job_id,
                "placeFlg": place_flg,
                "trayCount": tray_count,
                "source": source,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def log_job_completed(self, job_id: str, lot_no: str, level: str, block: str,
                               action: str, method: str = "API", duration: Optional[int] = None):
        """Log เมื่อ job เสร็จสิ้น"""
        event_data = {
            "jobId": job_id,
            "action": action,  # "placed" หรือ "picked"
            "method": method,
            "timestamp": datetime.now().isoformat()
        }
        
        if duration is not None:
            event_data["duration"] = duration
            
        return await self.log_event(
            "JOB_COMPLETED",
            level=level,
            block=block,
            lot_no=lot_no,
            event_data=event_data
        )
    
    async def log_job_error(self, job_id: str, lot_no: str, level: str, block: str,
                           error_type: str, error_message: str):
        """Log เมื่อ job เกิด error"""
        return await self.log_event(
            "JOB_ERROR",
            level=level,
            block=block,
            lot_no=lot_no,
            event_data={
                "jobId": job_id,
                "errorType": error_type,
                "errorMessage": error_message,
                "timestamp": datetime.now().isoformat()
            },
            status="FAILED"
        )
    
    # === LED CONTROL EVENTS ===
    
    async def log_led_on(self, level: str, block: str, color: str = "#00ff00", 
                        reason: str = "job_selected", brightness: int = 100,
                        lot_no: Optional[str] = None):
        """Log เมื่อเปิด LED"""
        return await self.log_event(
            "LED_ON",
            level=level,
            block=block,
            lot_no=lot_no,
            event_data={
                "color": color,
                "reason": reason,
                "brightness": brightness,
                "position": f"L{level}B{block}",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def log_led_off(self, level: Optional[str] = None, block: Optional[str] = None,
                         reason: str = "job_completed", duration: Optional[int] = None):
        """Log เมื่อปิด LED"""
        event_data = {
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        if level and block:
            event_data["position"] = f"L{level}B{block}"
        else:
            event_data["clearedPositions"] = "ALL"
            
        if duration is not None:
            event_data["duration"] = duration
            
        return await self.log_event(
            "LED_OFF",
            level=level,
            block=block,
            event_data=event_data
        )
    
    async def log_led_error(self, level: str, block: str, error_type: str, 
                           retry_count: int = 0):
        """Log เมื่อ LED เกิด error"""
        return await self.log_event(
            "LED_ERROR",
            level=level,
            block=block,
            event_data={
                "errorType": error_type,
                "retryCount": retry_count,
                "position": f"L{level}B{block}",
                "timestamp": datetime.now().isoformat()
            },
            status="FAILED"
        )
    
    # === BATCH LED OPERATIONS ===
    
    async def log_led_batch(self, positions: list, operation: str, reason: str = "batch_operation"):
        """Log เมื่อควบคุม LED แบบ batch"""
        return await self.log_event(
            f"LED_{operation.upper()}",
            event_data={
                "operation": operation,
                "positions": positions,
                "positionCount": len(positions),
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # === QUERY FUNCTIONS ===
    
    async def get_recent_events(self, limit: int = 10, event_type: Optional[str] = None):
        """ดึง events ล่าสุด"""
        conn = await get_db_connection()
        if not conn:
            return []
        
        try:
            if event_type:
                query = """
                    SELECT ShelfLogID, EventType, Level, Block, LotNo, EventData, Status, Create_At
                    FROM IoTShelfLog 
                    WHERE ShelfID = $1 AND EventType = $2
                    ORDER BY Create_At DESC LIMIT $3
                """
                results = await conn.fetch(query, self.shelf_id, event_type, limit)
            else:
                query = """
                    SELECT ShelfLogID, EventType, Level, Block, LotNo, EventData, Status, Create_At
                    FROM IoTShelfLog 
                    WHERE ShelfID = $1
                    ORDER BY Create_At DESC LIMIT $2
                """
                results = await conn.fetch(query, self.shelf_id, limit)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"❌ Failed to query shelf events: {e}")
            return []
        finally:
            await conn.close()
    
    async def get_event_stats(self):
        """ดึงสถิติ events"""
        conn = await get_db_connection()
        if not conn:
            return {}
        
        try:
            query = """
                SELECT EventType, 
                       COUNT(*) as total_count,
                       COUNT(CASE WHEN Status = 'FAILED' THEN 1 END) as failed_count,
                       COUNT(CASE WHEN Status = 'COMPLETED' THEN 1 END) as completed_count
                FROM IoTShelfLog 
                WHERE ShelfID = $1
                GROUP BY EventType
                ORDER BY total_count DESC
            """
            results = await conn.fetch(query, self.shelf_id)
            
            stats = {}
            for row in results:
                stats[row['eventtype']] = {
                    'total': row['total_count'],
                    'failed': row['failed_count'],
                    'completed': row['completed_count']
                }
            
            return stats
            
        except Exception as e:
            print(f"❌ Failed to get event stats: {e}")
            return {}
        finally:
            await conn.close()

# Global instance
shelf_logger = ShelfLogger()
