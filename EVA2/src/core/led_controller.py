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
_led_state = [(0, 0, 0)] * max(1, NUM_PIXELS)

try:
    import pi5neo, time
    neo = pi5neo.Pi5Neo('/dev/spidev0.0', NUM_PIXELS, 800)

    def refresh_led_config():
        global neo, NUM_PIXELS, _led_state
        cfg = get_shelf_config()
        new_pixels = _total_pixels(cfg)
        if new_pixels != NUM_PIXELS:
            NUM_PIXELS = new_pixels
            _led_state = [(0, 0, 0)] * max(1, NUM_PIXELS)
            neo = pi5neo.Pi5Neo('/dev/spidev0.0', NUM_PIXELS, 800)
        # clear ด้วยคำสั่งที่คุณต้องการ
        neo.fill_strip(0, 0, 0)
        neo.update_strip()
        time.sleep(0.01)
        print(f"💡 LED reinit: {NUM_PIXELS} pixels")

    def set_led(level, block, r, g, b):
        i = idx(level, block)
        if i < 0 or i >= NUM_PIXELS:
            return {"ok": False, "error": f"Invalid L{level}B{block}"}
        _led_state[i] = (r, g, b)
        neo.set_led_color(i, r, g, b)
        neo.update_strip()
        time.sleep(0.002)
        return {"ok": True, "index": i}

    def set_led_batch(leds):
        errors, count = [], 0
        # clear ก่อนเสมอด้วยคำสั่งที่กำหนด
        neo.fill_strip(0, 0, 0)
        for led in leds:
            lv = int(led.get('level', 0))
            bk = int(led.get('block', 0))
            r  = int(led.get('r', 0)); g = int(led.get('g', 0)); b = int(led.get('b', 0))
            i = idx(lv, bk)
            if 0 <= i < NUM_PIXELS:
                _led_state[i] = (r, g, b)
                neo.set_led_color(i, r, g, b)
                count += 1
            else:
                errors.append(f"L{lv}B{bk}: invalid")
        neo.update_strip()
        time.sleep(0.003)
        out = {"ok": True, "count": count, "total_requested": len(leds)}
        if errors: out["errors"] = errors
        return out

    def clear_all_leds():
        global _led_state
        _led_state = [(0, 0, 0)] * NUM_PIXELS
        neo.fill_strip(0, 0, 0)
        neo.update_strip()
        time.sleep(0.01)
        return {"ok": True, "pixels_cleared": NUM_PIXELS}

except ImportError:
    # -------- MOCK fallback (ไม่มีฮาร์ดแวร์) --------
    def refresh_led_config():
        global NUM_PIXELS, _led_state
        NUM_PIXELS = _total_pixels(get_shelf_config())
        _led_state = [(0, 0, 0)] * max(1, NUM_PIXELS)
        print(f"[MOCK] LED reinit: {NUM_PIXELS} pixels")

    def set_led(level, block, r, g, b):
        i = idx(level, block)
        if 0 <= i < len(_led_state):
            _led_state[i] = (r, g, b)
            print(f"[MOCK] set i={i} -> ({r},{g},{b})")
            return {"ok": True, "index": i, "mock": True}
        return {"ok": False, "error": "invalid index", "mock": True}

    def set_led_batch(leds):
        ok = 0; errs = []
        for led in leds:
            i = idx(int(led.get('level',0)), int(led.get('block',0)))
            if 0 <= i < len(_led_state):
                _led_state[i] = (int(led.get('r',0)), int(led.get('g',0)), int(led.get('b',0)))
                ok += 1
            else:
                errs.append(str(led))
        print(f"[MOCK] batch set {ok}/{len(leds)}")
        return {"ok": True, "count": ok, "errors": errs, "mock": True}

    def clear_all_leds():
        global _led_state
        _led_state = [(0, 0, 0)] * len(_led_state)
        print(f"[MOCK] clear {len(_led_state)}")
        return {"ok": True}

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
