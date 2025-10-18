#!/usr/bin/env python3
"""
Push Button Reader for Smart Shelf System
=========================================

Simple button reader class using PCF8574/MCP23008 I2C GPIO expander
with debounce and callback support. Integrates directly with main server.

Hardware Setup:
- I2C Address: 0x20 (MCP23008) or 0x21 (PCF8574)
- Pins: P0, P1, P2 (3 buttons)
- Pull-up resistors enabled (buttons connect to GND when pressed)

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
import logging
from typing import Callable, Dict, Optional
from dataclasses import dataclass

try:
    from smbus2 import SMBus
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False
    print("⚠️ smbus2 not available - button reader will run in simulation mode")

# Hardware Configuration
I2C_ADDR = 0x20          # MCP23008 I2C address
BUTTON_PINS = [0, 1, 2]  # GPIO pins P0, P1, P2
DEBOUNCE_TIME = 0.05     # 50ms debounce
I2C_BUS = 1              # I2C bus number
POLL_INTERVAL = 0.02     # 20ms polling interval

@dataclass
class ButtonState:
    """Button state tracking"""
    pressed: bool = False
    last_press_time: float = 0.0
    debounce_count: int = 0

class PushButtonReader:
    """
    Simple push button reader with debounce and position mapping
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
            0: "L1B1",  # Button 0 -> Level 1 Block 1
            1: "L1B2",  # Button 1 -> Level 1 Block 2  
            2: "L1B3",  # Button 2 -> Level 1 Block 3
        }
        
        # I2C setup
        self.bus = None
        self.hardware_available = False
        
        if HAS_SMBUS:
            try:
                self.bus = SMBus(I2C_BUS)
                # Test I2C connection
                self.bus.read_byte(I2C_ADDR)
                self.hardware_available = True
                self._log("✅ I2C hardware detected")
                
                # Initialize MCP23008 (if needed)
                self._init_mcp23008()
                
            except Exception as e:
                self._log(f"⚠️ I2C hardware not available: {e}")
                self.hardware_available = False
        else:
            self._log("⚠️ Running in simulation mode (smbus2 not installed)")
    
    def _log(self, message: str):
        """Debug logging"""
        if self.debug:
            print(f"[ButtonReader] {message}")
    
    def _init_mcp23008(self):
        """Initialize MCP23008 GPIO expander"""
        try:
            # Set GPIO direction (0xFF = all inputs)
            self.bus.write_byte_data(I2C_ADDR, 0x00, 0xFF)  # IODIR
            # Enable pull-ups (0xFF = all enabled)  
            self.bus.write_byte_data(I2C_ADDR, 0x06, 0xFF)  # GPPU
            self._log("🔧 MCP23008 initialized")
        except Exception as e:
            self._log(f"⚠️ MCP23008 init failed: {e}")
    
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
        Read current button states
        
        Returns:
            Dict mapping button_index to pressed state (True = pressed)
        """
        if not self.hardware_available:
            # Simulation mode - no buttons pressed
            return {i: False for i in BUTTON_PINS}
        
        try:
            # Read GPIO register
            gpio_state = self.bus.read_byte_data(I2C_ADDR, 0x09)  # GPIO register
            
            # Extract button states (inverted logic - 0 = pressed)
            button_states = {}
            for pin in BUTTON_PINS:
                button_states[pin] = not bool(gpio_state & (1 << pin))
            
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
                current_time = time.time()
                
                # Process each button
                for button_index in BUTTON_PINS:
                    current_pressed = current_states.get(button_index, False)
                    button_state = self.button_states[button_index]
                    
                    # Debounce logic
                    if current_pressed != button_state.pressed:
                        # State change detected
                        if current_time - button_state.last_press_time > DEBOUNCE_TIME:
                            # Update state after debounce period
                            button_state.pressed = current_pressed
                            button_state.last_press_time = current_time
                            
                            # Trigger callback on press (not release)
                            if current_pressed and self.callback:
                                position = self.position_mapping.get(button_index, f"L1B{button_index+1}")
                                
                                self._log(f"🔘 Button {button_index} pressed -> {position}")
                                
                                try:
                                    self.callback(button_index, position)
                                except Exception as callback_error:
                                    self._log(f"⚠️ Callback error: {callback_error}")
                
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
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Stopping...")
        reader.stop_monitoring()