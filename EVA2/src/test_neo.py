
# test_LED_neo.py


import time
import pi5neo
SHELF_CONFIG = {
    1: 6,  # Level 1: 6 blocks
    2: 6,  # Level 2: 6 blocks
    3: 6,  # Level 3: 6 blocks
    4: 6,  # Level 4: 6 blocks
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

LED_COUNT = 24
SPI_DEVICE = "/dev/spidev0.0"
FREQ = 800

# ---------- ซอฟต์บัฟเฟอร์สถานะ ----------
state = [(0, 0, 0)] * LED_COUNT  # เก็บสีของทุกดวง (r,g,b)

def show_state(neo):
    """เรนเดอร์ทั้งเส้นจากบัฟเฟอร์ในครั้งเดียว"""
    for i, (r, g, b) in enumerate(state):
        neo.set_led_color(i, r, g, b)
    neo.update_strip()

def set_pixels(neo, pairs):
    """
    เพิ่ม/เปลี่ยนสีบางดวงโดย 'ไม่ล้างของเดิม'
    pairs: [(index, (r,g,b)), ...]
    """
    for i, (r, g, b) in pairs:
        state[i] = (int(r), int(g), int(b))
    show_state(neo)

def turn_off_some(neo, indices):
    """ดับเฉพาะบางดวง โดยคงดวงอื่นไว้ตามบัฟเฟอร์"""
    for i in indices:
        state[i] = (0, 0, 0)
    show_state(neo)

def hard_clear(neo, pause=0.02, repeat=2):
    """ล้างทั้งเส้นแบบชัวร์ แล้วซิงค์บัฟเฟอร์ให้เป็นศูนย์"""
    global state
    for _ in range(repeat):
        neo.fill_strip(0, 0, 0)
        neo.update_strip()
        time.sleep(pause)
    state = [(0, 0, 0)] * LED_COUNT  # ซิงค์บัฟเฟอร์ให้ตรงกับฮาร์ดแวร์

if __name__ == "__main__":
    neo = pi5neo.Pi5Neo(SPI_DEVICE, LED_COUNT, FREQ)
    try:
        show_state(neo)
        # เปิดบางดวงก่อน (เช่น 0,1,2 และ 5,7)
        set_pixels(neo, [
            (0, (255, 0, 0)),
            (1, (255, 0, 0)),
            (2, (255, 0, 0)),
            (3, (0, 255, 0)),
            (4, (0, 0, 255)),
        ])
        time.sleep(5)

        # ดับเฉพาะ 0 และ 4 (แม้ 4 ไม่ได้เปิดก็จะไม่มีผลกับดวงอื่น)
        turn_off_some(neo, [0, 1])
        time.sleep(1)

        # เพิ่มดวงใหม่โดยไม่ล้างของเดิม
        set_pixels(neo, [
            (5, (255, 255, 0)),
            (6, (255, 0, 255)),
        ])
        time.sleep(10)

    finally:
        hard_clear(neo)
