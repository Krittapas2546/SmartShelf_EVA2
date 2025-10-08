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
    tray_count: str = Field(..., example="20")

