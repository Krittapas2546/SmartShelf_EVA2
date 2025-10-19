# test_LED.py
from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver
import time

LED_COUNT = 25      # ปรับจำนวนหลอดตามของจริง
SPI_BUS = 0
SPI_DEVICE = 0

def hard_clear(strip, pause=0.02):
    """
    ล้างไฟแบบชัวร์ ๆ:
    1) ส่งเฟรมดำทั้งเส้น
    2) ใช้คำสั่ง clear ของไดรเวอร์ (ส่งเฟรมรีเซ็ต)
    3) ส่งเฟรมดำซ้ำอีกครั้งกันหลุด
    """
    strip.set_all_pixels(Color(0, 0, 0))
    strip.show()
    time.sleep(pause)

    strip.clear()  # เคลียร์ผ่านไดรเวอร์ (รีเซ็ตบัฟเฟอร์/เส้น)
    time.sleep(pause)

    strip.set_all_pixels(Color(0, 0, 0))
    strip.show()
    time.sleep(pause)

def light_one(strip, index, color=Color(255, 0, 0)):
    """ตัวช่วย: เปิดแค่ 1 ดวงตาม index"""
    strip.set_all_pixels(Color(0, 0, 0))
    strip.show()
    time.sleep(0.01)
    strip.set_pixel_color(index, color)
    strip.show()

if __name__ == "__main__":
    # Initialize the WS2812 strip
    strip = WS2812SpiDriver(spi_bus=SPI_BUS, spi_device=SPI_DEVICE, led_count=LED_COUNT).get_strip()

    # เดโม: เปิดทั้งเส้นเป็นเขียว 1 วินาที แล้ว hard clear
    # strip.set_all_pixels(Color(0, 255, 0))
    # strip.show()
    # time.sleep(1.0)
    # hard_clear(strip)

    # ทดสอบเปิดดวงเดียว (index 0 สีดำ) แล้วเคลียร์อีกครั้ง
    # light_one(strip, 0, Color(255, 0, 0))
    # time.sleep(1.0)
    # light_one(strip, 1, Color(0, 255, 0))
    # time.sleep(1.0)
    # light_one(strip, 2, Color(0, 0, 255))
    # time.sleep(1.0)
    hard_clear(strip)
