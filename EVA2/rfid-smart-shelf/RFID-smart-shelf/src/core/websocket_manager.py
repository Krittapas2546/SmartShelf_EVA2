"""
WebSocket Connection Manager
จัดการการเชื่อมต่อทั้งหมด, การส่งข้อความแบบ Broadcast, และการจัดการ Client
"""
from fastapi import WebSocket
from typing import List
import json

class ConnectionManager:
    """
    คลาสที่ทำหน้าที่เป็นศูนย์กลางในการจัดการ WebSocket connections
    """
    def __init__(self):
        """เริ่มต้นด้วย List ว่างสำหรับเก็บ Client ที่เชื่อมต่ออยู่"""
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        รับการเชื่อมต่อใหม่, ตอบรับ, และเพิ่มเข้าสู่ List
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 New WebSocket connection established. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        ลบการเชื่อมต่อออกจาก List (เมื่อ Client หลุดการเชื่อมต่อ)
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"❌ WebSocket connection closed. Total clients: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        ส่งข้อความหา Client คนใดคนหนึ่งโดยเฉพาะ
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """
        ส่งข้อความเดียวกันไปยัง Client ทุกคนที่เชื่อมต่ออยู่
        """
        # สร้าง List ของ connection ที่จะลบทีหลัง เพื่อไม่ให้แก้ไข List ขณะที่กำลังวน Loop
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # หากส่งไม่สำเร็จ (เช่น Client ปิด Browser ไปแล้ว)
                # ให้เก็บ connection นั้นไว้เพื่อนำไปลบออกจาก List
                disconnected_clients.append(connection)
        
        # ลบ Client ที่หลุดการเชื่อมต่อทั้งหมดออกไป
        for client in disconnected_clients:
            self.disconnect(client)

# --- สร้าง Instance หลักสำหรับใช้งานทั่วทั้งโปรเจกต์ ---
# ไฟล์อื่นจะ import ตัวแปร manager นี้ไปใช้งาน
manager = ConnectionManager()