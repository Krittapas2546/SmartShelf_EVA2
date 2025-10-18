from smbus2 import SMBus
import time

ADDR = 0x20
PINS = [0, 1, 2]                 # P1, P2, P3
LABELS = ["L1B1", "L1B2", "L1B3"]  # ข้อความตอนกด
DEBOUNCE = 0.06                 # ~60 ms

def main():
    with SMBus(1) as bus:
        # ปล่อยทุกบิต HIGH ให้เป็น input
        bus.write_byte(ADDR, 0xFF)

        pressed = [False] * len(PINS)
        last_t  = [0.0]  * len(PINS)

        while True:
            now = time.time()

            # คงโหมด input แล้วอ่านครั้งเดียว
            bus.write_byte(ADDR, 0xFF)
            try:
                v = bus.read_byte(ADDR) & 0xFF  # 1=ปล่อย, 0=กด
            except OSError:
                # ถ้า I2C สะดุด ให้พักสั้นๆแล้ววนใหม่
                time.sleep(0.1)
                continue

            for i, pin in enumerate(PINS):
                state = (v >> pin) & 1
                # ขอบตก: เพิ่งกด -> พิมพ์ครั้งเดียว
                if not pressed[i] and state == 0 and (now - last_t[i] > DEBOUNCE):
                    print(LABELS[i])
                    pressed[i] = True
                    last_t[i] = now
                # ขอบขึ้น: เพิ่งปล่อย -> พร้อมพิมพ์รอบถัดไป
                elif pressed[i] and state == 1 and (now - last_t[i] > DEBOUNCE):
                    pressed[i] = False
                    last_t[i] = now

            time.sleep(0.005)

if __name__ == "__main__":
    main()
