# core/led_controller.py

from core.database import SHELF_CONFIG
NUM_PIXELS = sum(SHELF_CONFIG.values())

def idx(level, block):
    """
    แปลง (level, block) เป็น index ของ LED
    level: 1..N (1 คือชั้นล่างสุด)
    """
    max_level = max(SHELF_CONFIG.keys())
    reversed_level = max_level - level + 1
    
    return sum(SHELF_CONFIG[l] for l in range(1, reversed_level)) + (block-1)


_led_state = [(0, 0, 0)] * NUM_PIXELS 

try:
    from pi5neo import Pi5Neo
    neo = Pi5Neo('/dev/spidev0.0', NUM_PIXELS, 800)

    def set_led(level, block, r, g, b):
        i = idx(level, block)
        global _led_state
        _led_state = list(_led_state)
        _led_state[i] = (r, g, b)
        for j, (rr, gg, bb) in enumerate(_led_state):
            neo.set_led_color(j, rr, gg, bb)
        neo.update_strip()
        return {"ok": True, "index": i}

    def set_led_batch(leds):
        global _led_state
        _led_state = list(_led_state)
        for led in leds:
            level = int(led.get('level', 0))
            block = int(led.get('block', 0))
            r = int(led.get('r', 0))
            g = int(led.get('g', 0))
            b = int(led.get('b', 0))
            i = idx(level, block)
            _led_state[i] = (r, g, b)
        for j, (rr, gg, bb) in enumerate(_led_state):
            neo.set_led_color(j, rr, gg, bb)
        neo.update_strip()
        return {"ok": True, "count": len(leds)}

except ImportError:
    def set_led(level, block, r, g, b):
        i = idx(level, block)
        global _led_state
        _led_state = list(_led_state)
        _led_state[i] = (r, g, b)
        print(f"[MOCK] Would light LED at level {level}, block {block}, color=({r},{g},{b})")
        print(f"[MOCK] LED STATE: {_led_state}")
        return {"ok": True, "index": i, "mock": True}

    def set_led_batch(leds):
        global _led_state
        _led_state = list(_led_state)
        for led in leds:
            level = int(led.get('level', 0))
            block = int(led.get('block', 0))
            r = int(led.get('r', 0))
            g = int(led.get('g', 0))
            b = int(led.get('b', 0))
            i = idx(level, block)
            _led_state[i] = (r, g, b)
        print(f"[MOCK] Would batch set LEDs: {leds}")
        print(f"[MOCK] LED STATE: {_led_state}")
        return {"ok": True, "count": len(leds), "mock": True}

def clear_all_leds():
    global _led_state
    _led_state = [(0, 0, 0)] * NUM_PIXELS
    if 'neo' in globals() and neo:
        neo.clear_strip()
        neo.update_strip()
    else:
        print("[MOCK] Would clear all LEDs")
