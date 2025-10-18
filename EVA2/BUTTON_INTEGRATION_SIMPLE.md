# Push Button Integration - Simplified Version

## 📋 Overview

ระบบปุ่มกดแบบง่าย ไม่ต้องเป็น server แยก รวมเข้ากับ main server โดยตรง

### Components:
- `core/pushbutton_reader.py`: คลาสอ่าน I2C buttons (MCP23008/PCF8574)
- `api/jobs.py`: เพิ่ม endpoints และ integration
- `ui_logic.js`: รับ WebSocket event "button_press" แล้วทำงานเหมือนสแกนตำแหน่ง

## 🔧 Hardware Setup

```
MCP23008 I2C GPIO Expander
├── VCC → 3.3V
├── GND → Ground  
├── SDA → GPIO 2 (I2C SDA)
├── SCL → GPIO 3 (I2C SCL)
├── A0-A2 → GND (Address 0x20)
└── Buttons:
    ├── P0 → Button 0 (L1B1)
    ├── P1 → Button 1 (L1B2)  
    └── P2 → Button 2 (L1B3)
```

Pull-up resistors enabled internally.
Buttons connect to GND when pressed.

## 📦 Dependencies

Add to `requirements.txt`:
```txt
smbus2>=0.4.0
```

## 🚀 Usage

### 1. API Endpoints

#### Get Button Status
```bash
GET /api/button/status
```
Returns current button system status, hardware availability, and position mapping.

#### Start Button Monitoring  
```bash
POST /api/button/start
```

#### Stop Button Monitoring
```bash
POST /api/button/stop
```

#### Simulate Button Press (Testing)
```bash
POST /api/button/simulate/0  # Button 0
POST /api/button/simulate/1  # Button 1  
POST /api/button/simulate/2  # Button 2
```

### 2. Programmatic Usage

```python
from core.pushbutton_reader import PushButtonReader

def on_button_press(button_index, position):
    print(f"Button {button_index} pressed at {position}")

# Create reader
reader = PushButtonReader(callback=on_button_press, debug=True)

# Start monitoring (non-blocking)
reader.start_monitoring()

# Your main code here...

# Stop when done
reader.stop_monitoring()
```

### 3. Integration with Main Server

Button reader พ่วงเข้ากับ main FastAPI server:

```python
# In jobs.py
from core.pushbutton_reader import PushButtonReader

# Initialize when server starts
button_reader = PushButtonReader(callback=button_callback)
button_reader.start_monitoring()

# Button press -> WebSocket event -> UI handles like barcode scan
```

## 🎯 How It Works

1. **Hardware Detection**: ตรวจสอบ I2C hardware อัตโนมัติ
2. **Position Mapping**: แมป button index กับตำแหน่งชั้นวาง (L1B1, L1B2, ...)
3. **Debounce**: กรองสัญญาณรบกวน (50ms debounce time)
4. **WebSocket Integration**: ส่ง event ไป UI เหมือนการสแกน barcode
5. **UI Handling**: ใช้ logic เดียวกับ barcode scan (ตรวจสอบตำแหน่ง, complete job)

## 🧪 Testing

### Without Hardware (Simulation Mode):
```bash
cd /path/to/project
python test_button_reader.py
```

### With Hardware:
1. เริ่ม main server: `python src/main.py`
2. เรียก API: `POST /api/button/start`
3. กดปุ่มที่ฮาร์ดแวร์
4. ดู WebSocket events ใน browser console

### Check Status:
```bash
curl http://localhost:8000/api/button/status
```

## 🔧 Troubleshooting

### I2C Permission Issues:
```bash
sudo usermod -a -G i2c $USER
sudo chmod 666 /dev/i2c-1
```

### Hardware Not Detected:
- ตรวจสอบการเชื่อมต่อ I2C
- ใช้ `i2cdetect -y 1` เพื่อหา device address
- ตรวจสอบ pull-up resistors

### Import Errors:
```bash
pip install smbus2
```

## 🔄 Integration Flow

```
Physical Button Press
↓
I2C GPIO Read (MCP23008)  
↓
Debounce Logic
↓
Position Mapping (Button 0 → L1B1)
↓  
WebSocket Event {"type": "button_press", "payload": {...}}
↓
UI handleButtonPress()
↓
Same Logic as Barcode Scan (validate position, complete job)
```

## ✨ Features

- ✅ Non-blocking monitoring
- ✅ Hardware auto-detection  
- ✅ Simulation mode for testing
- ✅ Dynamic position mapping
- ✅ WebSocket integration
- ✅ Debounce protection
- ✅ Error handling
- ✅ Status monitoring
- ✅ Compatible with existing UI logic

## 📌 Notes

- Maximum 3 buttons (hardware limitation)
- Position mapping อัปเดตได้ dynamically
- ทำงานร่วมกับ LED control และ WebSocket
- ไม่ต้องใช้ aiohttp (ใช้ threading แทน asyncio)
- เริ่ม/หยุดได้ผ่าน API endpoints