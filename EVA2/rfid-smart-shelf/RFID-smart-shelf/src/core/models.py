from pydantic import BaseModel, Field
from typing import Optional, List

class JobRequest(BaseModel):
    lot_no: str = Field(..., example="Y531103TL.07")
    level: str = Field(..., example="1")
    block: str = Field(..., example="2")
    place_flg: str = Field(..., example="1")
    tray_count: str = Field(..., example="10")

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
    lot_no: str = Field(..., example="Y531103TL.07")
    place_flg: str = Field(..., example="1")

class LMSCheckShelfResponse(BaseModel):
    status: str = Field(..., example="success")
    correct_shelf: str = Field(..., example="AM_BURN_S_0006")
    lot_no: str = Field(..., example="Y531103TL.07")
    message: str = Field(..., example="Found correct shelf for Y531103TL.07")