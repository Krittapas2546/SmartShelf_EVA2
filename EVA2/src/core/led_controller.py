# core/led_controller.py

from core.database import get_shelf_config

# ---------- Hardware LED Mapping (ตามข้อกำหนด hardware จริง) ----------
def _total_pixels(cfg: dict) -> int:
    """คำนวณจำนวน LED ทั้งหมดจาก shelf configuration"""
    return sum(int(v) for v in cfg.values())

def idx(level: int, block: int) -> int:
    """
    แปลง (level, block) -> LED index
    - เริ่มที่ L<top> B1 = 0
    - ซ้าย→ขวาในชั้น, แล้วลงชั้นถัดไป
    - ตัวอย่าง: L4B1=0, L4B2=1, ..., L3B1=6, L3B2=7, ..., L1B6=23
    """
    cfg = get_shelf_config()
    # ตรวจสอบตำแหน่งมีจริง
    if level not in cfg or not (1 <= block <= int(cfg[level])):
        return -1

    # ลำดับชั้นจากบนลงล่าง: 4,3,2,1, ...
    order = sorted(cfg.keys(), reverse=True)

    # offset = รวมจำนวนบล็อกจากทุกชั้นที่อยู่ "เหนือ" ชั้นเป้าหมาย
    offset = 0
    for lv in order:
        if lv == level:
            break
        offset += int(cfg[lv])

    # index ภายในชั้น = block เริ่มที่ 1
    return offset + (block - 1)

# ---------- State / Hardware ----------
NUM_PIXELS = _total_pixels(get_shelf_config())

# ---------- ซอฟต์บัฟเฟอร์สถานะ ----------
state = [(0, 0, 0)] * max(1, NUM_PIXELS)  # เก็บสีของทุกดวง (r,g,b)

try:
    import pi5neo, time
    neo = pi5neo.Pi5Neo('/dev/spidev0.0', NUM_PIXELS, 800)
    
    def show_state():
        """เรนเดอร์ทั้งเส้นจากบัฟเฟอร์ในครั้งเดียว"""
        for i, (r, g, b) in enumerate(state):
            neo.set_led_color(i, r, g, b)
        neo.update_strip()

    def set_pixels(pairs):
        """
        เพิ่ม/เปลี่ยนสีบางดวงโดย 'ไม่ล้างของเดิม'
        pairs: [(level, block, (r,g,b)), ...] หรือ [(index, (r,g,b)), ...]
        """
        for item in pairs:
            if len(item) == 3 and isinstance(item[0], int) and isinstance(item[1], int):
                # รูปแบบ (level, block, (r,g,b))
                level, block, (r, g, b) = item
                i = idx(level, block)
            else:
                # รูปแบบ (index, (r,g,b))
                i, (r, g, b) = item
            
            if 0 <= i < NUM_PIXELS:
                state[i] = (int(r), int(g), int(b))
        show_state()

    def turn_off_some(indices):
        """ดับเฉพาะบางดวง โดยคงดวงอื่นไว้ตามบัฟเฟอร์"""
        for i in indices:
            if isinstance(i, tuple) and len(i) == 2:
                # รูปแบบ (level, block)
                level, block = i
                i = idx(level, block)
            
            if 0 <= i < NUM_PIXELS:
                state[i] = (0, 0, 0)
        show_state()

    def hard_clear(pause=0.02, repeat=2):
        """ล้างทั้งเส้นแบบชัวร์ แล้วซิงค์บัฟเฟอร์ให้เป็นศูนย์"""
        global state
        for _ in range(repeat):
            neo.fill_strip(0, 0, 0)
            neo.update_strip()
            time.sleep(pause)
        state = [(0, 0, 0)] * NUM_PIXELS  # ซิงค์บัฟเฟอร์ให้ตรงกับฮาร์ดแวร์

    def refresh_led_config():
        """รีเฟรชการตั้งค่า LED เมื่อมีการเปลี่ยนแปลง config"""
        global neo, NUM_PIXELS, state
        cfg = get_shelf_config()
        new_pixels = _total_pixels(cfg)
        if new_pixels != NUM_PIXELS:
            NUM_PIXELS = new_pixels
            state = [(0, 0, 0)] * max(1, NUM_PIXELS)
            neo = pi5neo.Pi5Neo('/dev/spidev0.0', NUM_PIXELS, 800)
        hard_clear()
        print(f"💡 LED reinit: {NUM_PIXELS} pixels")

except ImportError:
    # -------- MOCK fallback (ไม่มีฮาร์ดแวร์) --------
    def show_state():
        """MOCK: แสดงสถานะ buffer"""
        active_pixels = [(i, rgb) for i, rgb in enumerate(state) if rgb != (0, 0, 0)]
        if active_pixels:
            print(f"[MOCK] Active pixels: {active_pixels}")
        else:
            print(f"[MOCK] All pixels OFF")

    def set_pixels(pairs):
        """MOCK: เซ็ตบางดวง"""
        for item in pairs:
            if len(item) == 3 and isinstance(item[0], int) and isinstance(item[1], int):
                level, block, (r, g, b) = item
                i = idx(level, block)
            else:
                i, (r, g, b) = item
            
            if 0 <= i < len(state):
                state[i] = (int(r), int(g), int(b))
                print(f"[MOCK] set pixel {i} -> ({r},{g},{b})")
        show_state()

    def turn_off_some(indices):
        """MOCK: ดับบางดวง"""
        for i in indices:
            if isinstance(i, tuple) and len(i) == 2:
                level, block = i
                i = idx(level, block)
            
            if 0 <= i < len(state):
                state[i] = (0, 0, 0)
                print(f"[MOCK] turn off pixel {i}")
        show_state()

    def hard_clear(pause=0.02, repeat=2):
        """MOCK: ล้างทั้งหมด"""
        global state
        state = [(0, 0, 0)] * len(state)
        print(f"[MOCK] hard_clear: {len(state)} pixels")

    def refresh_led_config():
        """MOCK: รีเฟรชการตั้งค่า"""
        global NUM_PIXELS, state
        NUM_PIXELS = _total_pixels(get_shelf_config())
        state = [(0, 0, 0)] * max(1, NUM_PIXELS)
        print(f"[MOCK] LED reinit: {NUM_PIXELS} pixels")

# ---------- High-level LED Control Functions ----------
def set_target_blue(level, block):
    """แสดงช่องเป้าหมายเป็นสีน้ำเงิน"""
    hard_clear()
    set_pixels([(level, block, (0, 0, 255))])
    return {"ok": True, "action": "target_blue", "level": level, "block": block}

def set_target_green(level, block):
    """เปลี่ยนช่องเป้าหมายเป็นสีเขียว (สำเร็จ)"""
    set_pixels([(level, block, (0, 255, 0))])
    return {"ok": True, "action": "target_green", "level": level, "block": block}

def add_error_red(level, block):
    """เพิ่มช่องผิดเป็นสีแดง (ไม่ล้างของเดิม)"""
    set_pixels([(level, block, (255, 0, 0))])
    return {"ok": True, "action": "error_red", "level": level, "block": block}

def clear_all_leds():
    """ล้างไฟทั้งหมด"""
    hard_clear()
    return {"ok": True, "pixels_cleared": NUM_PIXELS}

# ---------- API Compatibility Functions ----------
def set_led_batch(leds):
    """
    API compatibility function สำหรับ batch LED commands
    leds: [{"level": 1, "block": 2, "r": 255, "g": 0, "b": 0}, ...]
    """
    if not leds:
        return {"ok": True, "count": 0, "total_requested": 0}
    
    # แปลงเป็นรูปแบบที่ set_pixels ใช้
    pairs = []
    errors = []
    
    for led in leds:
        try:
            level = int(led.get('level', 0))
            block = int(led.get('block', 0))
            r = int(led.get('r', 0))
            g = int(led.get('g', 0))
            b = int(led.get('b', 0))
            
            # ตรวจสอบว่าตำแหน่งถูกต้อง
            i = idx(level, block)
            if i >= 0:
                pairs.append((level, block, (r, g, b)))
            else:
                errors.append(f"L{level}B{block}: invalid position")
        except (ValueError, TypeError) as e:
            errors.append(f"Invalid LED data: {led}")
    
    # ล้างก่อนแล้วเซ็ตใหม่
    hard_clear()
    if pairs:
        set_pixels(pairs)
    
    result = {
        "ok": True,
        "count": len(pairs),
        "total_requested": len(leds)
    }
    if errors:
        result["errors"] = errors
    
    return result

def set_led(level, block, r, g, b):
    """
    API compatibility function สำหรับ single LED command
    """
    i = idx(level, block)
    if i < 0 or i >= NUM_PIXELS:
        return {"ok": False, "error": f"Invalid L{level}B{block}"}
    
    set_pixels([(level, block, (r, g, b))])
    return {"ok": True, "index": i}

# ---------- Debug Functions ----------
def debug_mapping():
    """Debug function สำหรับตรวจสอบ LED mapping แบบ sequential python -c "from core.led_controller import debug_mapping; debug_mapping()" """
    cfg = get_shelf_config()
    total = _total_pixels(cfg)
    
    print(f"📍 LED Sequential Mapping Debug")
    print(f"Shelf Config: {cfg}")
    print(f"Total Pixels: {total}")
    print(f"Wire Pattern: Top-Left (L4B1=0) → Left-to-Right per level → Jump to next level left")
    print(f"{'Level':<6} {'Block':<6} {'Index':<6} {'Position':<12}")
    print("-" * 40)
    
    # แสดงตามลำดับชั้นจากบนลงล่าง
    for level in sorted(cfg.keys(), reverse=True):
        for block in range(1, int(cfg[level]) + 1):
            index = idx(level, block)
            position = f"L{level}B{block}"
            print(f"{level:<6} {block:<6} {index:<6} {position:<12}")
    
    return {"config": cfg, "total_pixels": total}

def validate_expected_mapping():
    """ตรวจสอบ mapping ตามที่คาดหวัง - ตรงกับการเดินสายจริง"""
    # ตัวอย่างตรวจที่สอดคล้องลวดจริง (4×6)
    expected = {
        (4,1): 0,   # ชั้น 4 เริ่มต้น
        (4,6): 5,   # ชั้น 4 จบ
        (3,1): 6,   # ชั้น 3 เริ่มต้น
        (3,6): 11,  # ชั้น 3 จบ
        (2,1): 12,  # ชั้น 2 เริ่มต้น
        (2,6): 17,  # ชั้น 2 จบ
        (1,1): 18,  # ชั้น 1 เริ่มต้น
        (1,6): 23,  # ชั้น 1 จบ
    }
    
    print("🔍 Validating Expected Mapping:")
    all_correct = True
    
    for (level, block), expected_idx in expected.items():
        actual_idx = idx(level, block)
        status = "✅" if actual_idx == expected_idx else "❌"
        print(f"{status} L{level}B{block} -> {actual_idx} (expected {expected_idx})")
        if actual_idx != expected_idx:
            all_correct = False
    
    return all_correct

# ---------- Helper Functions ----------
def get_led_range_for_level(level: int) -> tuple:
    """
    ส่งกลับ (start_index, end_index) สำหรับชั้นที่ระบุ
    ใช้สำหรับการควบคุม LED ทั้งชั้น
    """
    cfg = get_shelf_config()
    if level not in cfg:
        return (-1, -1)
    
    start_idx = idx(level, 1)  # Block แรกของชั้น
    end_idx = idx(level, int(cfg[level]))  # Block สุดท้ายของชั้น
    
    return (start_idx, end_idx)

def create_level_led_batch(level: int, r: int, g: int, b: int) -> list:
    """
    สร้าง LED batch command สำหรับจุดไฟทั้งชั้น
    """
    cfg = get_shelf_config()
    if level not in cfg:
        return []
    
    batch = []
    for block in range(1, int(cfg[level]) + 1):
        batch.append({
            'level': level,
            'block': block, 
            'r': r,
            'g': g,
            'b': b
        })
    
    return batch

def light_entire_level(level: int, r: int, g: int, b: int):
    """จุดไฟทั้งชั้นด้วยสีที่กำหนด"""
    cfg = get_shelf_config()
    if level not in cfg:
        return {"ok": False, "error": f"Invalid level {level}"}
    
    pairs = []
    for block in range(1, int(cfg[level]) + 1):
        pairs.append((level, block, (r, g, b)))
    
    set_pixels(pairs)
    return {"ok": True, "level": level, "blocks_lit": len(pairs)}

def get_current_state():
    """ส่งคืนสถานะปัจจุบันของ LED buffer"""
    active_leds = []
    for i, (r, g, b) in enumerate(state):
        if (r, g, b) != (0, 0, 0):
            # แปลง index กลับเป็น level, block
            cfg = get_shelf_config()
            for level in sorted(cfg.keys(), reverse=True):
                level_start = idx(level, 1)
                level_end = idx(level, int(cfg[level]))
                if level_start <= i <= level_end:
                    block = (i - level_start) + 1
                    active_leds.append({
                        "index": i,
                        "level": level,
                        "block": block,
                        "color": {"r": r, "g": g, "b": b}
                    })
                    break
    
    return {
        "total_pixels": NUM_PIXELS,
        "active_count": len(active_leds),
        "active_leds": active_leds
    }
