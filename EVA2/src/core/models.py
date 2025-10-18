from pydantic import BaseModel, Field
from typing import Optional, List

class JobRequest(BaseModel):
    biz: str = Field(..., example="IS")
    shelf_id: str = Field(..., example="DESI-001")
    lot_no: str = Field(..., example="Y531146TL.28")
    level: str = Field(..., example="1")
    block: str = Field(..., example="2")
    place_flg: str = Field(..., example="1")
    trn_status: str = Field(..., example="1")
    tray_count: str = Field(..., example="20")

class ErrorRequest(BaseModel):
    errorLocation: dict = Field(..., example={"level": 1, "block": 2, "message": "Wrong position scanned"})

class LEDPosition(BaseModel):
    position: str = Field(..., example="L1B1")
    r: int = Field(255, ge=0, le=255, example=255)
    g: int = Field(0, ge=0, le=255, example=0)
    b: int = Field(0, ge=0, le=255, example=0)

class LEDPositionRequest(BaseModel):
    position: str = Field(..., example="L1B1")
    r: int = Field(255, ge=0, le=255, example=255)
    g: int = Field(0, ge=0, le=255, example=0)
    b: int = Field(0, ge=0, le=255, example=0)

class LEDPositionsRequest(BaseModel):
    positions: List[LEDPosition] = Field(..., example=[
        {"position": "L1B1", "r": 255, "g": 0, "b": 0},
        {"position": "L1B2", "r": 0, "g": 255, "b": 0},
        {"position": "L2B1", "r": 0, "g": 0, "b": 255}
    ])

class LMSCheckShelfRequest(BaseModel):
    lot_no: str = Field(..., example="ABC123DEF.01", description="LOT number format: 9 alphanumeric + dot + 2 digits")

class LMSCheckShelfResponse(BaseModel):
    status: str = Field(..., example="success")
    correct_shelf_name: str = Field(..., example="SHELF_A01")
    lot_no: str = Field(..., example="ABC123DEF.01")
    message: str = Field(..., example="Found correct shelf")

class LMSCheckShelfErrorResponse(BaseModel):
    status: str = Field(..., example="error")
    message: str = Field(..., example="Lot number not found in LMS")
    code: int = Field(..., example=500)
    data: List = Field(..., example=[])

class LEDClearAndBatch(BaseModel):
    """Model สำหรับควบคุม LED แบบ clear ก่อนแล้วค่อย batch เพื่อป้องกันการกระพริบ"""
    positions: List[LEDPosition] = Field(..., example=[
        {"position": "L1B1", "r": 255, "g": 0, "b": 0},
        {"position": "L1B2", "r": 0, "g": 255, "b": 0},
        {"position": "L2B1", "r": 0, "g": 0, "b": 255}
    ])
    clear_first: bool = Field(True, example=True, description="ล้าง LED ทั้งหมดก่อนจุดใหม่หรือไม่")
    delay_ms: int = Field(50, ge=0, le=1000, example=50, description="ดีเลย์ระหว่าง clear และ batch (มิลลิวินาที)")

class ShelfComplete(BaseModel):
    biz: str = Field(..., example="IS")
    shelf_id: str = Field(..., example="DESI-001")
    lot_no: str = Field(..., example="Y531146TL.28")
    level: str = Field(..., example="1")
    block: str = Field(..., example="2")
    place_flg: str = Field(..., example="1")
    trn_status: str = Field(..., example="1")

class LotData(BaseModel):
    """Model สำหรับข้อมูล lot ในแต่ละช่อง"""
    lot_no: str = Field(..., example="TEST001.01")
    tray_count: int = Field(..., example=5)
    biz: str = Field(..., example="IS")

class BlockState(BaseModel):
    """Model สำหรับสถานะของแต่ละช่อง (block) ในชั้นวาง"""
    level: int = Field(..., example=1)
    block: int = Field(..., example=1) 
    lots: List[LotData] = Field(..., example=[
        {"lot_no": "TEST001.01", "tray_count": 5, "biz": "IS"},
        {"lot_no": "TEST002.02", "tray_count": 3, "biz": "IS"}
    ])

class ShelfState(BaseModel):
    shelf_id: str = Field(..., example="PC2")
    update_flg: str = Field(..., example="0")
    shelf_state: List[BlockState] = Field(..., example=[
        {
            "level": 1,
            "block": 1,
            "lots": [
                {"lot_no": "TEST001.01", "tray_count": 5, "biz": "IS"},
                {"lot_no": "TEST002.02", "tray_count": 3, "biz": "IS"}
            ]
        },
        {
            "level": 4,
            "block": 1,
            "lots": [
                {"lot_no": "TEST001.01", "tray_count": 5, "biz": "IS"},
                {"lot_no": "TEST002.02", "tray_count": 3, "biz": "IS"}
            ]
        }
    ])

class SlotData(BaseModel):
    """Model สำหรับข้อมูลช่องวางในชั้นวาง"""
    capacity: int = Field(..., example=40)
    active: bool = Field(..., example=True)
    level: str = Field(..., example="1")
    block: str = Field(..., example="1") 
    position_name: str = Field(..., example="L1-B1")

class LayoutRequest(BaseModel):
    """Model สำหรับ request layout จาก Gateway"""
    shelf_id: str = Field(...,)
    update_flg: str = Field(..., example="0")
    slots: dict = Field(..., example={})

class LayoutResponse(BaseModel):
    """Model สำหรับ response layout จาก Gateway"""
    status: str = Field(..., example="success")
    shelf_id: str = Field(..., example="PC2")
    layout: dict = Field(..., example={
        "L1-B1": {
            "capacity": 40,
            "active": True,
            "level": "1",
            "block": "1", 
            "position_name": "L1-B1"
        },
        "L1-B2": {
            "capacity": 40,
            "active": True,
            "level": "1",
            "block": "2",
            "position_name": "L1-B2"
        }
    })

class GatewayLEDcommand(BaseModel):
    """Model สำหรับควบคุม LED ผ่าน Gateway"""
    level: str = Field(..., example="1")
    block: str = Field(..., example="2")
    color: Optional[str] = Field(None, example="blue")
    
class APILEDcommand(BaseModel):
    """Multiple LEDs:
    {
        "positions": [
            {"position": "L1B1", "r": 255, "g": 0, "b": 0},
            {"position": "L2B3", "r": 0, "g": 255, "b": 0}
        ],
        "clear_first": true  // optional
    }"""
    mode : Optional[str] = Field("multiple", example="multiple",)
    positions: List[LEDPosition] = Field(..., example=[
        {"position": "L1B1", "r": 255, "g": 0, "b": 0},
        {"position": "L2B3", "r": 0, "g": 255, "b": 0},
        {"position": "L3B1", "r": 0, "g": 0, "b": 255}
    ])
    clear_first: Optional[bool] = Field(False, example=True)