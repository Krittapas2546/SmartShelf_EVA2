# core/led_controller.py

from core.database import get_shelf_config

# ---------- Mapping (ซ้าย→ขวา ทุกชั้น) ----------
def _total_pixels(cfg: dict) -> int:
    return sum(int(v) for v in cfg.values())

def idx(level: int, block: int) -> int:
    """L1B1 คือ index 0, ไม่ reverse, รองรับ blocks ต่อชั้นไม่เท่ากัน"""
    cfg = get_shelf_config()
    if level not in cfg or not (1 <= block <= int(cfg[level])):
        return -1
    offset = 0
    for l in sorted(cfg):
        if l < level:
            offset += int(cfg[l])
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
