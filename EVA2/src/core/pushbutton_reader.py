#!/usr/bin/env python3
"""
Push Button Reader for Smart Shelf System
=========================================

Simple button reader class using PCF8574 I2C GPIO expander
with debounce and callback support. Integrates directly with main server.

Hardware Setup:
- I2C Address: 0x20 (PCF8574)
- Pins: P0, P1, P2 (3 buttons)
- PCF8574 quasi-bidirectional I/O with weak pull-up
- Buttons connect to GND when pressed (active LOW)

Usage:
    from core.pushbutton_reader import PushButtonReader
    
    def on_button_press(button_index, position):
        print(f"Button {button_index} pressed at {position}")
    
    reader = PushButtonReader(callback=on_button_press)
    reader.start_monitoring()  # Non-blocking
    # ... your main code ...
    reader.stop_monitoring()
"""

import time
import threading
from typing import Callable, Dict, Optional
from dataclasses import dataclass

try:
    from smbus2 import SMBus
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False
    print("⚠️ smbus2 not available - button reader will run in simulation mode")

# Hardware Configuration (PCF8574 only)
I2C_ADDR = 0x20          # PCF8574 I2C address
BUTTON_PINS = [0, 1, 2]  # GPIO pins P0, P1, P2
DEBOUNCE_TIME = 0.2      # 200ms debounce
I2C_BUS = 1              # I2C bus number
POLL_INTERVAL = 0.05     # 50ms polling interval

@dataclass
class ButtonState:
    """Button state tracking"""
    pressed: bool = False
    last_press_time: float = 0.0
    debounce_count: int = 0

class PushButtonReader:
    """
    Push button reader for PCF8574 (quasi-bidirectional I/O)
    
    How it works:
    - Write 0xFF once during init = set all pins as input with weak pull-up
    - Read 1 byte from port: 1=HIGH(released), 0=LOW(pressed)
    - Software inverts: pressed=True for easier handling
    """
    
    def __init__(self, callback: Optional[Callable[[int, str], None]] = None, debug: bool = False):
        """
        Initialize button reader
        
        Args:
            callback: Function called when button pressed (button_index, position)
            debug: Enable debug logging
        """
        self.callback = callback
        self.debug = debug
        self.running = False
        self.monitor_thread = None
        
        # Button state tracking
        self.button_states = {pin: ButtonState() for pin in BUTTON_PINS}
        
        # Position mapping (L1B1, L1B2, L1B3 by default)
        self.position_mapping = {
            BUTTON_PINS[0]: "L1B1",
            BUTTON_PINS[1]: "L1B2",
            BUTTON_PINS[2]: "L1B3",
        }
        
        # I2C setup
        self.bus = None
        self.hardware_available = False
        
        if HAS_SMBUS:
            try:
                self.bus = SMBus(I2C_BUS)
                # Test I2C connection and init PCF8574
                self.bus.read_byte(I2C_ADDR)  # Probe device
                self._init_pcf8574()
                self.hardware_available = True
                self._log("✅ I2C hardware detected (PCF8574)")
                
            except Exception as e:
                self._log(f"⚠️ I2C hardware not available: {e}")
                self.hardware_available = False
        else:
            self._log("⚠️ Running in simulation mode (smbus2 not installed)")
    
    def _log(self, msg: str):
        """Debug logging"""
        if self.debug:
            print(f"[ButtonReader] {msg}")
    
    def _init_pcf8574(self):
        """
        Initialize PCF8574 GPIO expander
        
        PCF8574 uses quasi-bidirectional I/O:
        - Write 0xFF = all pins as input with weak pull-up
        - Buttons pull pins LOW when pressed
        """
        try:
            # Write all 1s to enable input mode with pull-up
            self.bus.write_byte(I2C_ADDR, 0xFF)
            self._log("🔧 PCF8574 initialized (all pins as input w/ pull-up)")
        except Exception as e:
            self._log(f"⚠️ PCF8574 init failed: {e}")
    
    def update_position_mapping(self, button_mapping: Dict[int, str]):
        """
        Update position mapping for buttons
        
        Args:
            button_mapping: Dict mapping button_index to position (e.g., {0: "L1B1", 1: "L2B3"})
        """
        self.position_mapping.update(button_mapping)
        self._log(f"📍 Position mapping updated: {self.position_mapping}")
    
    def read_buttons(self) -> Dict[int, bool]:
        """
        Read current button states from PCF8574
        
        Returns:
            Dict mapping button_index to pressed state (True = pressed)
            
        PCF8574 logic:
        - Read entire 8-bit port
        - 1 = HIGH (button released)
        - 0 = LOW (button pressed)
        - Invert bits so pressed = True for easier handling
        """
        if not self.hardware_available:
            # Simulation mode - no buttons pressed
            return {i: False for i in BUTTON_PINS}
        
        try:
            # Read entire port (8 bits)
            port_val = self.bus.read_byte(I2C_ADDR)
            
            # Extract and invert button states
            # pressed = True when pin is LOW (0)
            button_states = {}
            for pin in BUTTON_PINS:
                pin_high = bool((port_val >> pin) & 0x01)
                button_states[pin] = not pin_high  # Invert: LOW = pressed
            
            return button_states
            
        except Exception as e:
            self._log(f"⚠️ Button read error: {e}")
            return {i: False for i in BUTTON_PINS}
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in separate thread)"""
        self._log("🔄 Button monitoring started")
        
        while self.running:
            try:
                # Read current button states
                current_states = self.read_buttons()
                now = time.time()
                
                # Process each button
                for pin in BUTTON_PINS:
                    cur = current_states.get(pin, False)
                    st = self.button_states[pin]
                    
                    # Detect button press (rising edge)
                    if cur and not st.pressed:
                        # Button press detected
                        time_since_last = now - st.last_press_time
                        
                        if time_since_last > DEBOUNCE_TIME:
                            st.pressed = True
                            st.last_press_time = now
                            
                            # Get position mapping
                            pos = self.position_mapping.get(pin, f"L1B{pin+1}")
                            
                            self._log(f"🔘 Button {pin} pressed -> {pos}")
                            
                            # Trigger callback
                            if self.callback:
                                try:
                                    self.callback(pin, pos)
                                except Exception as cb_err:
                                    self._log(f"⚠️ Callback error: {cb_err}")
                        else:
                            # Too soon after last press - ignore (debounce)
                            self._log(f"🔇 Button {pin} debounced ({time_since_last:.3f}s)")
                    
                    # Detect button release (falling edge)
                    elif not cur and st.pressed:
                        st.pressed = False
                        self._log(f"🔘 Button {pin} released")
                
                # Sleep until next poll
                time.sleep(POLL_INTERVAL)
                
            except Exception as e:
                self._log(f"⚠️ Monitor loop error: {e}")
                time.sleep(0.1)  # Brief pause on error
        
        self._log("🛑 Button monitoring stopped")
    
    def start_monitoring(self):
        """Start button monitoring (non-blocking)"""
        if self.running:
            self._log("⚠️ Monitoring already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self._log("▶️ Button monitoring started (non-blocking)")
    
    def stop_monitoring(self):
        """Stop button monitoring"""
        if not self.running:
            return
        
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        self._log("⏹️ Button monitoring stopped")
    
    def get_status(self) -> Dict:
        """
        Get current button reader status
        
        Returns:
            Status dictionary with hardware info, mapping, and current states
        """
        return {
            "hardware_available": self.hardware_available,
            "running": self.running,
            "position_mapping": self.position_mapping.copy(),
            "current_states": self.read_buttons(),
            "i2c_address": f"0x{I2C_ADDR:02X}",
            "button_pins": BUTTON_PINS,
            "debounce_time_ms": int(DEBOUNCE_TIME * 1000),
            "poll_interval_ms": int(POLL_INTERVAL * 1000)
        }
    
    def simulate_button_press(self, button_index: int):
        """
        Simulate button press for testing (when hardware not available)
        
        Args:
            button_index: Button index to simulate (0-2)
        """
        if button_index not in BUTTON_PINS:
            self._log(f"⚠️ Invalid button index: {button_index}")
            return
        
        position = self.position_mapping.get(button_index, f"L1B{button_index+1}")
        self._log(f"🧪 Simulating button {button_index} press -> {position}")
        
        if self.callback:
            try:
                self.callback(button_index, position)
            except Exception as callback_error:
                self._log(f"⚠️ Simulation callback error: {callback_error}")
    
    def debug_gpio_state(self):
        """Debug function to check raw GPIO state of PCF8574"""
        if not self.hardware_available:
            self._log("⚠️ Hardware not available for debugging")
            return None
        
        try:
            # Read entire port (8 bits)
            port_val = self.bus.read_byte(I2C_ADDR)
            
            self._log(f"🔍 Raw PORT (PCF8574): 0x{port_val:02X} ({port_val:08b})")
            
            # Show individual pin states
            for pin in BUTTON_PINS:
                pin_high = bool((port_val >> pin) & 0x01)
                button_pressed = not pin_high  # Inverted logic
                self._log(f"  P{pin}: {'HIGH' if pin_high else 'LOW'} -> Button {'PRESSED' if button_pressed else 'RELEASED'}")
            
            return port_val
            
        except Exception as e:
            self._log(f"⚠️ GPIO debug error: {e}")
            return None
    
    def __del__(self):
        """Cleanup on destruction"""
        self.stop_monitoring()
        if self.bus:
            try:
                self.bus.close()
            except:
                pass

# Example usage and testing
if __name__ == "__main__":
    def test_callback(button_index, position):
        print(f"🔘 Button {button_index} pressed at position {position}")
    
    # Create reader with debug enabled
    reader = PushButtonReader(callback=test_callback, debug=True)
    
    # Show status
    status = reader.get_status()
    print(f"📊 Button Reader Status: {status}")
    
    # Start monitoring
    reader.start_monitoring()
    
    # Test simulation if no hardware
    if not reader.hardware_available:
        print("🧪 Testing simulation mode...")
        time.sleep(1)
        for i in range(3):
            reader.simulate_button_press(i)
            time.sleep(0.5)
    
    # Keep running for manual testing
    try:
        print("✨ Press buttons or Ctrl+C to exit...")
        print("🔍 Debug: Press 'd' + Enter to see GPIO state")
        
        import sys
        import select
        
        while True:
            # Check for keyboard input (works on Linux/Pi)
            if hasattr(select, 'select'):
                ready, _, _ = select.select([sys.stdin], [], [], 1)
                if ready:
                    user_input = sys.stdin.readline().strip().lower()
                    if user_input == 'd':
                        reader.debug_gpio_state()
                    elif user_input == 'q':
                        break
            else:
                # Windows fallback
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n👋 Stopping...")
        reader.stop_monitoring()