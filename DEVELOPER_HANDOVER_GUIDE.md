# 👨‍💻 Developer Handover Guide - Smart Shelf System

> **📋 คู่มือสำหรับนักพัฒนาที่เข้ามาทำงานต่อ**  
> **Updated:** October 2025 | **Version:** 3.0.0

---

## 🎯 Overview - ภาพรวมระบบ

### 🏗️ **System Architecture**
Smart Shelf เป็นระบบ **IoT-based Inventory Management** ที่ประกอบด้วย:

- **🥧 Raspberry Pi** - Hardware controller + Web server
- **💡 LED Strip** - Position guidance system  
- **📡 Gateway Integration** - External LMS connectivity
- **🌐 Web UI** - Real-time user interface
- **📊 Database** - Job queue & shelf state management

### 🔄 **Core Data Flow**
```
LMS → Gateway → Smart Shelf → LED Display → User Interaction → Gateway → LMS
```

---

## 📁 Project Structure Deep Dive

```
EVA2/src/
├── main.py                 # 🚀 FastAPI application entry point
├── api/
│   ├── jobs.py            # 📋 Main API endpoints & business logic  
│   └── websockets.py      # 📡 Real-time WebSocket communication
├── core/
│   ├── database.py        # 💾 Data models & shelf state management
│   ├── led_controller.py  # 💡 LED hardware control & mapping
│   ├── models.py          # 📊 Pydantic data models
│   └── pushbutton*.py     # 🔘 Hardware button integration
├── static/
│   ├── css/ui_styles.css  # 🎨 UI styling
│   └── js/ui_logic.js     # ⚡ Frontend JavaScript logic
└── templates/
    ├── shelf_ui.html      # 📱 Main user interface
    └── test_api.html      # 🧪 API testing interface
```

---

## 🔧 Core Components Analysis

### 1. 🚀 **main.py** - Application Bootstrap
```python
# Key responsibilities:
- FastAPI app initialization
- Startup sequence management  
- Static file serving
- Router registration
```

**Critical Functions:**
- `initialize_shelf_info()` - ดึงข้อมูลชั้นจาก Gateway
- `initialize_shelf_layout()` - โหลด layout configuration
- `initialize_shelf_state()` - กู้คืน shelf state
- `startup_event()` - ลำดับการเริ่มต้นระบบ

**🔥 Important:** ระบบมี **automatic initialization sequence** เมื่อเริ่มต้น

---

### 2. 📋 **api/jobs.py** - Main Business Logic (2278 lines!)

#### **🎯 Key API Groups:**

##### **A. Job Management**
```python
@router.post("/command")          # สร้างงานใหม่
@router.get("/command")           # ดึงงานทั้งหมด
@router.post("/command/{id}/complete")  # ทำเครื่องหมายเสร็จ
@router.post("/command/{id}/error")     # รายงานข้อผิดพลาด
```

##### **B. LED Control**
```python
@router.post("/api/led")          # ควบคุม LED หลายตัว
@router.post("/api/led/clear")    # ดับ LED ทั้งหมด  
@router.post("/api/led/control")  # ควบคุม LED เดี่ยว
```

##### **C. Shelf Management**
```python
@router.get("/api/shelf/config")  # ข้อมูล configuration
@router.get("/api/shelf/state")   # สถานะชั้นปัจจุบัน
@router.post("/api/shelf/layout") # อัปเดต layout
```

##### **D. Gateway Integration**
```python
@router.get("/api/shelf/pending")     # ดึงงานจาก Gateway
@router.post("/api/shelf/askCorrectShelf")  # ตรวจสอบ LOT
```

#### **🔥 Critical Configuration:**
```python
GATEWAY_BASE_URL = "http://43.72.20.238:8000"  # Gateway server
GLOBAL_SHELF_INFO = {"shelf_id": None, "local_ip": None}
```

---

### 3. 💡 **core/led_controller.py** - Hardware Control

#### **🎯 LED Mapping Algorithm:**
```python
def idx(level: int, block: int) -> int:
    """
    Sequential mapping: L4B1=0, L4B2=1, ..., L1B6=23
    - เริ่มจาก top-left (L4B1 = index 0)  
    - ซ้าย→ขวา per level
    - กระโดดลงชั้นถัดไป
    """
```

#### **🔧 Hardware Support:**
- **Real Hardware:** `pi5neo` library สำหรับ WS2812B LED strip
- **Mock Mode:** จำลองการทำงานเมื่อไม่มี hardware

#### **⚡ Key Functions:**
```python
set_led(level, block, r, g, b)     # LED เดี่ยว
set_led_batch(leds)                # LED หลายตัว  
clear_all_leds()                   # ดับทั้งหมด
refresh_led_config()               # อัปเดต configuration
```

---

### 4. 💾 **core/database.py** - Data Management

#### **🗄️ Data Structures:**
```python
SHELF_CONFIG = {1: 6, 2: 6, 3: 6, 4: 6}  # Level → Blocks
CELL_CAPACITIES = {"1-1": 24, ...}        # Position → Capacity  
DB = {"shelf_state": [...]}                # In-memory database
```

#### **📊 Core Functions:**
```python
get_shelf_config()                 # ดึง configuration
validate_position(level, block)   # ตรวจสอบตำแหน่ง
add_lot_to_position(...)          # เพิ่ม LOT ในตำแหน่ง
get_lots_in_position(...)         # ดู LOT ในตำแหน่ง
```

---

### 5. 📡 **api/websockets.py** - Real-time Communication

#### **🔄 WebSocket Events:**
```javascript
{
  "job_assigned": {...},      // งานใหม่
  "job_completed": {...},     // งานเสร็จ  
  "led_control": {...},       // ควบคุม LED
  "shelf_state_change": {...}, // เปลี่ยนแปลงสถานะ
  "system_alert": {...}       // แจ้งเตือนระบบ
}
```

---

## 🎮 Frontend Architecture

### 📱 **templates/shelf_ui.html** - Main UI
- **Vue.js 3** reactive framework
- **WebSocket** integration สำหรับ real-time updates  
- **Responsive design** รองรับ mobile/desktop

### ⚡ **static/js/ui_logic.js** - Frontend Logic (~3600 lines!)

#### **🔧 Key Components:**
```javascript
// Job Management
renderShelfGrid()           // แสดง shelf grid
renderActiveJob()           // หน้าจอทำงาน
renderQueueSelectionView()  // เลือกงานจาก queue

// Real-time Updates  
setupWebSocket()            // WebSocket connection
controlLEDByQueue()         // ควบคุม LED ตาม queue

// User Interaction
handleLotSearch()           // ค้นหา LOT
handleBarcodeScanned()      // สแกนบาร์โค้ด
```

#### **📊 State Management:**
```javascript
const shelfState = {
  jobs: [],              // งานทั้งหมด
  activeJob: null,       // งานที่กำลังทำ
  queue: [],             // คิวงาน
  ledStatus: {},         // สถานะ LED
  systemStatus: 'online' // สถานะระบบ
};
```

---

## 🛠️ Development Workflow

### 🚀 **Getting Started**

#### **1. Environment Setup**
```bash
# Install dependencies
pip install -r requirements.txt

# Configure settings (ถ้าจำเป็น)
cp config.example.json config.json

# Start development server
python main.py
```

#### **2. Access Points**
- **Main UI:** `http://localhost:8000`
- **API Docs:** `http://localhost:8000/docs`  
- **Simulator:** `http://localhost:8000/simulator`

### 🔄 **Development Flow**

#### **A. Adding New API Endpoint**
1. **Define Model** in `core/models.py`
2. **Add Endpoint** in `api/jobs.py`
3. **Update Frontend** in `static/js/ui_logic.js`
4. **Test** via `/docs` or `/simulator`

#### **B. LED Control Modifications**
1. **Hardware Logic** in `core/led_controller.py`
2. **API Integration** in `api/jobs.py`
3. **Frontend Control** in UI JavaScript

#### **C. Database Schema Changes**
1. **Update Models** in `core/database.py`
2. **Migration Logic** (ถ้าจำเป็น)
3. **API Adjustments** in `api/jobs.py`

---

## 🔥 Critical Information

### ⚠️ **Known Issues & Limitations**

#### **1. Hardware Dependencies**
```python
# LED Control
try:
    import pi5neo  # ต้องมี hardware
    # Real LED control
except ImportError:
    # Mock mode สำหรับ development
```

#### **2. Gateway Connection**
- **URL:** `http://43.72.20.238:8000` (hardcoded)
- **Fallback:** ใช้ local config เมื่อ Gateway ไม่พร้อม
- **Retry Logic:** มี automatic retry mechanism

#### **3. Configuration Priority**
```
1. Gateway Layout (Primary)
2. Local Config (Fallback)  
3. Hardcoded FALLBACK_SHELF_CONFIG (Last resort)
```

### 🛡️ **Error Handling Strategy**

#### **Network Errors:**
```python
# Retry with exponential backoff
async def retry_connection(max_attempts=3, delay=1.0):
    for attempt in range(max_attempts):
        try:
            return await establish_connection()
        except ConnectionError:
            await asyncio.sleep(delay * (2 ** attempt))
```

#### **Hardware Errors:**
```python
# Graceful degradation to mock mode
def set_led_with_fallback(level, block, color):
    try:
        return hardware_set_led(level, block, color)
    except HardwareError:
        return mock_led_response(level, block, color)
```

---

## 🔧 Key Integration Points

### 🌐 **Gateway APIs**
```python
# Job Management
POST /command          # Create job
GET /shelf/pending     # Get pending jobs

# Configuration  
POST /shelf/layout     # Update layout
GET /shelf/info        # Get shelf info

# Reporting
POST /shelf/complete   # Job completion
POST /shelf/error      # Error reporting
```

### 📡 **WebSocket Protocol**
```javascript
// Connection
ws = new WebSocket('ws://localhost:8000/ws')

// Message Format
{
  "type": "event_type",
  "payload": { ... },
  "timestamp": "2025-01-01T10:30:00Z"
}
```

### 💡 **LED Control Protocol**
```python
# Single LED
{
  "level": 1, "block": 2,
  "r": 255, "g": 0, "b": 0
}

# Batch Control
{
  "positions": [
    {"position": "L1B1", "r": 255, "g": 0, "b": 0},
    {"position": "L2B3", "r": 0, "g": 255, "b": 0}
  ],
  "clear_first": true
}
```

---

## 🧪 Testing Strategy

### 🔍 **API Testing**
```bash
# Available test files:
test_led_api.py         # LED API testing
test_led_controller.py  # LED controller unit tests  
test_LED.py            # Hardware LED testing
test_neo.py            # pi5neo library testing
```

### 🎮 **Manual Testing**
- **Simulator:** `/simulator` - ทดสอบ UI และ workflow
- **API Docs:** `/docs` - ทดสอบ API endpoints
- **Test Interface:** `/test_api.html` - UI สำหรับทดสอบ

### 🔄 **Integration Testing**
1. **Mock Mode:** ทดสอบโดยไม่ต้องมี hardware
2. **Gateway Simulation:** ใช้ local fallback config
3. **End-to-End:** ทดสอบ complete workflow

---

## 📊 Performance Considerations

### ⚡ **Response Time Targets**
- **API Calls:** < 200ms
- **LED Control:** < 100ms  
- **WebSocket Messages:** < 50ms
- **Database Operations:** < 50ms

### 🔄 **Optimization Areas**
```python
# Batch LED Operations
set_led_batch(leds)  # แทนการ loop set_led()

# Connection Pooling  
async with httpx.AsyncClient() as client:
    # Reuse connection

# Caching
@lru_cache(maxsize=128)
def get_shelf_config():
    # Cache configuration data
```

---

## 🔮 Future Development Roadmap

### Phase 1: **Immediate Improvements**
- [ ] **Database Migration** to PostgreSQL/SQLite
- [ ] **Enhanced Error Handling** with detailed logging
- [ ] **API Rate Limiting** และ authentication
- [ ] **Unit Test Coverage** เพิ่มเติม

### Phase 2: **Feature Extensions**  
- [ ] **Multi-shelf Management** support
- [ ] **Advanced Analytics** dashboard
- [ ] **Mobile App** integration
- [ ] **Voice Command** support

### Phase 3: **Enterprise Features**
- [ ] **Machine Learning** optimization
- [ ] **Predictive Maintenance** alerts
- [ ] **Global Dashboard** management
- [ ] **Kubernetes** deployment ready

---

## 🆘 Troubleshooting Guide

### 🔥 **Common Issues**

#### **1. LED Not Working**
```bash
# Check hardware connection
ls /dev/spi*  # Should show spidev0.0

# Test pi5neo library
python test_neo.py

# Fallback to mock mode
# System automatically detects and switches
```

#### **2. Gateway Connection Failed**
```python
# Check network connectivity
ping 43.72.20.238

# Verify Gateway URL in jobs.py
GATEWAY_BASE_URL = "http://43.72.20.238:8000"

# System uses fallback config automatically
```

#### **3. WebSocket Disconnection**
```javascript
// Client auto-reconnect logic in ui_logic.js
ws.onclose = () => {
    setTimeout(setupWebSocket, 1000); // Retry after 1s
};
```

#### **4. Performance Issues**
```python
# Check system resources
top  # CPU/Memory usage

# Monitor API response times
# Use /docs interface for testing

# Check LED batch size
# Reduce batch size if needed
```

### 🔧 **Debug Tools**

#### **Development Mode:**
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use debug functions  
from core.led_controller import debug_mapping, validate_expected_mapping
debug_mapping()        # Show current LED mapping
validate_expected_mapping()  # Verify mapping correctness
```

#### **Monitoring:**
```bash
# Check logs
tail -f /var/log/smart_shelf.log

# System health endpoint
curl http://localhost:8000/health

# Real-time WebSocket monitoring
# Use browser developer tools → Network → WS
```

---

## 📋 Code Standards & Conventions

### 🎯 **File Naming**
- **Snake_case** for Python files
- **kebab-case** for HTML/CSS files  
- **camelCase** for JavaScript functions
- **UPPER_CASE** for constants

### 📝 **Documentation Standards**
```python
def function_name(param1: type, param2: type) -> return_type:
    """
    Brief description of function purpose
    
    Args:
        param1: Description of parameter
        param2: Description of parameter
        
    Returns:
        Description of return value
        
    Example:
        result = function_name("test", 123)
    """
```

### 🔄 **API Response Format**
```json
{
  "ok": true,
  "data": { ... },
  "message": "Success description",
  "timestamp": "2025-01-01T10:30:00Z",
  "request_id": "req-123456"
}
```

---

## 🎓 Learning Resources

### 📚 **Documentation**
- **FastAPI:** https://fastapi.tiangolo.com/
- **Vue.js 3:** https://vuejs.org/guide/
- **WebSocket API:** https://developer.mozilla.org/en-US/docs/Web/API/WebSocket

### 🛠️ **Hardware References**  
- **Raspberry Pi:** https://www.raspberrypi.org/documentation/
- **WS2812B LEDs:** NeoPixel documentation
- **SPI Interface:** `/dev/spidev0.0` configuration

### 🔧 **Development Tools**
- **API Testing:** Postman, HTTPie, FastAPI `/docs`
- **WebSocket Testing:** Browser Developer Tools
- **Hardware Testing:** `test_*.py` files ใน project

---

## 🤝 Contact & Support

### 👨‍💻 **Development Team**
- **Primary Developer:** [Previous team member]
- **System Architecture:** Smart Shelf IoT Team
- **Hardware Integration:** Raspberry Pi Specialists

### 📞 **Getting Help**
- **Code Issues:** Check existing `test_*.py` files
- **API Questions:** Use `/docs` interface  
- **Hardware Problems:** Check hardware connection guides
- **Gateway Integration:** Verify `GATEWAY_BASE_URL` configuration

---

## ⚡ Quick Reference

### 🚀 **Start Development**
```bash
cd EVA2/src
python main.py
# → http://localhost:8000
```

### 🔧 **Key Files to Modify**
- **New APIs:** `api/jobs.py`
- **LED Control:** `core/led_controller.py`  
- **Frontend:** `static/js/ui_logic.js`
- **Configuration:** `core/database.py`

### 📊 **Important URLs**
- **Main UI:** `http://localhost:8000`
- **API Docs:** `http://localhost:8000/docs`
- **WebSocket:** `ws://localhost:8000/ws`
- **Gateway:** `http://43.72.20.238:8000`

---

**🎯 Ready to continue development!** 

> 💡 **Pro Tip:** เริ่มจากการทดสอบระบบผ่าน `/simulator` เพื่อทำความเข้าใจ workflow ก่อนแก้ไขโค้ด

> 🔥 **Important:** ระบบมี **automatic fallback mechanisms** ที่จะทำให้ทำงานได้แม้ Gateway หรือ Hardware ไม่พร้อม - เหมาะสำหรับ development!