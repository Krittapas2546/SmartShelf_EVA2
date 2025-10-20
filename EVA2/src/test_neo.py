<<<<<<< HEAD

# test_LED_neo.py


=======
# test_LED_Neo.py
>>>>>>> parent of 81beaf8 (LED_cor)
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

LED_COUNT = 24          # <-- ปรับตามจำนวนจริง
SPI_DEVICE = "/dev/spidev0.0"
FREQUENCY = 800         # kHz ของสัญญาณ

def hard_clear(neo, pause=0.02, repeat=2):
    """
    ล้างไฟแบบชัวร์:
      - ส่งเฟรมดำทั้งเส้น + update หลายครั้งกันค้าง
    """
    for _ in range(repeat):
        neo.fill_strip(0, 0, 0)
        neo.update_strip()
        time.sleep(pause)

def set_all(neo, r, g, b):
    """เปิดทั้งเส้นสีเดียว"""
    neo.fill_strip(r, g, b)
    neo.update_strip()

def light_one(neo, index, r=255, g=0, b=0, pause_after=0):
    """เปิด 1 ดวงตาม index (ปิดที่เหลือก่อน)"""
    neo.fill_strip(0, 0, 0)
    neo.update_strip()
    time.sleep(0.01)
    neo.set_led_color(index, r, g, b)
    neo.update_strip()
    if pause_after:
        time.sleep(pause_after)
def light_many(neo, indices, r, g, b, clear_first=False):
    """
    เปิดหลายดวงพร้อมกัน
    - clear_first=True จะล้างก่อน
    - clear_first=False จะ 'เพิ่ม' ทับของเดิม (ไม่ล้าง)
    """
    if clear_first:
        neo.fill_strip(0, 0, 0)

    # เซ็ตสีให้ทุก index ที่ต้องการ
    for i in indices:
        neo.set_led_color(int(i), int(r), int(g), int(b))

    # อัปเดตครั้งเดียวเพื่อลดการกระพริบ
    neo.update_strip()

def add_pixels(neo, pairs):
    """
    เพิ่มดวงแบบ “ไม่ล้างของเดิม”
    pairs: [(index, (r,g,b)), ...]
    """
    for i, (r, g, b) in pairs:
        neo.set_led_color(int(i), int(r), int(g), int(b))
    neo.update_strip()
    
def turn_off(neo, indices):
    """ดับเฉพาะบางดวง (ไม่กระทบดวงอื่น)"""
    for i in indices:
        neo.set_led_color(int(i), 0, 0, 0)
    neo.update_strip()
    
if __name__ == "__main__":
<<<<<<< HEAD
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
=======
    neo = pi5neo.Pi5Neo(SPI_DEVICE, LED_COUNT, FREQUENCY)

    # try:
    hard_clear(neo)

        # 1) เปิดหลายดวงพร้อมกัน (ล้างก่อน)
        # light_many(neo, [0, 1, 2], 255, 0, 0, clear_first=True)  # 0,1,2 เป็นสีแดง
        # time.sleep(1)
>>>>>>> parent of 81beaf8 (LED_cor)

        # 2) สั่งติดเพิ่ม โดยไม่ล้างของเดิม
    
    # add_pixels(neo, [
    #     (4, (0, 255, 0)),   # เพิ่มดวง 5 เป็นเขียว
    #     (6, (0, 0, 255)),   # เพิ่มดวง 7 เป็นน้ำเงิน
    #     (10, (255, 255, 0)),  # เพิ่มดวง 11 เป็นเหลือง
    #     (11, (255, 0, 255)),  # เพิ่มดวง 12 เป็นม่วง
    #     (0, (0, 255, 255))   # เพิ่มดวง 13 เป็นฟ้า
    # ])
    # time.sleep(10)

        # 3) ดับเฉพาะบางดวง (ของที่เหลือยังค้าง)
        # turn_off(neo, [1, 7])   # ดับดวง 1 และ 7
        # time.sleep(1)

        # 4) เปิดทั้งเส้นแบบไม่กระพริบ (อัปเดตครั้งเดียว)
        # light_many(neo, list(range(LED_COUNT)), 16, 16, 16, clear_first=True)
        # time.sleep(1)
    # #     # เดโม: เปิดทั้งเส้นเป็นสีเขียว 1 วินาที แล้วเคลียร์
    #     set_all(neo, 0, 255, 0)
    #     time.sleep(20.0)
    #     hard_clear(neo)

    # #     # เดโม: เปิดดวงเดียวทีละดวง (0,1,2) แล้วเคลียร์
    # #     
    #     light_one(neo, 0, 255, 0, 0, pause_after=2.0)  # index 0 = DUMMY
    #     light_one(neo, 1, 0, 255, 0, pause_after=2.0)
    #     light_one(neo, 2, 0, 0, 255, pause_after=2.0)

    # finally:
        # ปลอดภัยไว้ก่อน—ออกโปรแกรมให้ดับทั้งหมด
        # hard_clear(neo)
