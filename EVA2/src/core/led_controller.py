# core/led_controller.py

from core.database import get_shelf_config

def get_num_pixels():
    """Get current number of pixels based on dynamic shelf config"""
    shelf_config = get_shelf_config()
    return sum(shelf_config.values())

# NUM_PIXELS จะถูกอัปเดตใน refresh_led_config()
NUM_PIXELS = 24  # Fallback initial value

def idx(level, block):
    """
    แปลง (level, block) เป็น index ของ LED
    level: 1..N (1 คือชั้นล่างสุด)
    
    Returns:
        int: LED index, หรือ -1 ถ้าตำแหน่งไม่ถูกต้อง
    """
    try:
        shelf_config = get_shelf_config()
        print(f"🔍 idx({level}, {block}) - shelf_config: {shelf_config}")
        
        # ตรวจสอบ level ถูกต้อง
        if level not in shelf_config:
            print(f"❌ Invalid level {level}. Available levels: {list(shelf_config.keys())}")
            return -1
            
        # ตรวจสอบ block ถูกต้อง
        if not (1 <= block <= shelf_config[level]):
            print(f"❌ Invalid block {block} for level {level}. Max blocks: {shelf_config[level]}")
            return -1
        
        # คำนวณ LED index โดยเริ่มจากชั้น 1
        # ชั้น 1 = index 0-7, ชั้น 2 = index 8-13, ฯลฯ
        calculated_idx = 0
        
        # รวม blocks จากชั้น 1 ถึงชั้นก่อนหน้าชั้นเป้าหมาย
        for l in range(1, level):
            if l in shelf_config:
                calculated_idx += shelf_config[l]
        
        # เพิ่ม block offset ในชั้นปัจจุบัน (block เริ่มจาก 1)
        calculated_idx += (block - 1)
        
        total_pixels = sum(shelf_config.values())
        
        print(f"🔍 Calculation: level_offset={calculated_idx-(block-1)}, block_offset={block-1}, final_idx={calculated_idx}, total={total_pixels}")
        
        # 🔍 Debug: เฝ้าระวัง L1B1 โดยเฉพาะ
        if level == 1 and block == 1:
            print(f"🚨 CRITICAL: L1B1 maps to LED index {calculated_idx} (should be 0 normally)")
        elif level == 1 and block == 2:
            print(f"🔍 DEBUG: L1B2 maps to LED index {calculated_idx}")
        elif level == 1 and block == 3:
            print(f"🔍 DEBUG: L1B3 maps to LED index {calculated_idx}")
        # ตรวจสอบ bounds
        if calculated_idx < 0 or calculated_idx >= total_pixels:
            print(f"❌ LED index {calculated_idx} out of bounds (0-{total_pixels-1})")
            return -1
            
        print(f"✅ L{level}B{block} -> LED index {calculated_idx}")
        return calculated_idx
        
    except Exception as e:
        print(f"❌ Error calculating LED index for L{level}B{block}: {e}")
        return -1


def init_led_state():
    """Initialize LED state based on current shelf config"""
    return [(0, 0, 0)] * get_num_pixels()

# _led_state จะถูกสร้างใน refresh_led_config()
_led_state = [(0, 0, 0)] * 24  # Fallback initial value

# Lazy initialization - จะ refresh เมื่อเรียกใช้งานจริง
_initialized = False

def ensure_led_initialized():
    """Ensure LED system is initialized with correct configuration"""
    global _initialized
    if not _initialized:
        try:
            refresh_led_config()
            _initialized = True
            print("💡 LED Controller lazy-initialized with correct configuration")
        except Exception as e:
            print(f"⚠️ LED Controller initialization warning: {e}")

def refresh_led_config():
    """Refresh LED configuration when shelf config changes"""
    global _led_state, NUM_PIXELS, neo
    old_pixels = NUM_PIXELS
    NUM_PIXELS = get_num_pixels()
    _led_state = init_led_state()
    
    print(f"💡 LED Config Refreshed: {old_pixels} -> {NUM_PIXELS} pixels")
    print(f"💡 New _led_state size: {len(_led_state)}")
    
    # Reinitialize hardware if available
    if 'pi5neo' in globals():
        try:
            import time
            neo = pi5neo.Pi5Neo('/dev/spidev0.0', NUM_PIXELS, 800)
            # Clear ทันทีหลัง init
            neo.fill_strip(0, 0, 0)
            neo.update_strip()
            time.sleep(0.02)
            print(f"💡 Hardware LED strip reinitialized with {NUM_PIXELS} pixels")
        except Exception as e:
            print(f"⚠️ Hardware LED reinit failed: {e}")

try:
    import pi5neo
    import time
    
    neo = pi5neo.Pi5Neo('/dev/spidev0.0', NUM_PIXELS, 800)

    def set_led(level, block, r, g, b):
        try:
            ensure_led_initialized()
            i = idx(level, block)
            if i == -1:
                return {"ok": False, "error": f"Invalid position L{level}B{block}"}
                
            # 🔍 Debug: ตรวจสอบสีที่ส่งมา
            if g > 0:
                print(f"⚠️ WARNING: Green detected! L{level}B{block} -> RGB({r},{g},{b})")
            
            global _led_state
            current_pixels = get_num_pixels()
            
            # ตรวจสอบและ refresh _led_state ถ้าจำเป็น
            if len(_led_state) != current_pixels:
                print(f"💡 Refreshing LED state: {len(_led_state)} -> {current_pixels} pixels")
                _led_state = [(0, 0, 0)] * current_pixels
            
            _led_state = list(_led_state)
            
            # Double-check bounds
            if i >= len(_led_state):
                return {"ok": False, "error": f"LED index {i} >= array length {len(_led_state)}"}
                
            # อัพเดต state
            _led_state[i] = (r, g, b)
            
            # Set เฉพาะ LED เดียวโดยไม่ clear ทั้งหมด
            neo.set_led_color(i, r, g, b)
            neo.update_strip()
            time.sleep(0.02)
            
            return {"ok": True, "index": i, "position": f"L{level}B{block}"}
            
        except Exception as e:
            return {"ok": False, "error": f"LED control failed: {str(e)}"}

    def set_led_batch(leds):
        try:
            global _led_state
            current_pixels = get_num_pixels()
            
            # ตรวจสอบและ refresh _led_state ถ้าจำเป็น
            if len(_led_state) != current_pixels:
                print(f"💡 Refreshing LED state for batch: {len(_led_state)} -> {current_pixels} pixels")
                _led_state = [(0, 0, 0)] * current_pixels
            
            _led_state = list(_led_state)
            processed = 0
            errors = []
            
            # Clear strip ก่อน
            neo.fill_strip(0, 0, 0)
            neo.update_strip()
            time.sleep(0.02)
            
            for led in leds:
                level = int(led.get('level', 0))
                block = int(led.get('block', 0))
                r = int(led.get('r', 0))
                g = int(led.get('g', 0))
                b = int(led.get('b', 0))
                
                # 🔍 Debug: ตรวจสอบสีที่ส่งมา
                if g > 0:
                    print(f"⚠️ WARNING: Green in batch! L{level}B{block} -> RGB({r},{g},{b})")
                
                i = idx(level, block)
                if i == -1:
                    errors.append(f"L{level}B{block}: Invalid position")
                    continue
                    
                if i >= len(_led_state):
                    errors.append(f"L{level}B{block}: Index {i} out of bounds")
                    continue
                    
                _led_state[i] = (r, g, b)
                neo.set_led_color(i, r, g, b)  # Set แต่ละ LED ทันที
                processed += 1
            
            # Update hardware ครั้งเดียว
            neo.update_strip()
            time.sleep(0.02)
            
            result = {"ok": True, "count": processed, "total_requested": len(leds)}
            if errors:
                result["errors"] = errors
            return result
            
        except Exception as e:
            return {"ok": False, "error": f"LED batch failed: {str(e)}"}

except ImportError:
    def set_led(level, block, r, g, b):
        try:
            ensure_led_initialized()
            i = idx(level, block)
            if i == -1:
                return {"ok": False, "error": f"Invalid position L{level}B{block}", "mock": True}
                
            # 🔍 Debug: ตรวจสอบสีที่ส่งมา
            if g > 0:
                print(f"⚠️ WARNING: Green detected! L{level}B{block} -> RGB({r},{g},{b})")
                
            global _led_state
            current_pixels = get_num_pixels()
            
            # ตรวจสอบและ refresh _led_state ถ้าจำเป็น
            if len(_led_state) != current_pixels:
                print(f"💡 Refreshing LED state: {len(_led_state)} -> {current_pixels} pixels")
                _led_state = [(0, 0, 0)] * current_pixels
            
            _led_state = list(_led_state)
            
            # Double-check bounds
            if i >= len(_led_state):
                return {"ok": False, "error": f"LED index {i} >= array length {len(_led_state)}", "mock": True}
                
            _led_state[i] = (r, g, b)
            position_str = f"L{level}B{block}"
            
            # 🔍 Debug: ตรวจสอบสีที่ส่งมา (Mock)
            if g > 0:
                print(f"⚠️ WARNING: Green detected in mock! L{level}B{block} -> RGB({r},{g},{b})")
            
            print(f"[MOCK] ✅ LED {position_str} -> index {i}, color=({r},{g},{b}), state_size={len(_led_state)}")
            result = {"ok": True, "index": i, "position": position_str, "mock": True}
            return result
            
        except Exception as e:
            return {"ok": False, "error": f"LED control failed: {str(e)}", "mock": True}

    def set_led_batch(leds):
        try:
            global _led_state
            current_pixels = get_num_pixels()
            
            # ตรวจสอบและ refresh _led_state ถ้าจำเป็น
            if len(_led_state) != current_pixels:
                print(f"💡 Refreshing LED state for batch: {len(_led_state)} -> {current_pixels} pixels")
                _led_state = [(0, 0, 0)] * current_pixels
            
            _led_state = list(_led_state)
            processed = 0
            errors = []
            
            for led in leds:
                level = int(led.get('level', 0))
                block = int(led.get('block', 0))
                r = int(led.get('r', 0))
                g = int(led.get('g', 0))
                b = int(led.get('b', 0))
                
                # 🔍 Debug: ตรวจสอบสีที่ส่งมา (Mock)
                if g > 0:
                    print(f"⚠️ WARNING: Green in mock batch! L{level}B{block} -> RGB({r},{g},{b})")
                
                i = idx(level, block)
                if i == -1:
                    errors.append(f"L{level}B{block}: Invalid position")
                    continue
                    
                if i >= len(_led_state):
                    errors.append(f"L{level}B{block}: Index {i} out of bounds")
                    continue
                    
                _led_state[i] = (r, g, b)
                processed += 1
            
            print(f"[MOCK] Would batch set LEDs: {processed}/{len(leds)} successful")
            if errors:
                print(f"[MOCK] Batch errors: {errors}")
            
            result = {"ok": True, "count": processed, "total_requested": len(leds), "mock": True}
            if errors:
                result["errors"] = errors
            return result
            
        except Exception as e:
            return {"ok": False, "error": f"LED batch failed: {str(e)}", "mock": True}

def clear_all_leds():
    """Clear all LEDs and reset state"""
    global _led_state
    current_pixels = get_num_pixels()
    _led_state = [(0, 0, 0)] * current_pixels
    
    if 'neo' in globals() and neo:
        # ใช้คำสั่งที่ work จากโค้ดตัวอย่าง
        neo.fill_strip(0, 0, 0)
        neo.update_strip()
        time.sleep(0.02)  # ให้เวลารีเซ็ต
        print(f"💡 Hardware LEDs cleared ({current_pixels} pixels)")
    else:
        print(f"[MOCK] Would clear all LEDs ({current_pixels} pixels)")
    
    return {"ok": True, "pixels_cleared": current_pixels}
