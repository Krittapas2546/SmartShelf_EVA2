# led_controller_standalone.py
# ใช้ทดสอบระบบ LED แบบไฟล์เดียว (มีทั้งโหมดฮาร์ดแวร์จริงและ MOCK)
# รันตัวอย่าง: python led_controller_standalone.py --demo
# หรือ:       python led_controller_standalone.py --target 1 1
#             python led_controller_standalone.py --error 1 3
#             python led_controller_standalone.py --sweep
#             python led_controller_standalone.py --clear

import argparse
import time

# ---------- สมมติ Layout ตายตัว (4 ชั้น × 6 บล็อก) ----------
SHELF_CONFIG = {
    1: 8,  # Level 1: 6 blocks
    2: 8,  # Level 2: 6 blocks
    3: 6,  # Level 3: 6 blocks
    4: 8,  # Level 4: 6 blocks
}

def get_shelf_config():
    # ทำให้โค้ดส่วนล่างใช้เหมือน led_controller เดิม
    return SHELF_CONFIG

# ---------- Mapping & Helpers ----------
def _total_pixels(cfg: dict) -> int:
    return sum(int(v) for v in cfg.values())

def idx(level: int, block: int) -> int:
    """
    แปลง (level, block) -> LED index
    เดินสายแบบ: เริ่ม L<top> B1 = 0 → ซ้าย→ขวา แล้วลงชั้นถัดไป
    4×6: L4B1=0 ... L4B6=5, L3B1=6 ... L1B6=23
    """
    cfg = get_shelf_config()
    if level not in cfg or not (1 <= block <= int(cfg[level])):
        return -1

    order = sorted(cfg.keys(), reverse=True)  # จากบนลงล่าง: 4,3,2,1
    offset = 0
    for lv in order:
        if lv == level:
            break
        offset += int(cfg[lv])
    return offset + (block - 1)

# ---------- State / Hardware ----------
NUM_PIXELS = _total_pixels(get_shelf_config())
state = [(0, 0, 0)] * max(1, NUM_PIXELS)  # บัฟเฟอร์สี (r,g,b)

# พยายามใช้ไลบรารีจริง ถ้าไม่มีให้ MOCK
try:
    import pi5neo
    _HW = True
    neo = pi5neo.Pi5Neo('/dev/spidev0.0', NUM_PIXELS, 800)

    def show_state():
        for i, (r, g, b) in enumerate(state):
            neo.set_led_color(i, r, g, b)
        neo.update_strip()

    def set_pixels(pairs):
        """
        pairs รองรับ:
          - (level, block, (r,g,b))  หรือ
          - (index, (r,g,b))
        """
        for item in pairs:
            if len(item) == 3 and isinstance(item[2], tuple):
                # รูปแบบ (level, block, (r,g,b))
                level, block, (r, g, b) = item
                i = idx(level, block)
            elif len(item) == 2 and isinstance(item[1], tuple):
                # รูปแบบ (index, (r,g,b))
                i, (r, g, b) = item
            else:
                continue  # ข้าม item ที่ไม่ตรงรูปแบบ
            
            if 0 <= i < NUM_PIXELS:
                state[i] = (int(r), int(g), int(b))
        show_state()

    def turn_off_some(indices):
        for i in indices:
            if isinstance(i, tuple) and len(i) == 2:
                level, block = i
                i = idx(level, block)
            if 0 <= i < NUM_PIXELS:
                state[i] = (0, 0, 0)
        show_state()

    def hard_clear(pause=0.02, repeat=2):
        global state
        for _ in range(repeat):
            neo.fill_strip(0, 0, 0)
            neo.update_strip()
            time.sleep(pause)
        state = [(0, 0, 0)] * NUM_PIXELS

    def refresh_led_config():
        # ในไฟล์นี้ NUM_PIXELS ตายตัวอยู่แล้ว แต่คงฟังก์ชันไว้เพื่อให้ API ครบ
        hard_clear()
        print(f"💡 LED reinit (HW): {NUM_PIXELS} pixels")

except Exception:
    _HW = False

    def show_state():
        active = [(i, rgb) for i, rgb in enumerate(state) if rgb != (0, 0, 0)]
        if active:
            print(f"[MOCK] Active: {active}")
        else:
            print("[MOCK] All OFF")

    def set_pixels(pairs):
        for item in pairs:
            if len(item) == 3 and isinstance(item[2], tuple):
                # รูปแบบ (level, block, (r,g,b))
                level, block, (r, g, b) = item
                i = idx(level, block)
            elif len(item) == 2 and isinstance(item[1], tuple):
                # รูปแบบ (index, (r,g,b))
                i, (r, g, b) = item
            else:
                continue  # ข้าม item ที่ไม่ตรงรูปแบบ
            
            if 0 <= i < len(state):
                state[i] = (int(r), int(g), int(b))
                print(f"[MOCK] set {i} -> ({r},{g},{b})")
        show_state()

    def turn_off_some(indices):
        for i in indices:
            if isinstance(i, tuple) and len(i) == 2:
                level, block = i
                i = idx(level, block)
            if 0 <= i < len(state):
                state[i] = (0, 0, 0)
                print(f"[MOCK] off {i}")
        show_state()

    def hard_clear(pause=0.02, repeat=1):
        global state
        state = [(0, 0, 0)] * len(state)
        print(f"[MOCK] hard_clear: {len(state)} pixels")

    def refresh_led_config():
        global NUM_PIXELS, state
        NUM_PIXELS = _total_pixels(get_shelf_config())
        state = [(0, 0, 0)] * max(1, NUM_PIXELS)
        print(f"[MOCK] LED reinit: {NUM_PIXELS} pixels")

# ---------- High-level ----------
def set_target_blue(level, block):
    hard_clear()
    set_pixels([(level, block, (0, 0, 255))])

def set_target_green(level, block):
    set_pixels([(level, block, (0, 255, 0))])

def add_error_red(level, block):
    set_pixels([(level, block, (255, 0, 0))])

def clear_all_leds():
    hard_clear()

def set_led_batch(leds):
    """
    leds: [{'level':1,'block':2,'r':0,'g':0,'b':255}, ...]
    ล้างก่อนหนึ่งครั้ง แล้วค่อยเซ็ตทั้งหมด
    """
    pairs = []
    for led in leds or []:
        level = int(led['level'])
        block = int(led['block'])
        r = int(led['r'])
        g = int(led['g'])
        b = int(led['b'])
        pairs.append((level, block, (r, g, b)))
    
    hard_clear()
    if pairs:
        set_pixels(pairs)

def set_led(level, block, r, g, b):
    set_pixels([(level, block, (r, g, b))])

# ---------- Debug ----------
def debug_mapping():
    cfg = get_shelf_config()
    total = _total_pixels(cfg)
    print("📍 LED Sequential Mapping Debug")
    print(f"Shelf Config: {cfg} | Total: {total}")
    print(f"{'Level':<6} {'Block':<6} {'Index':<6}")
    print("-"*28)
    for level in sorted(cfg.keys(), reverse=True):
        for block in range(1, int(cfg[level]) + 1):
            print(f"{level:<6} {block:<6} {idx(level, block):<6}")

def validate_expected_mapping():
    expected = {
        (4,1):0,(4,6):5,(3,1):6,(3,6):11,(2,1):12,(2,6):17,(1,1):18,(1,6):23
    }
    ok = True
    for (lv, bk), want in expected.items():
        got = idx(lv, bk)
        mark = "✅" if got == want else "❌"
        if got != want:
            ok = False
        print(f"{mark} L{lv}B{bk} -> {got} (expected {want})")
    return ok

# ---------- Demo sequences ----------
def demo():
    print(f"=== DEMO (HW={_HW}) | NUM_PIXELS={NUM_PIXELS} ===")
    refresh_led_config()
    debug_mapping()
    print("🔍 Validate mapping:")
    validate_expected_mapping()
    time.sleep(0.5)

    # ชี้ตำแหน่งเป้าหมาย
    print("🎯 Target blue L1B1")
    set_target_blue(1, 1)
    time.sleep(1.0)

    # จุดผิดให้เป็นแดง
    print("❌ Wrong red L1B3")
    add_error_red(1, 3)
    time.sleep(1.0)

    # เปลี่ยนเป้าหมายเป็นเขียว (สำเร็จ)
    print("✅ Target green L1B1")
    set_target_green(1, 1)
    turn_off_some([(1, 3)])
    time.sleep(2.0)

    # ดับเฉพาะผิด แล้วเคลียร์ทั้งหมด
    print("🧹 Turn off clear")

    time.sleep(0.5)
    hard_clear()

def test_mixed_formats():
    """ทดสอบการใช้ทั้งรูปแบบ (level,block,color) และ (index,color) ในครั้งเดียว"""
    print("🧪 Testing mixed format support")
    hard_clear()
    
    # ใช้รูปแบบ (level, block, color)
    print("Setting L1B1=Blue, L2B3=Red using (level,block,color) format")
    set_pixels([
        (1, 1, (0, 0, 255)),    # L1B1 = น้ำเงิน
        (2, 3, (255, 0, 0))     # L2B3 = แดง
    ])
    time.sleep(1)
    
    # ใช้รูปแบบ (index, color) 
    print("Adding index 5=Green, index 10=Yellow using (index,color) format")
    set_pixels([
        (5, (0, 255, 0)),       # index 5 = เขียว
        (10, (255, 255, 0))     # index 10 = เหลือง
    ])
    time.sleep(1)
    
    # ผสมทั้งสองรูปแบบ
    print("Mixed: L4B6=Purple + index 15=Cyan")
    set_pixels([
        (4, 6, (255, 0, 255)),  # L4B6 = ม่วง (level,block,color)
        (15, (0, 255, 255))     # index 15 = ฟ้า (index,color)
    ])
    time.sleep(2)
    
    print("✅ Mixed format test complete")
    time.sleep(1)

def sweep(delay=0.05):
    """กวาดไฟทีละดวงจาก 0..NUM_PIXELS-1"""
    hard_clear()
    for i in range(NUM_PIXELS):
        set_pixels([(i, (0, 0, 255))])
        time.sleep(delay)
        turn_off_some([i])
    hard_clear()

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="Standalone LED controller test")
    ap.add_argument("--demo", action="store_true", help="รันเดโม่ครบชุด")
    ap.add_argument("--target", nargs=2, metavar=("LEVEL", "BLOCK"), type=int,
                    help="จุดไฟสีน้ำเงินที่ตำแหน่ง (level,block)")
    ap.add_argument("--green", nargs=2, metavar=("LEVEL", "BLOCK"), type=int,
                    help="จุดไฟสีเขียวที่ตำแหน่ง (level,block)")
    ap.add_argument("--error", nargs=2, metavar=("LEVEL", "BLOCK"), type=int,
                    help="เพิ่มไฟสีแดงที่ตำแหน่งผิด (level,block)")
    ap.add_argument("--batch-blue", action="store_true",
                    help="จุดไฟสีน้ำเงินทั้งชั้นวาง (ทุกตำแหน่ง)")
    ap.add_argument("--sweep", action="store_true",
                    help="กวาดไฟทีละดวง")
    ap.add_argument("--test-mixed", action="store_true",
                    help="ทดสอบการใช้ทั้งรูปแบบ (level,block,color) และ (index,color)")
    ap.add_argument("--clear", action="store_true", help="เคลียร์ไฟทั้งหมด")
    args = ap.parse_args()

    if args.demo:
        demo()
        return

    if args.clear:
        clear_all_leds()

    if args.target:
        lv, bk = args.target
        set_target_blue(lv, bk)

    if args.green:
        lv, bk = args.green
        set_target_green(lv, bk)

    if args.error:
        lv, bk = args.error
        add_error_red(lv, bk)

    if args.batch_blue:
        leds = []
        for lv in sorted(SHELF_CONFIG.keys(), reverse=True):
            for bk in range(1, SHELF_CONFIG[lv] + 1):
                leds.append({"level": lv, "block": bk, "r": 0, "g": 0, "b": 255})
        set_led_batch(leds)

    if args.test_mixed:
        test_mixed_formats()

    if args.sweep:
        sweep()

if __name__ == "__main__":
    main()
